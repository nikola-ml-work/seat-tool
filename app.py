
from pages import personal_data
from pages import hist_event
from pages import new_event
from tkinter import ttk
from model import *
from util import *
from ui import *
import tkinter as tk
import os

def on_tab_changed(e):
    tab = e.widget.select()
    name = e.widget.tab(tab, "text")
    
    callback = glob_model['tab_callback'][name]    
    if callback: callback()

if not os.path.exists('./out/'): os.mkdir('./out/')

root = tk.Tk()
root.title("Seating Generation")
root.update_idletasks()

new_width = root.winfo_width() * 5
new_height = root.winfo_height() * 4

root.geometry(f"{new_width}x{new_height}")

notebook = ttk.Notebook(root)
notebook.pack(expand = True, fill = 'both', padx = 10, pady = 10)

personal_data.init_tab(notebook)
hist_event.init_tab(notebook)
new_event.init_tab(notebook)

notebook.bind("<<NotebookTabChanged>>", on_tab_changed)
root.mainloop()

close_db(True)
