
""" No Match Tab Page
"""

from tkinter import messagebox, Frame
from constant import *
from model import *
from util import *
from ui import *
import pandas as pd
import copy

page_tid = 1
page_title = 'No-Match'
page_col = 'NM'
page_tbl = 'tbl_person_no_match'
page_col_count = no_match_col_count

page_model = {    
    'backbone': None,
    'treeview': None,
    'column_info': [
        ('line', { 'title': 'Nr', 'width': 40 }),
        ('surname', { 'title': 'Nachname' }),
        ('forename', { 'title': 'Vorname' }),
        ('mid', { 'title': 'Member-ID' })
    ] + [
        (f"val{i}", { 'title': f"{page_col}-{i + 1}", 'editable': True, 'dtype': int })
        for i in range(page_col_count)
    ],
    'comment': None,
    'person': None,
    'tab': None,
    'hovertext': None,
    'hoverdlg': None,
    'buttons': None,
    'history': [],
    'history_pos': 0    
}

def init_tab(notebook):
    page_model['tab'] = tab = create_tab(notebook, page_title, on_tab_selected, on_save_db_clicked)
    
    top_frame = Frame(tab, height = 700)
    top_frame.pack_propagate(False)
    top_frame.pack(fill = 'x', expand = False)
    
    page_model['treeview'], _ = create_treeview(
        master = top_frame,
        column_info = page_model['column_info'],
        dbl_click_callback = on_treeview_dbl_clicked,
        disable_hscroll = True
    )
    page_model['buttons'] = create_control_panel(
        master = tab,
        button_info = {
            #'Edit Line': { 'click': on_edit_line_clicked },
            'Datenbank speichern': { 'click': on_save_db_clicked },
            'Undo': { 'click': on_undo_clicked },
            'Redo': { 'click': on_redo_clicked }
        }
    )
    page_model['treeview'].bind(get_shortcut_button(), on_shortcut_clicked)
    page_model['treeview'].bind("<Enter>", on_enter)
    page_model['treeview'].bind("<Leave>", on_leave)

    page_model['hoverdlg'] = HoverInfo(tab)
    page_model['treeview'].bind("<Motion>", on_enter)
    
    on_tab_selected()

def on_undo_clicked():
    backward_history()

def on_redo_clicked():
    forward_history()
    
def on_tab_selected():
    page_model['person'] = person_df = load_table('tbl_person', 'surname, forename, mid')    
    person_match_df = load_table(page_tbl)
    records = []
    
    for _, person in person_df.iterrows():
        mid = person['mid']
        r = [person['surname'], person['forename'], mid]
        v = [0] * page_col_count
        
        for _, pm in person_match_df.iterrows():
            if pm['mid'] == mid:
                v = [pm[f"val{i + 1}"] for i in range(page_col_count)]
                break
        
        records.append(tuple(r + v))
    
    df = pd.DataFrame(records, columns = ['surname', 'forename', 'mid'] + [f"val{i}" for i in range(page_col_count)])
    
    page_model['backbone'] = df    
    page_model['comment'] = load_table('tbl_comment')
    
    reset_history()
    update_treeview()

def on_shortcut_clicked(ev):
    tv = page_model['treeview']
    popup_menu = None
    
    try:
        region = tv.identify('region', ev.x, ev.y)
        
        if region == 'cell':
            col_name = tv.column(tv.identify_column(ev.x), 'id')            
            
            if col_name.startswith('val'):
                col_id = int(col_name[3:])
                item = tv.item(tv.identify_row(ev.y), 'values')
                row_id = int(item[3])
                omid = item[4 + col_id]
                                
                popup_menu = tk.Menu(page_model['tab'], tearoff = 0)                
                popup_menu.add_command(label = f"Informationen bearbeiten", command = lambda: on_comment_clicked(row_id, col_id, omid, item))
                popup_menu.tk_popup(ev.x_root, ev.y_root)
    finally:
        if popup_menu is not None: popup_menu.grab_release()

