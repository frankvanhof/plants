#!/usr/bin/env bash

# 1. Maak plants.json aan
cat << 'EOF' > plants.json
{
    "Olifantsoor (Alocasia zebrina)": {
        "last_fertilized": "2026-09-01", "summer_interval": 14, "winter_interval": null,
        "last_watered": "2026-10-18", "water_interval": 7,
        "water_amount": "Royaal (zorg dat de kluit niet uitdroogt, maar geen natte voeten)"
    },
    "Lipstick plant (Aeschynanthus radicans)": {
        "last_fertilized": "2026-09-15", "summer_interval": 21, "winter_interval": 42,
        "last_watered": "2026-10-18", "water_interval": 7,
        "water_amount": "Matig (aarde licht vochtig houden)"
    },
    "Orchidee (Phalaenopsis)": {
        "last_fertilized": "2026-10-01", "summer_interval": 14, "winter_interval": 28,
        "last_watered": "2026-10-15", "water_interval": 10,
        "water_amount": "Dompelen (ca. 10 minuten in een bakje water zetten en goed laten uitlekken)"
    },
    "Gatenplant (Monstera deliciosa)": {
        "last_fertilized": "2026-09-20", "summer_interval": 21, "winter_interval": null,
        "last_watered": "2026-10-15", "water_interval": 10,
        "water_amount": "Matig (laat de bovenste laag aarde iets opdrogen tussen gietbeurten)"
    },
    "Flamingoplant (Anthurium andraeanum)": {
        "last_fertilized": "2026-09-10", "summer_interval": 35, "winter_interval": 70,
        "last_watered": "2026-10-18", "water_interval": 7,
        "water_amount": "Matig (geef regelmatig kleine beetjes lauw water)"
    },
    "Graslelie (Chlorophytum comosum)": {
        "last_fertilized": "2026-09-25", "summer_interval": 21, "winter_interval": 42,
        "last_watered": "2026-10-18", "water_interval": 7,
        "water_amount": "Matig tot ruim (sterke plant, maar houdt van regelmaat)"
    }
}
EOF

# 2. Maak check_plants.py aan
cat << 'EOF' > check_plants.py
#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime, timedelta
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), 'plants.json')

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def send_notification(plant_name, actions):
    title = f"🌱 {plant_name} heeft verzorging nodig!"
    
    message_lines = []
    for action in actions:
        if action['type'] == 'water':
            message_lines.append(f"💧 Water geven ({action['days']} dagen te laat):\n   Hoeveelheid: {action['amount']}")
        elif action['type'] == 'fertilizer':
            message_lines.append(f"🧪 Voeding geven ({action['days']} dagen te laat)")
            
    message = "\n\n".join(message_lines)
    subprocess.run(['notify-send', '-u', 'normal', '-i', 'weather-clear', title, message])

def main():
    plants = load_data()
    today = datetime.now()
    is_winter = today.month in [11, 12, 1, 2]
    needs_attention = False

    for plant, data in plants.items():
        actions_needed = []

        # 1. Controleer water
        last_watered = datetime.strptime(data['last_watered'], "%Y-%m-%d")
        next_water_date = last_watered + timedelta(days=data['water_interval'])
        
        if today >= next_water_date:
            days_overdue = (today - next_water_date).days
            actions_needed.append({'type': 'water', 'days': days_overdue, 'amount': data['water_amount']})

        # 2. Controleer voeding
        fert_interval = data['winter_interval'] if is_winter else data['summer_interval']
        
        if fert_interval is not None:
            last_fert_date = datetime.strptime(data['last_fertilized'], "%Y-%m-%d")
            next_fert_date = last_fert_date + timedelta(days=fert_interval)
            
            if today >= next_fert_date:
                days_overdue = (today - next_fert_date).days
                actions_needed.append({'type': 'fertilizer', 'days': days_overdue})

        if actions_needed:
            send_notification(plant, actions_needed)
            print(f"[!] {plant} heeft actie nodig.")
            needs_attention = True
            
    if not needs_attention:
        print(f"Alle planten zijn momenteel voorzien (Seizoen: {'Winter' if is_winter else 'Zomer'}).")

if __name__ == "__main__":
    main()
EOF

# 3. Maak plant_manager.py aan
cat << 'EOF' > plant_manager.py
#!/usr/bin/env python3
import json
import os
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), 'plants.json')

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
        self.root.geometry("450x400")
        
        self.data = load_data()
        
        tk.Label(root, text="Huidige Planten:", font=('Arial', 10, 'bold')).pack(pady=(10, 0))
        self.listbox = tk.Listbox(root, width=50, height=12)
        self.listbox.pack(pady=5)
        self.refresh_list()
        
        tk.Label(root, text="Nieuwe plant toevoegen:").pack(pady=(10, 0))
        self.entry_name = tk.Entry(root, width=40)
        self.entry_name.pack(pady=5)
        
        frame_buttons = tk.Frame(root)
        frame_buttons.pack(pady=10)
        
        btn_add = tk.Button(frame_buttons, text="Voeg Toe", command=self.add_plant, width=15)
        btn_add.grid(row=0, column=0, padx=5)
        
        btn_remove = tk.Button(frame_buttons, text="Verwijder Selectie", command=self.remove_plant, width=15)
        btn_remove.grid(row=0, column=1, padx=5)

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

    def add_plant(self):
        name = self.entry_name.get().strip()
        if not name:
            messagebox.showwarning("Invoer Fout", "Vul een plantennaam in.")
            return
        if name in self.data:
            messagebox.showwarning("Dubbel", "Deze plant bestaat al in de lijst.")
            return
        
        profile = self.get_profile(name)
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
        self.entry_name.delete(0, tk.END)
        
        profiel_naam = next((k for k in PLANT_PROFILES if k in name.lower()), 'standaard')
        messagebox.showinfo("Succes", f"'{name}' is toegevoegd met het '{profiel_naam}' schema.")

    def remove_plant(self):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showwarning("Selectie Fout", "Klik eerst op een plant.")
            return
        
        name = self.listbox.get(selected[0])
        if messagebox.askyesno("Bevestigen", f"Weet je zeker dat je '{name}' wilt verwijderen?"):
            del self.data[name]
            save_data(self.data)
            self.refresh_list()

if __name__ == "__main__":
    root = tk.Tk()
    app = PlantManager(root)
    root.mainloop()
EOF

# 4. Maak scripts uitvoerbaar
chmod +x check_plants.py plant_manager.py

# 5. Maak de .desktop file aan
# We gebruiken $PWD zodat het pad altijd klopt met waar je het script draait
cat << EOF > PlantenBeheer.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=Planten Beheer
Comment=Beheer je kamerplanten en water/voeding schema's
Exec=$PWD/plant_manager.py
Icon=weather-clear
Terminal=false
Categories=Utility;
EOF

# Optioneel: Maak de .desktop file vertrouwd op Linux Mint (Cinnamon)
chmod +x PlantenBeheer.desktop

echo "Installatie voltooid! Er zijn 4 bestanden aangemaakt in $PWD."
echo "- plants.json"
echo "- check_plants.py"
echo "- plant_manager.py"
echo "- PlantenBeheer.desktop"
echo "Je kunt PlantenBeheer.desktop nu verplaatsen naar je bureaublad of ~/.local/share/applications/"
