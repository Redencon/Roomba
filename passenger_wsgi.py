import sys

import os

INTERP = os.path.expanduser("/var/www/u2906537/data/www/folegle.ru/.venv/bin/python")
if sys.executable != INTERP:
   os.execl(INTERP, INTERP, *sys.argv)

sys.path.append(os.getcwd())

import traceback

try:
    from main import server as application
except:
    with open("/var/www/u2906537/data/www/folegle.ru/report.log", 'w', encoding='utf-8') as f:
        f.write(traceback.format_exc()) 