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
# check if DEBUG is on in production (BAD)
DEBUG_ON=$(python $MANAGE shell --no-imports -c 'from django.conf import settings; print(settings.DEBUG)' 2>/dev/null | tail -n 1)
if [ "$DEBUG_ON" = "True" ]; then
    echo -e "\033[1;97;41m                                                          \033[0m"
    echo -e "\033[1;97;41m   [deploy] WARNING: DEBUG IS TRUE IN PRODUCTION !!!      \033[0m"
    echo -e "\033[1;97;41m   tracebacks and settings are public. fix and redeploy   \033[0m"
    echo -e "\033[1;97;41m                                                          \033[0m"
fi
echo -e "[deploy] done. \033[1mDon't forget to \x1b[38;2;187;024;156mrestart\x1b[0;1m the python application in cpanel! \033[0m"
