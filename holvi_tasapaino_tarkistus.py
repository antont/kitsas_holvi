#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarkistaa Kitsas CSV:n tasapainon - jokainen päivämäärä+selite yhdistelmä
pitää olla tasapainossa (debet-summa = kredit-summa)
"""

import csv
import sys
from collections import defaultdict

def tarkista_tasapaino(csv_file):
    """Tarkistaa CSV:n tasapainon"""
    
    tositteet = defaultdict(lambda: {'debet': 0, 'kredit': 0, 'rivit': []})
    
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=';')
        
        for i, row in enumerate(reader, 1):
            pvm = row['Päivämäärä']
            selite = row['Selite'][:50]  # Lyhennä selite
            
            # Avain: päivämäärä + selite
            avain = f"{pvm}:{selite}"
            
            try:
                debet = float(row['Debet euroa'].replace(',', '.')) if row['Debet euroa'] else 0
                kredit = float(row['Kredit euroa'].replace(',', '.')) if row['Kredit euroa'] else 0
            except ValueError:
                print(f"VIRHE rivillä {i}: Epäkelpo summa - {row}")
                continue
                
            tositteet[avain]['debet'] += debet
            tositteet[avain]['kredit'] += kredit
            tositteet[avain]['rivit'].append(i)
    
    print(f"Tarkistetaan {len(tositteet)} tositekokonaisuutta...\n")
    
    virheet = 0
    for avain, data in tositteet.items():
        erotus = abs(data['debet'] - data['kredit'])
        if erotus > 0.01:  # Salli pieni pyöristysvirhe
            virheet += 1
            print(f"❌ EPÄTASAPAINO: {avain}")
            print(f"   Debet: {data['debet']:.2f} € | Kredit: {data['kredit']:.2f} € | Erotus: {erotus:.2f} €")
            print(f"   Rivit: {data['rivit']}")
            print()
    
    if virheet == 0:
        print("✅ Kaikki tositteet ovat tasapainossa!")
    else:
        print(f"❌ {virheet} tositekokonaisuutta EI ole tasapainossa!")
    
    print(f"\nYhteenveto:")
    total_debet = sum(t['debet'] for t in tositteet.values())
    total_kredit = sum(t['kredit'] for t in tositteet.values())
    print(f"Kokonais-debet: {total_debet:.2f} €")
    print(f"Kokonais-kredit: {total_kredit:.2f} €")
    print(f"Kokonais-erotus: {abs(total_debet - total_kredit):.2f} €")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Käyttö: python holvi_tasapaino_tarkistus.py <kitsas_tiedosto.csv>")
        sys.exit(1)
    
    tarkista_tasapaino(sys.argv[1]) 