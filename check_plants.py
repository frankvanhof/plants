#!/usr/bin/env python3
import json
import os
import subprocess
import requests
from datetime import datetime, timedelta

# Pad naar je data in dezelfde map als dit script
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plants.json')
NTFY_TOPIC = "frank_planten_beheer_2026"

def load_data():
    print(f"Zoeken naar data in: {DATA_FILE}")
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def main():
    print("Start planten check...")
    data = load_data()
    
    print(f"Aantal ingeladen planten: {len(data)}")
    if not data:
        print("Geen data gevonden of bestand is leeg!")
        return

    today = datetime.now()
    is_winter = today.month in [11, 12, 1, 2]
    tasks = []

    # Loop door alle planten om te controleren of er actie nodig is
    for plant, info in data.items():
        try:
            last_watered = datetime.strptime(info['last_watered'], "%Y-%m-%d")
            next_water = last_watered + timedelta(days=info['water_interval'])
            
            # Heeft de plant water nodig?
            if today >= next_water:
                overdue_water = (today - next_water).days
                
                # Veilig ophalen van voeding interval (handelt 'null' in json netjes af)
                fert_interval = info.get('winter_interval') if is_winter else info.get('summer_interval')
                fert_due = False
                
                # Check of voeding ook nodig is, gesynct met de water-datum
                if fert_interval is not None:
                    last_fert = datetime.strptime(info['last_fertilized'], "%Y-%m-%d")
                    ideal_next_fert = last_fert + timedelta(days=fert_interval)
                    
                    sync_fert = next_water
                    while sync_fert < ideal_next_fert:
                        sync_fert += timedelta(days=info['water_interval'])
                        
                    if today >= sync_fert:
                        fert_due = True
                
                # Voeg toe aan de takenlijst
                if fert_due:
                    tasks.append(f"💧 + 🧪 WATER & MEST: {plant} ({overdue_water} dagen te laat)")
                else:
                    tasks.append(f"💧 WATER: {plant} ({overdue_water} dagen te laat)")
        
        except Exception as e:
            print(f"Fout bij berekenen plant '{plant}': {e}")
            continue

    # Als er taken zijn, stuur de notificaties
    if tasks:
        print(f"Er zijn {len(tasks)} taken gevonden. Notificaties voorbereiden...")
        message = "\n".join(tasks)
        title = "🌱 Planten Verzorging Nodig!"
        
        # 1. Desktop Notificatie (fouten geruisloos negeren op een headless Pi)
        try:
            subprocess.run(
                ['notify-send', '-u', 'normal', '-i', 'weather-showers-scattered', title, message], 
                check=True
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
            
        # 2. Push Notificatie naar de telefoon (ntfy) via JSON
        try:
            response = requests.post(
                "https://ntfy.sh/",
                json={
                    "topic": NTFY_TOPIC,
                    "title": title,
                    "message": message,
                    "tags": ["potted_plant", "droplet"],
                    "priority": 3
                },
                timeout=10
            )
            if response.status_code == 200:
                print("Push notificatie succesvol verstuurd naar de Motorola!")
            else:
                print(f"Fout bij ntfy-API, HTTP code: {response.status_code}")
        except Exception as e:
            print(f"Fout bij push notificatie: {e}")
    else:
        print("Alle planten zijn voorzien. Geen actie nodig vandaag.")

if __name__ == "__main__":
    main()