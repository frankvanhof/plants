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

        last_watered = datetime.strptime(data['last_watered'], "%Y-%m-%d")
        next_water_date = last_watered + timedelta(days=data['water_interval'])
        if today >= next_water_date:
            days_overdue = (today - next_water_date).days
            actions_needed.append({'type': 'water', 'days': days_overdue, 'amount': data['water_amount']})

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
