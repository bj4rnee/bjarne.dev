#!/bin/bash
echo "[deploy] fetching changes from remote repository..."
cd /home/bjarxxjd/bjarne.dev
git pull
echo "[deploy] collecting static and migrating database..."
source /home/bjarxxjd/virtualenv/bjarne.dev/3.13/bin/activate && cd /home/bjarxxjd/bjarne.dev
python /home/bjarxxjd/bjarne.dev/bjarne_dev/manage.py collectstatic --noinput
python /home/bjarxxjd/bjarne.dev/bjarne_dev/manage.py makemigrations
python /home/bjarxxjd/bjarne.dev/bjarne_dev/manage.py migrate
echo -e "[deploy] done. \033[1mDon't forget to \x1b[38;2;187;024;156mrestart\x1b[0;1m the python application in cpanel! \033[0m"

# ---------------------------------------------------------------------------
# FileLink cleanup: one-time cron setup
# ---------------------------------------------------------------------------
# FileLink purges expired/orphaned ciphertext and stale upload temp files via
# the purge_expired management command. It also sweeps expired entries out of
# the file-based cache dir (media/.cache), which Django otherwise only reaps
# lazily. There is no Celery/Redis; it runs from a cPanel cron entry. Add this
# once in the cPanel "Cron Jobs" UI. Hourly is ideal, but the sweep is safe at
# any cadence (even once a day) because it only deletes cache files already
# past their TTL:
#
#   0 * * * * /home/bjarxxjd/virtualenv/bjarne.dev/3.13/bin/python /home/bjarxxjd/bjarne.dev/bjarne_dev/manage.py purge_expired >> /home/bjarxxjd/bjarne.dev/filelink_purge.log 2>&1
