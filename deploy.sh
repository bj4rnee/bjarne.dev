#!/bin/bash
echo "[deploy] fetching changes from remote repository..."
cd /home/bjarxxjd/bjarne.dev
git pull
echo "[deploy] collecting static and migrating database..."
source /home/bjarxxjd/virtualenv/bjarne.dev/3.11/bin/activate && cd /home/bjarxxjd/bjarne.dev
python /home/bjarxxjd/bjarne.dev/bjarne_dev/manage.py collectstatic --noinput
python /home/bjarxxjd/bjarne.dev/bjarne_dev/manage.py makemigrations
python /home/bjarxxjd/bjarne.dev/bjarne_dev/manage.py migrate
echo -e "[deploy] done. \033[1mDon't forget to \x1b[38;2;187;024;156mrestart\x1b[0;1m the python application in cpanel! \033[0m"