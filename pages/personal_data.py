
""" Personal-Data Tab Page
"""

from tkinter import filedialog, messagebox, Frame
from constant import *
from model import *
from util import *
from ui import *
import pandas as pd
import shutil
import copy
import glob
import os

page_model = {
    'backbone': None,
    'is_excel': False,
    'treeview': None,
    'column_info': [
        ('line', { 'title': 'Nr', 'width': 60 }),
        ('surname', { 'title': 'Nachname', 'editable': True }),
        ('forename', { 'title': 'Vorname', 'editable': True }),
        ('mid', { 'title': 'Member-ID', 'editable': True, 'dtype': int }),
        ('branch', { 'title': 'Branchen', 'editable': True, 'dtype': str })
    ],
    'history': [],
    'history_pos': 0,
    'buttons': None
}

def init_tab(notebook):
    tab = create_tab(notebook, 'Personen-Infos', on_tab_selected, on_save_database)

    top_frame = Frame(tab, height = 700)
    top_frame.pack_propagate(False)
    top_frame.pack(fill = 'x', expand = False)
    
    tv, _ = create_treeview(
        master = top_frame,
        column_info = page_model['column_info'],
        dbl_click_callback = on_treeview_dbl_clicked,
        disable_hscroll = True
    )
    page_model['buttons'] = create_control_panel(
        master = tab,
        button_info = {
            'SQL-Datenbank\nladen': { 'click': on_load_database_clicked },
            'Excel-Datenbank\nladen': { 'click': on_load_excel_clicked },
            'Kontakte aus CSV\nimportieren': { 'click': on_import_csv_clicked },
            'Datenbank\nspeichern': { 'click': on_save_database },
            'Wiederherstellen\naus Backup': { 'click': on_restore_database },
            'Neue Zeile\nhinzufügen': { 'click': on_add_line_clicked },
            'Zeile\nbearbeiten': { 'click': on_edit_line_clicked },
            'Zeile\nlöschen': { 'click': on_delete_line_clicked },
            'Nächste freie\nMember-ID anzeigen': { 'click': on_next_mid_clicked },
            'Undo': { 'click': on_undo_clicked },
            'Redo': { 'click': on_redo_clicked }
        }
    )
    tv.tag_configure('dup_full', background = 'salmon')
    tv.tag_configure('dup_name', background = 'light blue')
    tv.tag_configure('dup_mid', background = 'orange')
    tv.tag_configure('null_mid', background = 'pink')
    
    page_model['treeview'] = tv
    on_tab_selected()

def on_tab_selected():
    on_load_database_clicked(True)

def on_treeview_dbl_clicked(tv, item, col_id):
    if not item:
        messagebox.showerror('Fehler', 'Keine Zeile ausgewählt.')
        return

    values = tv.item(item, 'values')
    default_values = []
    
    for i, ci in enumerate(page_model['column_info']):
        key, info = ci        
        v = values[i]
        
        default_values.append(v)
    
    show_entry_dlg(False, default_values, page_model['column_info'], on_edit, tags = (item, ))

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

def on_add(dlg, entries, tags):
    column_info = page_model['column_info']
    df = page_model['backbone']
    
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
    
    rec_dict['display'] = max(list(df['display'])) + 1 if len(df) > 0 else 1
    page_model['backbone'] = pd.concat([df, pd.Series(rec_dict).to_frame().T], ignore_index = True)
    
    dlg.destroy()
    
    add_history()    
    update_pending(True)
    update_treeview()

def on_load_excel_clicked():
    xls_path = filedialog.askopenfilename(title = 'Wählen Sie eine Excel-Datei aus', filetypes = [('Excel-Dateien', '*.xlsx')])
    if xls_path is None or not os.path.exists(xls_path): return
    
    try:
        df = pd.read_excel(xls_path)
        df = df.rename(columns = {'Forename': 'forename', 'Surname': 'surname', 'Member_ID': 'mid', 'Branch': 'branch'})
        
        df['display'] = range(1, len(df) + 1)
    except Exception:
        messagebox.showerror('Fehler', 'Fehler beim Laden der Excel-Datei.')
        return
    
    page_model['backbone'] = df
    page_model['is_excel'] = True
    
    reset_history()
    update_pending(True)
    update_treeview(lambda: messagebox.showinfo('Erfolg', 'Excel-Datei erfolgreich geladen.'))

def on_load_database_clicked(is_init = False):
    page_model['backbone'] = load_table('tbl_person', 'display')
    page_model['is_excel'] = False
    
    reset_history()
    update_pending(False)
    update_treeview(None if is_init else lambda: messagebox.showinfo('Erfolg', 'SQL-Datenbank erfolgreich geladen.'))

