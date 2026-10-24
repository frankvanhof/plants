#!/usr/bin/env python3
import json
import os
import sys
import fcntl
import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime
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
        self.root.geometry("1200x1200")
        
        self.data = load_data()
        
        tk.Label(root, text="Huidige Planten:", font=('Arial', 10, 'bold')).pack(pady=(10, 0))
        self.listbox = tk.Listbox(root, width=120, height=20)
        self.listbox.pack(pady=5)
        self.refresh_list()
        
        tk.Label(root, text="Nieuwe plant toevoegen:").pack(pady=(10, 0))
        self.entry_name = tk.Entry(root, width=40)
        self.entry_name.pack(pady=5)
        
        frame_buttons = tk.Frame(root)
        frame_buttons.pack(pady=10)
        
        btn_add = tk.Button(frame_buttons, text="Voeg Toe", command=self.add_plant, width=15)
        btn_add.grid(row=0, column=0, padx=5)
        
        btn_ai = tk.Button(frame_buttons, text="Identificeer via Foto (AI)", command=self.identify_with_ai, width=22)
        btn_ai.grid(row=0, column=1, padx=5)
        
        btn_remove = tk.Button(frame_buttons, text="Verwijder Selectie", command=self.remove_plant, width=15)
        btn_remove.grid(row=0, column=2, padx=5)

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for plant in sorted(self.data.keys()):
            self.listbox.insert(tk.END, plant)

    def get_profile(self, name):
        name_lower = name.lower()
        for key, profile in PLANT_PROFILES.items():
            if key in name_lower:
                return profile
        return PLANT_PROFILES['standaard']

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
        if name in self.data: return
        
        profile = self.get_profile(name)
        today = datetime.now().strftime("%Y-%m-%d")
        
        self.data[name] = {
            "last_fertilized": today, "summer_interval": profile['summer_interval'], "winter_interval": profile['winter_interval'],
            "last_watered": today, "water_interval": profile['water_interval'], "water_amount": profile['water_amount']
        }
        
        save_data(self.data)
        self.refresh_list()
        self.entry_name.delete(0, tk.END)

    def remove_plant(self):
        selected = self.listbox.curselection()
        if not selected: return
        
        name = self.listbox.get(selected[0])
        if messagebox.askyesno("Bevestigen", f"Weet je zeker dat je '{name}' wilt verwijderen?"):
            del self.data[name]
            save_data(self.data)
            self.refresh_list()

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
