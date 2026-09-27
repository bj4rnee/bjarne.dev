#!/bin/bash
echo "[deploy] fetching changes from remote repository..."
cd /home/bjarxxjd/bjarne.dev
OLD_COMMIT=$(git rev-parse HEAD)
git pull
source /home/bjarxxjd/virtualenv/bjarne.dev/3.13/bin/activate && cd /home/bjarxxjd/bjarne.dev
if ! git diff --quiet $OLD_COMMIT HEAD -- requirements.txt; then
    echo "[deploy] requirements.txt changed, installing..."
    pip install -r requirements.txt
fi
echo "[deploy] collecting static and migrating database..."
MANAGE=/home/bjarxxjd/bjarne.dev/bjarne_dev/manage.py
python $MANAGE collectstatic --noinput
# migrations are authored and committed locally
if ! python $MANAGE makemigrations --check --dry-run; then
    echo -e "\033[1;31m[deploy] ABORT: models changed with no committed migration."
    echo -e "         run 'manage.py makemigrations' locally, commit, redeploy.\033[0m"
    exit 1
fi
python $MANAGE migrate --noinput
echo -e "[deploy] done. \033[1mDon't forget to \x1b[38;2;187;024;156mrestart\x1b[0;1m the python application in cpanel! \033[0m"
