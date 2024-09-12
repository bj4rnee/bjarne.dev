import os
import sys


sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bjarne_dev.settings")

# add your project directory to the sys.path
project_home = "/home/bjarne.dev/bjarne_dev"
# if property not in sys.path:
sys.path.append(project_home)

bjarne_dev_home = "/home/bjarne.dev/bjarne_dev/index"
sys.path.append(bjarne_dev_home)

from bjarne_dev.wsgi import application