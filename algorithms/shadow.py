#!/usr/bin/env python3
"""
SHADOW.PY - Pontos szélességi fok számítás előfeldolgozott adatokból
Használat: python shadow.py [input_fájl.json]
"""

import json
import math
from datetime import datetime

class ShadowCalculator:
    def __init__(self, data):
        self.data = data
        self.validate_input()
        self.prepare_calculation()
        
    def validate_input(self):
        """Bemeneti adatok validálása"""
        required = ['height', 'shadow', 'date', 'time']
        if not all(k in self.data for k in required):
            raise ValueError("Hiányzó adatok")
        
    def prepare_calculation(self):
        """Számítás előkészítése"""
        # Dátum/idő átalakítás
        dt = datetime.strptime(f"{self.data['date']} {self.data['time']}", "%Y-%m-%d %H:%M")
        self.day_of_year = dt.timetuple().tm_yday
        self.local_hour = dt.hour + dt.minute/60
        
        # Alapadatok
        self.shadow_ratio = self.data['shadow'] / self.data['height']
        
    def calculate_declination(self):
        """Nap deklinációjának számítása"""
        return 23.45 * math.sin(math.radians(360/365 * (self.day_of_year - 81)))
        
    def calculate_solar_elevation(self):
        """Nap magassági szögének számítása"""
        return math.degrees(math.atan(1 / self.shadow_ratio))
        
    def calculate_latitude(self):
        """Pontos szélességi fok számítás"""
        declination = self.calculate_declination()
        elevation = self.calculate_solar_elevation()
        
        # Korrekciók
        time_correction = (self.local_hour - 12) * 0.5  # Délidőhöz viszonyított korrekció
        return 90 - elevation + declination + time_correction
        
    def calculate_all(self):
        """Teljes számítási folyamat"""
        results = {
            'input_data': self.data,
            'declination': self.calculate_declination(),
            'solar_elevation': self.calculate_solar_elevation(),
            'latitude': self.calculate_latitude(),
            'calculation_time': datetime.now().isoformat(),
            'accuracy_estimate': self.estimate_accuracy()
        }
        return results
        
    def estimate_accuracy(self):
        """Pontosság becslése"""
        accuracy = 0.5  # Alappontosság fokokban
        
        # Pontosság javítása ha pontos idő ismert
        if 'time' in self.data and self.data['time'] != '':
            accuracy *= 0.7
            
        # Pontosság romlása ha nincs pontos dátum
        if 'date' not in self.data:
            accuracy *= 1.5
            
        return round(accuracy, 2)

def load_data(filename='shadow_data.json'):
    """Adatok betöltése JSON fájlból"""
    with open(filename) as f:
        return json.load(f)

def print_results(results):
    """Eredmények megjelenítése"""
    print("\nSHADOW - Számítási eredmények")
    print("=" * 40)
    print(f"Objektum magassága: {results['input_data']['height']} m")
    print(f"Árnyék hossza: {results['input_data']['shadow']} m")
    print(f"Mérés ideje: {results['input_data']['date']} {results['input_data']['time']}")
    print("\nKalkulált értékek:")
    print(f"- Nap deklinációja: {results['declination']:.2f}°")
    print(f"- Nap magassági szöge: {results['solar_elevation']:.2f}°")
    print(f"- Szélességi fok: {results['latitude']:.2f}°")
    print(f"- Becsült pontosság: ±{results['accuracy_estimate']}°")

if __name__ == '__main__':
    import sys
    
    try:
        input_file = sys.argv[1] if len(sys.argv) > 1 else 'shadow_data.json'
        data = load_data(input_file)
        
        calculator = ShadowCalculator(data)
        results = calculator.calculate_all()
        
        print_results(results)
        
        # Eredmény mentése
        with open('shadow_results.json', 'w') as f:
            json.dump(results, f, indent=2)
            
    except Exception as e:
        print(f"Hiba: {str(e)}")
        print("Használat: python shadow.py [input_fájl.json]")