def on_import_csv_clicked():
    csv_path = filedialog.askopenfilename(title = 'Wählen Sie eine CSV-Datei aus', filetypes = [('CSV-Datei', '*.csv')])
    if csv_path is None or not os.path.exists(csv_path): return
    
    try:
        contact_df = pd.read_csv(csv_path)        
        contact_df = contact_df.rename(columns = {'Vorname': 'forename', 'Nachname': 'surname', 'Mitgliedernummer': 'mid', 'Branche': 'branch'})

        try:
            contact_df['mid'] = pd.to_numeric(contact_df['mid'], errors = 'coerce').fillna(0).astype('int64')
            contact_df = contact_df.drop_duplicates(subset = ['mid', 'forename', 'surname'])
            
            if len(contact_df[contact_df['mid'] == 0]) > 0:
                messagebox.showerror('Importfehler', 'Es existiert ein Kontakt mit MemberID=0, der nicht erlaubt ist.')
                return                
            
            df = page_model['backbone']
            did = max(list(df['display'])) + 1 if len(df) > 0 else 1
            
            for i, cr in contact_df.iterrows():
                r = {
                    'forename': cr['forename'],
                    'surname': cr['surname'],
                    'mid': cr['mid'],
                    'branch': cr['branch'],
                    'display': did + i
                }
                df = pd.concat([df, pd.Series(r).to_frame().T], ignore_index = True)
            
            page_model['backbone'] = df.drop_duplicates(subset = ['mid', 'forename', 'surname'])
            page_model['is_excel'] = False
            
            reset_history()
            update_pending(True)
            update_treeview(lambda: messagebox.showinfo('Erfolg', 'Kontakte erfolgreich importiert.'))            
        except pd.errors.IntCastingNaNError as e:
            messagebox.showerror('Importfehler', 'Nicht numerische Werte in der Spalte Member_ID.')
            return
    except Exception:
        messagebox.showerror('Fehler', 'Fehler beim Laden der CSV-Datei.')
        return

def on_add_line_clicked():
    column_info = page_model['column_info']
    show_entry_dlg(True, ['' for _ in column_info], column_info, on_add)

def on_edit_line_clicked():
    tv = page_model['treeview']
    
    try:
        item = tv.selection()[0]
        on_treeview_dbl_clicked(tv, item, 0)
    except Exception:
        messagebox.showerror('Fehler', 'Bitte wählen Sie zunächst eine Zeile aus.')

def on_delete_line_clicked():
    tv = page_model['treeview']
    df = page_model['backbone']
    
    items = tv.selection()
    
    if not items:
        messagebox.showerror('Fehler', 'Bitte wählen Sie die zu löschende(n) Zeile(n) aus.')
        return

    indices = [df.index[int(tv.item(it, 'values')[0]) - 1] for it in items]    
    page_model['backbone'] = df.drop(indices).reset_index(drop = True)

    add_history()
    update_pending(True)
    update_treeview()

def on_next_mid_clicked():
    df = page_model['backbone']
    mid = max(list(df['mid'])) + 1 if len(df) > 0 else 1
    
    messagebox.showinfo('Info', f"Die nächste freie Member_ID ist {mid}.")

def on_undo_clicked():
    backward_history()

def on_redo_clicked():
    forward_history()

def on_restore_database():
    choices = []
    g = glob.glob('./bkup/*.db')
    
    if len(g) == 0:
        messagebox.showerror('Keine Sicherung', 'Im Sicherungsordner wurde keine Datenbank gefunden.')
        return
    
    dlg = tk.Toplevel()
    dlg.title('DB wiederherstellen')

    tkvar = tk.StringVar(dlg)

    for f in sorted(g):
        f = f.replace('\\', '/').split('/')[-1][:-3]
        choices.append(f)
    
    dropdown = tk.OptionMenu(dlg, tkvar, *choices)
    tk.Label(dlg, text = "Wählen Sie Datum").grid(row = 0, column = 0)
    dropdown.grid(row = 0, column = 1)

    entries = { 'date': tkvar }
    tk.Button(dlg, text = 'Wiederherstellen', command = lambda: on_restore(dlg, entries)).grid(row = 1, column = 1)

def on_restore(dlg, entries):
    dt = entries['date'].get()
    dlg.destroy()
    
    if dt is not None and dt != '':
        f = './bkup/{}.db'.format(dt)
        
        if os.path.exists(f):
            shutil.copy(f, local_db_path)
            
            close_db()
            load_or_create_db()
            on_load_database_clicked()

