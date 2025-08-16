#!/usr/bin/env python3
"""
PRESHADOW.PY - Adatgyűjtő és előfeldolgozó szkript a SHADOW számára
Használat: 
1. Interaktív mód: python preshadow.py
2. Kötegmód: python preshadow.py <magasság> <árnyék> [dátum] [idő]
"""

import sys
import json
from datetime import datetime

def collect_data():
    """Interaktív adatgyűjtés"""
    print("PRESHADOW - Adatgyűjtő mód\n" + "="*40)
    
    data = {
        'height': float(input("Objektum magassága (méter): ")),
        'shadow': float(input("Árnyék hossza (méter): ")),
        'date': input("Dátum (ÉÉÉÉ-HH-NN, üresen ma): ") or datetime.now().strftime("%Y-%m-%d"),
        'time': input("Idő (ÓÓ:PP, üresen most): ") or datetime.now().strftime("%H:%M")
    }
    
    # Kiegészítő metaadatok
    data['calc_date'] = datetime.now().isoformat()
    data['version'] = '1.0'
    
    return data

def validate_data(data):
    """Adatvalidáció"""
    if data['height'] <= 0 or data['shadow'] <= 0:
        raise ValueError("Érvénytelen méretértékek")
    try:
        datetime.strptime(data['date'], "%Y-%m-%d")
        datetime.strptime(data['time'], "%H:%M")
    except ValueError:
        raise ValueError("Érvénytelen dátum/idő formátum")

def save_to_json(data, filename='shadow_data.json'):
    """JSON export"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\nAdatok elmentve: {filename}")

if __name__ == '__main__':
    if len(sys.argv) > 2:  # Kötegmód
        try:
            data = {
                'height': float(sys.argv[1]),
                'shadow': float(sys.argv[2]),
                'date': sys.argv[3] if len(sys.argv) > 3 else datetime.now().strftime("%Y-%m-%d"),
                'time': sys.argv[4] if len(sys.argv) > 4 else datetime.now().strftime("%H:%M")
            }
            validate_data(data)
        except (IndexError, ValueError) as e:
            print(f"Hiba: {e}\nHasználat: python preshadow.py <magasság> <árnyék> [dátum] [idő]")
            sys.exit(1)
    else:  # Interaktív mód
        data = collect_data()
    
    try:
        validate_data(data)
        save_to_json(data)
    except Exception as e:
        print(f"Hiba történt: {str(e)}")
        sys.exit(1)