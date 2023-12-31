
""" Common utility functions
"""

from datetime import datetime
from constant import *
from model import *
import pandas as pd
import platform
import shutil
import os

def regularize_dict(d, default_dict):
    for k, v in default_dict.items():
        if k not in d.keys(): d[k] = v

def find_info_by_column_key(column_info, key):
    for k, ci in column_info:
        if key == k: return ci
    
    return None

def check_ci_validation(ci, val):
    res = val
    
    if ci['dtype'] == int:
        try:
            res = int(val)
        except Exception:
            return 0, f"Das Feld `{ci['title']}` erfordert einen ganzzahligen Wert."
    
    return res, None

def null_or(val, def_val):
    if val is None or pd.isna(val) or pd.isnull(val): return def_val
    return val

def int_nonzero_or_empty(val):
    if val == 0: return ''
    
    try:
        return str(int(val))
    except Exception:
        return ''

def get_int_nzoe(val):
    try:
        return int(val)
    except Exception:
        return 0

def get_shortcut_button():
    system = platform.system().lower()
    
    if system == 'windows' or 'linux':
        return '<Button-3>'
    else:
        return '<Button-2>'

def bkup_db():
    if not os.path.exists(local_db_path): return
    
    try:
        shutil.copy(local_db_path, bkup_db_path.format(datetime.now().strftime('%Y-%m-%d-%H-%M-%S')))
    except Exception:
        pass

def update_pending(pending):
    glob_model['pending'] = pending
    glob_model['root'].title(root_title + (' *' if pending else ''))