def on_save_database():
    df = page_model['backbone']
    
    if True in set(df['null_mid']):
        messagebox.showerror('Fehler', 'Es gibt Zeilen mit null Mitglieds-IDs.\nBitte beheben Sie das Problem und versuchen Sie es erneut.')
        return
    
    if True in (set(df['dup_full']) | set(df['dup_mid'])):
        messagebox.showerror('Fehler', 'Es gibt Zeilen mit doppelten Mitglieds-IDs.\nBitte beheben Sie das Problem und versuchen Sie es erneut.')
        return
    
    if True in set(df['dup_name']):
        if not messagebox.askyesno('Doppelter Name', 'Es sind Zeilen mit demselben Namen vorhanden.\nWerden Sie mit dem Speichern fortfahren?'):
            return

    ev_cols = [col for col in sorted(list(df.columns)) if col.startswith('Event-')]    
    person_records, ev_records, person_ev_records, match_records, no_match_records, never_match_records, sel_records = [], [], [], [], [], [], []
    
    for _, row in df.iterrows():
        person_records.append((
            row['mid'], row['surname'], row['forename'], row['branch'], row['display']
        ))
        
        if page_model['is_excel']:
            sel_records.append((
                row['mid'], null_or(row['Selection'], 0)
            ))
            match_records.append(tuple([row['mid']] + [null_or(row[f"Match_{k + 1}"], 0) for k in range(match_col_count)]))
            no_match_records.append(tuple([row['mid']] + [null_or(row[f"No_Match_{k + 1}"], 0) for k in range(no_match_col_count)]))
            never_match_records.append(tuple([row['mid']] + [null_or(row[f"Never_Match_{k + 1}"], 0) for k in range(never_match_col_count)]))

            for i, col in enumerate(ev_cols):
                person_ev_records.append((
                    row['mid'], i + 1, null_or(row[col], 0)
                ))

    if page_model['is_excel']:
        for i, col in enumerate(ev_cols):
            ev_records.append((
                i + 1, col[6:], i + 1                
            ))

    person_df = pd.DataFrame(person_records, columns = ['mid', 'surname', 'forename', 'branch', 'display'])

    tbl_df_dict = {
        'tbl_person': person_df,
        'tbl_person_selection': pd.DataFrame(sel_records, columns = ['mid', 'val']),
        'tbl_event': pd.DataFrame(ev_records, columns = ['eid', 'title', 'display']),
        'tbl_person_event': pd.DataFrame(person_ev_records, columns = ['mid', 'eid', 'val']),
        'tbl_person_match': pd.DataFrame(match_records, columns = ['mid'] + [f"val{k + 1}" for k in range(match_col_count)]),
        'tbl_person_no_match': pd.DataFrame(no_match_records, columns = ['mid'] + [f"val{k + 1}" for k in range(no_match_col_count)]),
        'tbl_person_never_match': pd.DataFrame(never_match_records, columns = ['mid'] + [f"val{k + 1}" for k in range(never_match_col_count)])
    } if page_model['is_excel'] else {
        'tbl_person': person_df
    }        
    for tbl, df in tbl_df_dict.items():
        if not save_table(tbl, df):
            messagebox.showerror('Fehler', f"{tbl} konnte nicht gespeichert werden.")
            return
    
    bkup_db()
    update_pending(False)
    
    messagebox.showinfo('Erfolg', 'Datenbank erfolgreich gespeichert.')
    
def update_treeview(callback = None):
    tv = page_model['treeview']
    tv.delete(*tv.get_children())

    df = page_model['backbone']
    page_model['backbone'] = df = df.sort_values(by = ['surname', 'forename', 'mid'])
    df.reset_index(drop = True, inplace = True)

    df['dup_full'] = df.duplicated(subset = ['forename', 'surname', 'mid'], keep = False)
    df['dup_name'] = df.duplicated(subset = ['forename', 'surname'], keep = False)
    df['dup_mid'] = df.duplicated(subset = ['mid'], keep = False)
    df['null_mid'] = df['mid'].isnull()

    for i, row in df.iterrows():
        if row['dup_full']:
            tags = ('dup_full',)
        elif row['dup_name']:
            tags = ('dup_name',)
        elif row['dup_mid']:
            tags = ('dup_mid',)
        elif row['null_mid']:
            tags = ('null_mid',)
        else:
            tags = ()

        tv.insert(
            '', 'end', values = (
                i + 1, row['surname'], row['forename'], row['mid'], row['branch']
            ),
            tags = tags
        )

    if callback: callback()

def reset_history():
    page_model['history'].clear()
    page_model['history_pos'] = -1
    
    add_history()
    
    page_model['buttons']['Undo']['state'] = 'disabled'
    page_model['buttons']['Redo']['state'] = 'disabled'

def add_history():
    df = copy.deepcopy(page_model['backbone'])
    history = page_model['history']
    
    history = history[:page_model['history_pos'] + 1]
    history.append((df, page_model['is_excel']))
    
    page_model['history'] = history
    page_model['history_pos'] = len(history) - 1
    
    page_model['buttons']['Undo']['state'] = 'normal'
    page_model['buttons']['Redo']['state'] = 'disabled'

def backward_history():
    history_pos = page_model['history_pos']
    if history_pos <= 0: return False
    
    history_pos -= 1
    page_model['backbone'], page_model['is_excel'] = copy.deepcopy(page_model['history'][history_pos])
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
    page_model['backbone'], page_model['is_excel'] = copy.deepcopy(page_model['history'][history_pos])
    page_model['history_pos'] = history_pos
    
    update_pending(True)
    update_treeview()
    
    page_model['buttons']['Undo']['state'] = 'normal'
    page_model['buttons']['Redo']['state'] = 'normal' if history_pos < len(page_model['history']) - 1 else 'disabled'
    
    return True