def on_comment_clicked(mid, cid, omid, item):
    comm = null_or(get_comment(page_model['comment'], page_tid, mid, cid), '')
    
    dlg = tk.Toplevel()
    dlg.title('Zelle bearbeiten')

    tkvar = tk.StringVar(dlg, '--Niemand--')
    choices = ['--Niemand--']
    
    for _, r in page_model['person'].iterrows():
        v = f"{r['mid']}: {r['surname']}, {r['forename']}"
        is_exists = str(r['mid']) == str(mid)
        
        if not is_exists:
            for i in range(page_col_count):
                if item[4 + i] == str(r['mid']):
                    is_exists = True
                    break
        
        if str(r['mid']) == str(omid) or not is_exists:
            choices.append(v)
            if str(r['mid']) == str(omid): tkvar.set(v)

    dropdown = tk.OptionMenu(dlg, tkvar, *choices)
    tk.Label(dlg, text = "Wähle eine Person").grid(row = 0, column = 0)
    dropdown.grid(row = 0, column = 1)

    evar = tk.StringVar(dlg, value = comm)
    ent = tk.Entry(dlg, textvariable = evar)
    
    tk.Label(dlg, text = 'Kommentar: ').grid(row = 1, column = 0)
    ent.grid(row = 1, column = 1)
    
    entries = { 'comm': evar, 'person': tkvar }
    tk.Button(dlg, text = 'Save', command = lambda: on_comment(dlg, entries, mid, cid)).grid(row = 2, column = 1)

def on_comment(dlg, entries, mid, cid):
    comm = entries['comm'].get()
    comm_df = page_model['comment']
    is_add = get_comment(comm_df, page_tid, mid, cid) is None
    
    if is_add:
        rec_dict = {
            'tid': page_tid,
            'mid': mid,
            'cid': cid,
            'val': comm
        }
        page_model['comment'] = pd.concat([comm_df, pd.Series(rec_dict).to_frame().T], ignore_index = True)
    else:
        for _, r in comm_df.iterrows():
            if int(r['tid']) == int(page_tid) and int(r['mid']) == int(mid) and int(r['cid']) == int(cid):
                idx = r.name
                break
        
        comm_df.at[idx, 'val'] = comm
    
    choice = null_or(entries['person'].get(), '')
    
    if choice != '' and choice != '--Niemand--':
        omid = int(choice.split(':')[0])
    else:
        omid = 0
        
    df = page_model['backbone']
    idx = df[df['mid'] == mid].index[0]
    df.at[idx, f"val{cid}"] = omid

    dlg.destroy()
    
    add_history()
    update_pending(True)
    update_treeview()

def on_enter(ev):
    page_model['hoverdlg'].hide_tooltip()
    
    try:
        tv = page_model['treeview']        
        
        col_id = tv.column(tv.identify_column(ev.x), "id")        
        if not col_id.startswith('val'): return
        
        col_id = col_id[3:]
        row_id = tv.item(tv.identify_row(ev.y), 'values')[3]
        person_id = tv.item(tv.identify_row(ev.y), 'values')[int(col_id) + 4]
        
        msg = ''        
        person = get_person(page_model['person'], person_id)        
        if person is not None: msg = 'Name: ' + person['surname'] + ' ' + person['forename']
        
        comm = get_comment(page_model['comment'], page_tid, row_id, col_id) or ''
        
        if comm != '':
            comm = 'Comment: ' + comm
            
            if msg == '':
                msg = comm
            else:
                msg += '\n' + comm
        
        if msg == '': return
        
        x = tv.winfo_pointerx() + 10
        y = tv.winfo_pointery() + 10
        
        page_model['hoverdlg'].show_tooltip(msg, x, y)
    except Exception:
        pass

def on_leave(event):
    page_model['hoverdlg'].hide_tooltip()
    
def on_treeview_dbl_clicked(tv, item, col_id):
    if not item or not col_id: return
    
    try:
        col_name = tv.column(col_id, 'id')
        col_id = int(col_name[3:])
    except Exception:
        return
            
    item = tv.item(item, 'values')
    row_id = int(item[3])
    omid = item[4 + col_id]
                    
    on_comment_clicked(row_id, col_id, omid, item)

