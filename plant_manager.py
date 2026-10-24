#!/usr/bin/env python3
import json
import os
import sys
import fcntl
import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime, timedelta
import base64
import requests

DATA_FILE = os.path.join(os.path.dirname(__file__), 'plants.json')
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llava"

PLANT_PROFILES = {
    'alocasia': {'summer_interval': 14, 'winter_interval': None, 'water_interval': 7, 'water_amount': 'Royaal (kluit niet laten uitdrogen, geen natte voeten)'},
    'monstera': {'summer_interval': 21, 'winter_interval': None, 'water_interval': 10, 'water_amount': 'Matig (bovenste laag aarde iets laten opdrogen)'},
    'orchidee': {'summer_interval': 14, 'winter_interval': 28, 'water_interval': 10, 'water_amount': 'Dompelen (ca. 10 minuten en goed laten uitlekken)'},
    'vetplant': {'summer_interval': None, 'winter_interval': None, 'water_interval': 21, 'water_amount': 'Weinig (laat aarde volledig uitdrogen)'},
    'cactus': {'summer_interval': None, 'winter_interval': None, 'water_interval': 28, 'water_amount': 'Zeer weinig (bijna droog laten staan)'},
    'standaard': {'summer_interval': 30, 'winter_interval': None, 'water_interval': 7, 'water_amount': 'Matig (standaard waterbehoefte)'}
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
        
        # --- SECTIE 1: PLANTEN BEHEER ---
        tk.Label(root, text="Huidige Planten:", font=('Arial', 10, 'bold')).pack(pady=(10, 0))
        self.listbox = tk.Listbox(root, width=120, height=15)
        self.listbox.pack(pady=5)
        self.refresh_list()
        
        tk.Label(root, text="Nieuwe plant toevoegen:").pack(pady=(5, 0))
        self.entry_name = tk.Entry(root, width=40)
        self.entry_name.pack(pady=5)
        
        frame_buttons = tk.Frame(root)
        frame_buttons.pack(pady=5)
        
        btn_add = tk.Button(frame_buttons, text="Voeg Toe", command=self.add_plant, width=15)
        btn_add.grid(row=0, column=0, padx=5)
        
        btn_ai = tk.Button(frame_buttons, text="Identificeer via Foto (AI)", command=self.identify_with_ai, width=22)
        btn_ai.grid(row=0, column=1, padx=5)
        
        btn_remove = tk.Button(frame_buttons, text="Verwijder Selectie", command=self.remove_plant, width=15)
        btn_remove.grid(row=0, column=2, padx=5)

        tk.Frame(root, height=2, bd=1, relief=tk.SUNKEN).pack(fill=tk.X, padx=20, pady=20)

        # --- SECTIE 2: TAKENLIJST ---
        tk.Label(root, text="Openstaande Taken (Water & Voeding):", font=('Arial', 10, 'bold')).pack(pady=(0, 0))
        
        # selectmode=tk.EXTENDED zorgt ervoor dat je meerdere regels kunt selecteren met Ctrl of Shift
        self.task_listbox = tk.Listbox(root, width=120, height=10, bg="#f0f8ff", selectmode=tk.EXTENDED) 
        self.task_listbox.pack(pady=5)
        
        btn_done = tk.Button(root, text="✔️ Markeer geselecteerde taak/taken als GEDAAN", command=self.mark_task_done, width=45, font=('Arial', 10, 'bold'), bg="#e6ffe6")
        btn_done.pack(pady=5)
        
        self.refresh_tasks()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for plant in sorted(self.data.keys()):
            self.listbox.insert(tk.END, plant)

    def refresh_tasks(self):
        self.task_listbox.delete(0, tk.END)
        self.pending_tasks.clear()
        
        today = datetime.now()
        is_winter = today.month in [11, 12, 1, 2]
        
        for plant, data in self.data.items():
            last_watered = datetime.strptime(data['last_watered'], "%Y-%m-%d")
            next_water = last_watered + timedelta(days=data['water_interval'])
            
            if today >= next_water:
                overdue = (today - next_water).days
                self.pending_tasks.append({'plant': plant, 'type': 'water'})
                self.task_listbox.insert(tk.END, f"💧 WATER: {plant} ({overdue} dagen te laat) - Advies: {data['water_amount']}")
                
            fert_interval = data['winter_interval'] if is_winter else data['summer_interval']
            if fert_interval is not None:
                last_fert = datetime.strptime(data['last_fertilized'], "%Y-%m-%d")
                next_fert = last_fert + timedelta(days=fert_interval)
                
                if today >= next_fert:
                    overdue = (today - next_fert).days
                    self.pending_tasks.append({'plant': plant, 'type': 'voeding'})
                    self.task_listbox.insert(tk.END, f"🧪 VOEDING: {plant} ({overdue} dagen te laat)")
                    
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
                continue # Sla de "🎉 Alle planten verzorgd" tekst over
                
            task = self.pending_tasks[idx]
            plant = task['plant']
            task_type = task['type']
            
            if task_type == 'water':
                self.data[plant]['last_watered'] = today_str
            elif task_type == 'voeding':
                self.data[plant]['last_fertilized'] = today_str
                
            tasks_completed += 1
            
        if tasks_completed > 0:
            save_data(self.data)
            self.refresh_tasks()
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
            "Zorg dat summer_interval NOOIT null is als winter_interval wel een getal heeft."
        )
        
        # Temperature op 0.1 voor feitelijke, niet-creatieve antwoorden
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
            
            # Verwijder markdown JSON blokken
            if ai_result.startswith("```"):
                ai_result = ai_result.strip("`").replace("json", "", 1).strip()
                
            profile = json.loads(ai_result)
            required_keys = ['summer_interval', 'winter_interval', 'water_interval', 'water_amount']
            
            if all(key in profile for key in required_keys):
                w_int = profile.get('water_interval')
                s_int = profile.get('summer_interval')
                wi_int = profile.get('winter_interval')
                
                # 1. Harde check: Water interval MOET een geldig getal zijn
                if not isinstance(w_int, int) or w_int <= 0:
                    return None
                    
                # 2. Auto-correctie: Heeft de AI zomer en winter omgedraaid?
                if s_int is None and isinstance(wi_int, int):
                    s_int = wi_int
                    wi_int = None
                    profile['summer_interval'] = s_int
                    profile['winter_interval'] = wi_int
                    
                # 3. Harde check: Zomer/winter intervallen moeten integers of null zijn
                if s_int is not None and (not isinstance(s_int, int) or s_int <= 0):
                    return None
                if wi_int is not None and (not isinstance(wi_int, int) or wi_int <= 0):
                    return None
                    
                # 4. Fallback voor rare hallucinatie-zinnen
                if not isinstance(profile['water_amount'], str) or len(profile['water_amount']) < 5:
                    profile['water_amount'] = "Matig water geven."
                    
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
            
        standaard = {'summer_interval': 30, 'winter_interval': None, 'water_interval': 7, 'water_amount': 'Matig (standaard waterbehoefte)'}
        return standaard, "standaard fallback (AI onbereikbaar)"

    def identify_with_ai(self):
        file_path = filedialog.askopenfilename(title="Kies een foto", filetypes=[("Afbeeldingen", "*.jpg *.jpeg *.png")])
        if not file_path: return

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
            "water_amount": profile['water_amount']
        }
        
        save_data(self.data)
        self.refresh_list()
        self.refresh_tasks() 
        self.entry_name.delete(0, tk.END)
        messagebox.showinfo("Succes", f"'{name}' is toegevoegd.\nSchema gebaseerd op: {bron}.")

    def remove_plant(self):
        selected = self.listbox.curselection()
        if not selected: return
        
        name = self.listbox.get(selected[0])
        if messagebox.askyesno("Bevestigen", f"Weet je zeker dat je '{name}' wilt verwijderen?"):
            del self.data[name]
            save_data(self.data)
            self.refresh_list()
            self.refresh_tasks()

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
