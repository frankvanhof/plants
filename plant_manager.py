#!/usr/bin/env python3
import json
import os
import sys
import fcntl
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import base64
import requests

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

DATA_FILE = os.path.join(os.path.dirname(__file__), 'plants.json')
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llava"

PLANT_PROFILES = {
    'alocasia': {'summer_interval': 14, 'winter_interval': None, 'water_interval': 7, 'water_amount': 'Royaal (kluit niet laten uitdrogen, geen natte voeten)', 'light_requirement': 'Veel indirect zonlicht, vermijd felle middagzon.', 'care_tips': 'Houdt van een hoge luchtvochtigheid (regelmatig sproeien).'},
    'monstera': {'summer_interval': 21, 'winter_interval': None, 'water_interval': 10, 'water_amount': 'Matig (bovenste laag aarde iets laten opdrogen)', 'light_requirement': 'Indirect licht tot halfschaduw.', 'care_tips': 'Luchtwortels kun je terug de pot in leiden of langs een mosstok binden.'},
    'orchidee': {'summer_interval': 14, 'winter_interval': 28, 'water_interval': 10, 'water_amount': 'Dompelen (ca. 10 minuten en goed laten uitlekken)', 'light_requirement': 'Veel licht, maar geen direct zonlicht (voorkom bladverbranding).', 'care_tips': 'Zorg dat er nooit water in het hart van de plant blijft staan.'},
    'vetplant': {'summer_interval': None, 'winter_interval': None, 'water_interval': 21, 'water_amount': 'Weinig (laat aarde volledig uitdrogen)', 'light_requirement': 'Zoveel mogelijk direct zonlicht.', 'care_tips': 'In de winter vrijwel volledig droog laten staan.'},
    'cactus': {'summer_interval': None, 'winter_interval': None, 'water_interval': 28, 'water_amount': 'Zeer weinig (bijna droog laten staan)', 'light_requirement': 'Volle zon, zeer licht.', 'care_tips': 'Geef liever te weinig dan te veel water.'},
    'standaard': {'summer_interval': 30, 'winter_interval': None, 'water_interval': 7, 'water_amount': 'Matig (standaard waterbehoefte)', 'light_requirement': 'Indirect licht (standaard kameromstandigheden).', 'care_tips': 'Let op gele bladeren (te veel water) of bruine randen (te droog).'}
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

class PlantManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Planten Beheer")
        self.root.geometry("1200x1400")
        
        self.data = load_data()
        self.pending_tasks = [] 
        self.last_image_path = None
        self.current_sort_col = None
        self.current_sort_reverse = False
        
        if not HAS_PIL:
            print("Waarschuwing: Pillow is niet geïnstalleerd. Foto's worden niet weergegeven.")

        style = ttk.Style()
        style.configure("Treeview.Heading", font=('Arial', 10, 'bold'))
        style.configure("Treeview", font=('Arial', 10), rowheight=35) 

        tk.Label(root, text="Huidige Planten & Planning (Dubbelklik voor details):", font=('Arial', 10, 'bold')).pack(pady=(10, 5))
        
        tree_frame = tk.Frame(root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        columns = ('naam', 'water', 'voeding')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        self.tree.heading('naam', text='Plant Naam', anchor=tk.W, command=lambda: self.sort_treeview('naam', False))
        self.tree.heading('water', text='Volgende Water', anchor=tk.CENTER, command=lambda: self.sort_treeview('water', False))
        self.tree.heading('voeding', text='Volgende Voeding', anchor=tk.CENTER, command=lambda: self.sort_treeview('voeding', False))
        
        self.tree.column('naam', width=500, anchor=tk.W, stretch=True)
        self.tree.column('water', width=300, anchor=tk.CENTER, stretch=True)
        self.tree.column('voeding', width=300, anchor=tk.CENTER, stretch=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<Double-1>", self.show_plant_details)
        self.refresh_list()
        self.sort_treeview('water', False)
        
        tk.Label(root, text="Nieuwe plant toevoegen (naam):").pack(pady=(15, 0))
        
        input_frame = tk.Frame(root)
        input_frame.pack(pady=5)
        self.entry_name = tk.Entry(input_frame, width=40)
        self.entry_name.pack(side=tk.LEFT, padx=5)
        
        self.lbl_photo_status = tk.Label(input_frame, text="", fg="green", font=('Arial', 9, 'italic'))
        self.lbl_photo_status.pack(side=tk.LEFT)
        
        frame_buttons = tk.Frame(root)
        frame_buttons.pack(pady=5)
        
        btn_add = tk.Button(frame_buttons, text="Voeg Toe", command=self.add_plant, width=12)
        btn_add.grid(row=0, column=0, padx=5)

        btn_manual_photo = tk.Button(frame_buttons, text="Kies Foto (Handmatig)", command=self.choose_manual_photo, width=20)
        btn_manual_photo.grid(row=0, column=1, padx=5)
        
        btn_ai = tk.Button(frame_buttons, text="Identificeer via Foto (AI)", command=self.identify_with_ai, width=22)
        btn_ai.grid(row=0, column=2, padx=5)
        
        btn_remove = tk.Button(frame_buttons, text="Verwijder Selectie", command=self.remove_plant, width=15)
        btn_remove.grid(row=0, column=3, padx=5)

        tk.Frame(root, height=2, bd=1, relief=tk.SUNKEN).pack(fill=tk.X, padx=20, pady=15)

        tk.Label(root, text="Openstaande Taken (Water & Voeding):", font=('Arial', 10, 'bold')).pack(pady=(0, 0))
        
        task_frame = tk.Frame(root)
        task_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        self.task_listbox = tk.Listbox(task_frame, height=20, bg="#f0f8ff", selectmode=tk.EXTENDED, font=('Arial', 10)) 
        task_scrollbar = ttk.Scrollbar(task_frame, orient=tk.VERTICAL, command=self.task_listbox.yview)
        self.task_listbox.configure(yscrollcommand=task_scrollbar.set)
        
        self.task_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        task_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        btn_done = tk.Button(root, text="✔️ Markeer geselecteerde taak/taken als GEDAAN", command=self.mark_task_done, width=45, font=('Arial', 10, 'bold'), bg="#e6ffe6")
        btn_done.pack(pady=(15, 20))
        
        self.refresh_tasks()

    def sort_treeview(self, col, reverse):
        self.current_sort_col = col
        self.current_sort_reverse = reverse
        
        self.tree.heading('naam', text='Plant Naam', anchor=tk.W)
        self.tree.heading('water', text='Volgende Water', anchor=tk.CENTER)
        self.tree.heading('voeding', text='Volgende Voeding', anchor=tk.CENTER)
        
        indicator = " ▼" if reverse else " ▲"
        if col == 'naam':
            self.tree.heading('naam', text='Plant Naam' + indicator, anchor=tk.W)
        elif col == 'water':
            self.tree.heading('water', text='Volgende Water' + indicator, anchor=tk.CENTER)
        elif col == 'voeding':
            self.tree.heading('voeding', text='Volgende Voeding' + indicator, anchor=tk.CENTER)
            
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        
        if col == 'naam':
            l.sort(key=lambda t: t[0].lower(), reverse=reverse)
        else:
            def date_key(item):
                val = item[0]
                try:
                    return datetime.strptime(val, "%d-%m-%Y")
                except ValueError:
                    return datetime.max if not reverse else datetime.min
            l.sort(key=date_key, reverse=reverse)
            
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)
            
        self.tree.heading(col, command=lambda _col=col: self.sort_treeview(_col, not reverse))

    def choose_manual_photo(self):
        file_path = filedialog.askopenfilename(title="Kies een foto", filetypes=[("Afbeeldingen", "*.jpg *.jpeg *.png"), ("Alle bestanden", "*.*")])
        if file_path:
            self.last_image_path = file_path
            self.lbl_photo_status.config(text="✓ Foto gekoppeld")

    def identify_with_ai(self):
        file_path = filedialog.askopenfilename(title="Kies een foto", filetypes=[("Afbeeldingen", "*.jpg *.jpeg *.png"), ("Alle bestanden", "*.*")])
        if not file_path: return

        self.last_image_path = file_path
        self.lbl_photo_status.config(text="✓ AI Foto gekoppeld")

        self.root.config(cursor="watch")
        self.root.update()

        try:
            with open(file_path, "rb") as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode('utf-8')

            prompt = "Identify this houseplant. Reply ONLY with the common Dutch name or scientific name. No other text, no explanation."
            payload = {"model": OLLAMA_MODEL, "prompt": prompt, "images": [img_base64], "stream": False}
            
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
            response.raise_for_status()
            
            ai_result = response.json().get("response", "").strip()
            if ai_result:
                self.entry_name.delete(0, tk.END)
                self.entry_name.insert(0, ai_result)
                messagebox.showinfo("AI Resultaat", f"Plant herkend als: {ai_result}")
            else:
                messagebox.showwarning("AI Fout", "Geen naam gegenereerd.")

        except Exception as e:
            messagebox.showerror("Fout", f"AI identificatie mislukt:\n{e}")
        finally:
            self.root.config(cursor="")

    def add_plant(self):
        name = self.entry_name.get().strip()
        if not name: return
        if name in self.data: 
            messagebox.showwarning("Dubbel", "Deze plant bestaat al.")
            return
        
        profile, bron = self.get_profile(name)
        today = datetime.now().strftime("%Y-%m-%d")
        
        self.data[name] = {
            "last_fertilized": today, 
            "summer_interval": profile['summer_interval'], 
            "winter_interval": profile['winter_interval'],
            "last_watered": today, 
            "water_interval": profile['water_interval'], 
            "water_amount": profile['water_amount'],
            "light_requirement": profile['light_requirement'],
            "care_tips": profile['care_tips'],
            "image_path": self.last_image_path
        }
        
        save_data(self.data)
        self.refresh_list()
        self.refresh_tasks() 
        self.entry_name.delete(0, tk.END)
        self.last_image_path = None
        self.lbl_photo_status.config(text="")
        messagebox.showinfo("Succes", f"'{name}' is toegevoegd.\nSchema gebaseerd op: {bron}.")

    def update_plant_image(self, plant_name, modal_window, img_frame_widget):
        modal_window.grab_release()
        
        file_path = filedialog.askopenfilename(
            parent=modal_window, 
            title="Kies een nieuwe foto", 
            filetypes=[("Afbeeldingen", "*.jpg *.jpeg *.png"), ("Alle bestanden", "*.*")]
        )
        
        if not file_path: 
            modal_window.grab_set()
            return
            
        self.data[plant_name]['image_path'] = file_path
        save_data(self.data)
        modal_window.destroy()
        self._open_details_modal(plant_name)

    def show_plant_details(self, event):
        selected = self.tree.selection()
        if not selected: return
        
        item = selected[0]
        name = self.tree.item(item, 'values')[0]
        self._open_details_modal(name)

    def _open_details_modal(self, name):
        data = self.data.get(name)
        if not data: return
        
        modal = tk.Toplevel(self.root)
        modal.title(f"Details: {name}")
        modal.geometry("800x650") 
        modal.transient(self.root)
        
        tk.Label(modal, text=f"🌱 {name}", font=('Arial', 14, 'bold')).pack(pady=15)
        
        main_frame = tk.Frame(modal, padx=30)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        info_frame = tk.Frame(main_frame)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        img_frame = tk.Frame(main_frame, width=300)
        img_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        
        light = data.get('light_requirement', 'Onbekend (Voeg opnieuw toe via AI voor details).')
        tips = data.get('care_tips', 'Geen extra tips beschikbaar.')
        water = data.get('water_amount', 'Onbekend')
        
        tk.Label(info_frame, text="☀️ Lichtbehoefte:", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(5, 2))
        tk.Label(info_frame, text=light, font=('Arial', 10), wraplength=400, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 15))
        
        tk.Label(info_frame, text="💧 Water Advies:", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(0, 2))
        tk.Label(info_frame, text=water, font=('Arial', 10), wraplength=400, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 15))
        
        tk.Label(info_frame, text="💡 Extra Verzorgingstips:", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(0, 2))
        tk.Label(info_frame, text=tips, font=('Arial', 10), wraplength=400, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 20))
        
        img_path = data.get('image_path')
        
        if not HAS_PIL:
            waarschuwing = "⚠️ FOTO KAN NIET GETOOND WORDEN\n\nDe bibliotheek 'Pillow' ontbreekt.\nOpen je terminal en run:\n\nsudo apt install python3-pil python3-pil.imagetk"
            tk.Label(img_frame, text=waarschuwing, fg="red", font=('Arial', 10, 'bold'), justify=tk.CENTER).pack(pady=30)
        elif img_path and os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                img.thumbnail((250, 250)) 
                photo = ImageTk.PhotoImage(img)
                lbl_img = tk.Label(img_frame, image=photo, bg="white", relief=tk.SOLID, borderwidth=1)
                lbl_img.image = photo 
                lbl_img.pack(pady=5)
            except Exception as e:
                tk.Label(img_frame, text=f"Fout bij laden foto", fg="red").pack(pady=30)
        else:
            tk.Label(img_frame, text="Geen foto beschikbaar", fg="gray").pack(pady=30)
            
        tk.Button(img_frame, text="Wijzig / Voeg Foto Toe", command=lambda: self.update_plant_image(name, modal, img_frame)).pack(pady=10)
        
        tk.Button(modal, text="Sluiten", command=modal.destroy, width=15).pack(pady=10)
        
        modal.update_idletasks()
        modal.grab_set()
        modal.focus_set()

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        today = datetime.now()
        is_winter = today.month in [11, 12, 1, 2]
        
        for plant in sorted(self.data.keys()):
            data = self.data[plant]
            
            # 1. Bepaal het volgende water moment
            try:
                last_watered = datetime.strptime(data['last_watered'], "%Y-%m-%d")
                next_water = last_watered + timedelta(days=data['water_interval'])
                water_str = next_water.strftime("%d-%m-%Y")
            except:
                water_str = "??"
                next_water = None

            # 2. Bepaal het voeding moment en sync dit direct met de water cyclus
            fert_interval = data['winter_interval'] if is_winter else data['summer_interval']
            if fert_interval is not None and next_water is not None:
                try:
                    last_fert = datetime.strptime(data['last_fertilized'], "%Y-%m-%d")
                    ideal_next_fert = last_fert + timedelta(days=fert_interval)
                    
                    # Zorg dat bemesten ALTIJD gelijk valt met een water-dag
                    sync_fert = next_water
                    while sync_fert < ideal_next_fert:
                        sync_fert += timedelta(days=data['water_interval'])
                        
                    fert_str = sync_fert.strftime("%d-%m-%Y")
                except:
                    fert_str = "??"
            else:
                fert_str = "Rustperiode (Geen)"
                
            self.tree.insert('', tk.END, values=(plant, water_str, fert_str))
            
        if self.current_sort_col:
            self.sort_treeview(self.current_sort_col, self.current_sort_reverse)

    def refresh_tasks(self):
        self.task_listbox.delete(0, tk.END)
        self.pending_tasks.clear()
        
        today = datetime.now()
        is_winter = today.month in [11, 12, 1, 2]
        
        for plant, data in self.data.items():
            last_watered = datetime.strptime(data['last_watered'], "%Y-%m-%d")
            next_water = last_watered + timedelta(days=data['water_interval'])
            
            # Alleen taken tonen als de plant WATER nodig heeft
            if today >= next_water:
                overdue_water = (today - next_water).days
                
                fert_interval = data['winter_interval'] if is_winter else data['summer_interval']
                fert_due = False
                
                if fert_interval is not None:
                    last_fert = datetime.strptime(data['last_fertilized'], "%Y-%m-%d")
                    ideal_next_fert = last_fert + timedelta(days=fert_interval)
                    
                    # Sync logica (wacht op bewateringsmoment)
                    sync_fert = next_water
                    while sync_fert < ideal_next_fert:
                        sync_fert += timedelta(days=data['water_interval'])
                        
                    # Als de gesynchroniseerde bemestingsdag ook bereikt is
                    if today >= sync_fert:
                        fert_due = True
                
                # Gecombineerde taak als vloeibare voeding ook nodig is
                if fert_due:
                    self.pending_tasks.append({'plant': plant, 'type': 'both'})
                    self.task_listbox.insert(tk.END, f"💧 WATER + 🧪 VLOEIBARE MEST: {plant} ({overdue_water} dagen te laat)")
                else:
                    self.pending_tasks.append({'plant': plant, 'type': 'water'})
                    self.task_listbox.insert(tk.END, f"💧 WATER: {plant} ({overdue_water} dagen te laat)")
                    
        if not self.pending_tasks:
            self.task_listbox.insert(tk.END, "🎉 Alle planten zijn verzorgd! Er zijn momenteel geen taken.")

    def mark_task_done(self):
        selected_indices = self.task_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selectie Fout", "Selecteer eerst minimaal één taak in de lijst (gebruik Ctrl voor meerdere).")
            return
            
        tasks_completed = 0
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        for idx in selected_indices:
            if idx >= len(self.pending_tasks):
                continue 
                
            task = self.pending_tasks[idx]
            plant = task['plant']
            task_type = task['type']
            
            if task_type == 'water':
                self.data[plant]['last_watered'] = today_str
            elif task_type == 'voeding':
                self.data[plant]['last_fertilized'] = today_str
            elif task_type == 'both':
                # Reset beide tellers tegelijk!
                self.data[plant]['last_watered'] = today_str
                self.data[plant]['last_fertilized'] = today_str
                
            tasks_completed += 1
            
        if tasks_completed > 0:
            save_data(self.data)
            self.refresh_tasks()
            self.refresh_list()
            messagebox.showinfo("Succes", f"Er zijn {tasks_completed} ta(a)k(en) afgevinkt. De data zijn gereset naar vandaag.")

    def fetch_profile_via_ai(self, plant_name):
        prompt = (
            f"Je bent een botanisch expert. Geef de verzorgingsbehoefte voor de kamerplant '{plant_name}'. "
            "Antwoord UITSLUITEND met geldige JSON. Geef geen introductie, geen markdown, en geen extra tekst. "
            "Regels:\n"
            "- \"summer_interval\": aantal dagen tussen voeding in zomer (integer > 0). Mag null zijn, maar planten hebben in de zomer vaker voeding nodig dan in de winter!\n"
            "- \"winter_interval\": aantal dagen tussen voeding in winter (integer > 0) of null.\n"
            "- \"water_interval\": aantal dagen tussen water geven (integer > 0).\n"
            "- \"water_amount\": Korte, logische Nederlandse zin over de hoeveelheid water (string).\n"
            "- \"light_requirement\": Korte Nederlandse zin over lichtbehoefte, bijv 'Veel indirect licht' (string).\n"
            "- \"care_tips\": Een of twee korte extra verzorgingstips in het Nederlands (string).\n"
            "Zorg dat summer_interval NOOIT null is als winter_interval wel een getal heeft."
        )
        
        payload = {
            "model": OLLAMA_MODEL, 
            "prompt": prompt, 
            "stream": False,
            "options": {"temperature": 0.1}
        }
        
        try:
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=20)
            response.raise_for_status()
            ai_result = response.json().get("response", "").strip()
            
            if ai_result.startswith("```"):
                ai_result = ai_result.strip("`").replace("json", "", 1).strip()
                
            profile = json.loads(ai_result)
            required_keys = ['summer_interval', 'winter_interval', 'water_interval', 'water_amount']
            
            if all(key in profile for key in required_keys):
                w_int = profile.get('water_interval')
                s_int = profile.get('summer_interval')
                wi_int = profile.get('winter_interval')
                
                if not isinstance(w_int, int) or w_int <= 0:
                    return None
                    
                if s_int is None and isinstance(wi_int, int):
                    s_int = wi_int
                    wi_int = None
                    profile['summer_interval'] = s_int
                    profile['winter_interval'] = wi_int
                    
                if s_int is not None and (not isinstance(s_int, int) or s_int <= 0):
                    return None
                if wi_int is not None and (not isinstance(wi_int, int) or wi_int <= 0):
                    return None
                    
                if not isinstance(profile['water_amount'], str) or len(profile['water_amount']) < 5:
                    profile['water_amount'] = "Matig water geven."
                    
                if 'light_requirement' not in profile:
                    profile['light_requirement'] = "Onbekend"
                if 'care_tips' not in profile:
                    profile['care_tips'] = "Geen extra tips gegenereerd."
                    
                return profile
                
        except json.JSONDecodeError:
            print("AI retourneerde geen geldige JSON. Terugval naar standaardprofiel.")
        except Exception as e:
            print(f"AI profiel generatie mislukt: {e}. Terugval naar standaardprofiel.")
        
        return None

    def get_profile(self, name):
        name_lower = name.lower()
        for key, profile in PLANT_PROFILES.items():
            if key in name_lower:
                return profile, f"lokaal profiel '{key}'"
        
        self.root.config(cursor="watch")
        self.root.update()
        ai_profile = self.fetch_profile_via_ai(name)
        self.root.config(cursor="")
        
        if ai_profile:
            return ai_profile, "AI gegenereerd (internetkennis)"
            
        standaard = {'summer_interval': 30, 'winter_interval': None, 'water_interval': 7, 'water_amount': 'Matig (standaard waterbehoefte)', 'light_requirement': 'Indirect licht', 'care_tips': 'Geen'}
        return standaard, "standaard fallback (AI onbereikbaar)"

    def remove_plant(self):
        selected = self.tree.selection()
        if not selected: return
        
        item = selected[0]
        name = self.tree.item(item, 'values')[0]
        
        confirm_dialog = tk.Toplevel(self.root)
        confirm_dialog.title("Bevestigen")
        confirm_dialog.geometry("500x250")
        confirm_dialog.transient(self.root)
        
        tk.Label(confirm_dialog, text=f"Weet je zeker dat je '{name}' wilt verwijderen?", font=('Arial', 12, 'bold'), wraplength=450, justify=tk.CENTER).pack(pady=(25, 20))
        
        btn_frame = tk.Frame(confirm_dialog)
        btn_frame.pack(pady=10)
        
        def execute_delete():
            del self.data[name]
            save_data(self.data)
            self.refresh_list()
            self.refresh_tasks()
            confirm_dialog.destroy()
            
        tk.Button(btn_frame, text="Ja", command=execute_delete, width=12, bg="#ffcccc").pack(side=tk.LEFT, padx=15)
        tk.Button(btn_frame, text="Nee", command=confirm_dialog.destroy, width=12).pack(side=tk.RIGHT, padx=15)
        
        confirm_dialog.update_idletasks()
        confirm_dialog.grab_set()
        confirm_dialog.focus_set()

if __name__ == "__main__":
    lock_file_path = os.path.join(os.path.dirname(__file__), '.plant_manager.lock')
    lock_file = open(lock_file_path, 'w')
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        temp_root = tk.Tk()
        temp_root.withdraw()
        messagebox.showinfo("Planten Beheer", "De applicatie is al geopend.")
        sys.exit(1)

    root = tk.Tk()
    app = PlantManager(root)
    root.mainloop()