def on_edit_line_clicked():
    tv = page_model['treeview']
    
    try:
        item = tv.selection()[0]
        on_treeview_dbl_clicked(tv, item)
    except Exception:
        messagebox.showerror('Fehler', 'Bitte wählen Sie zunächst eine Zeile aus.')

def on_save_db_clicked():
    df = page_model['backbone']
    records = []
    
    for _, row in df.iterrows():
        mid = row['mid']
        
        records.append(tuple(
            [mid] +
            [get_int_nzoe(row[f"val{i}"]) for i in range(page_col_count)]
        ))            
    
    person_match_df = pd.DataFrame(records, columns = ['mid'] + [f"val{i + 1}" for i in range(page_col_count)])
    
    if not save_table(page_tbl, person_match_df):
        messagebox.showerror('Fehler', 'tbl_person_match konnte nicht gespeichert werden.')
        return

    if not save_table('tbl_comment', page_model['comment']):
        messagebox.showerror('Fehler', 'tbl_comment konnte nicht gespeichert werden.')
        return

    bkup_db()
    update_pending(False)
    
    messagebox.showinfo('Erfolg', 'Datenbank erfolgreich gespeichert.')
    
def on_edit(dlg, entries, tags):
    tv = page_model['treeview']
    column_info = page_model['column_info']
    df = page_model['backbone']
    
    item = tags[0]
    idx = int(tv.item(item, 'values')[0]) - 1
    rec_dict = {}
    
    for key, evar in entries.items():
        ci = find_info_by_column_key(column_info, key)
        v = evar.get()
        rv, err = check_ci_validation(ci, v)
        
        if err is not None:
            messagebox.showerror('Eingabefehler', err)
            dlg.destroy()
            return
        else:
            rec_dict[key] = rv
    
    for key, rv in rec_dict.items():
        df.at[idx, key] = rv

    dlg.destroy()
    
    add_history()
    update_pending(True)
    update_treeview()

def update_treeview(callback = None):
    tv = page_model['treeview']
    tv.delete(*tv.get_children())

    df = page_model['backbone']
        
    for i, row in df.iterrows():
        tv.insert(
            '', 'end', values = tuple(
                [i + 1, row['surname'], row['forename'], row['mid']] +
                [int_nonzero_or_empty(row[f"val{k}"]) for k in range(page_col_count)]
            )
        )

    if callback: callback()

def reset_history():
    page_model['history'].clear()
    page_model['history_pos'] = -1
    
    add_history()
    
    page_model['buttons']['Undo']['state'] = 'disabled'
    page_model['buttons']['Redo']['state'] = 'disabled'

def add_history():    
    history = page_model['history']
    
    history = history[:page_model['history_pos'] + 1]
    history.append((copy.deepcopy(page_model['backbone']), copy.deepcopy(page_model['comment'])))
    
    page_model['history'] = history
    page_model['history_pos'] = len(history) - 1
    
    page_model['buttons']['Undo']['state'] = 'normal'
    page_model['buttons']['Redo']['state'] = 'disabled'
    
def backward_history():
    history_pos = page_model['history_pos']
    if history_pos <= 0: return False
    
    history_pos -= 1
    page_model['backbone'], page_model['comment'] = copy.deepcopy(page_model['history'][history_pos])
    page_model['history_pos'] = history_pos
    
    update_pending(True)
    update_treeview()
    
    page_model['buttons']['Undo']['state'] = 'normal' if history_pos > 0 else 'disabled'
    page_model['buttons']['Redo']['state'] = 'normal'
    
    return True

def forward_history():
    history_pos = page_model['history_pos']
    if history_pos >= len(page_model['history']) - 1: return False
    
    history_pos += 1
    page_model['backbone'], page_model['comment'] = copy.deepcopy(page_model['history'][history_pos])
    page_model['history_pos'] = history_pos
    
    update_pending(True)
    update_treeview()
    
    page_model['buttons']['Undo']['state'] = 'normal'
    page_model['buttons']['Redo']['state'] = 'normal' if history_pos < len(page_model['history']) - 1 else 'disabled'
    
    return True