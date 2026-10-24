# Planten Beheer App

Lokaal, privacy-vriendelijk beheersysteem voor kamerplanten. Geschreven in Python en geoptimaliseerd voor Linux Mint.

## Bestanden in deze map
* **`plants.json`**: De lokale database waarin de statussen en intervallen (zomer/winter) van alle planten worden bijgehouden.
* **`plant_manager.py`**: De grafische Tkinter-interface (1200x800). Bevat een `fcntl` lock-file mechanisme om te voorkomen dat er meerdere instanties draaien. Biedt integratie met een lokale Ollama-instantie (`llava` model) voor automatische plantidentificatie via foto's.
* **`check_plants.py`**: Het achtergrondscript dat berekent of planten water of voeding nodig hebben, en deze via `notify-send` als gebundelde desktopnotificaties weergeeft.
* **`PlantenBeheer.desktop`**: Snelkoppeling voor het Linux Mint applicatiemenu of bureaublad.

## Vereisten
1. **Python packages**: `requests` voor de Ollama API-calls. (`pip install requests`)
2. **Ollama**: Zorg dat de service lokaal draait (poort 11434) en het vision-model gedownload is: `ollama pull llava`
3. **Systeem**: `notify-send` (standaard aanwezig in Linux Mint/Cinnamon).

## Automatisering (Cronjob)
Voeg `check_plants.py` toe aan je crontab om elke ochtend (bijv. 09:00) te controleren:
`0 9 * * * export DISPLAY=:0 && export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus" && /home/$USER/tools/plants/check_plants.py`
