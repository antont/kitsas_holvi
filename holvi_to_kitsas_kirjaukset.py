#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Holvi CSV -> Kitsas Kirjausviennit CSV muunnin
Optimoitu Kitsas "Kirjauksia" -tuontimuotoa varten (joka tukee ALV-kenttiä).
Sisältää automaattisen tilikartan generoinnin.
"""

import csv
import sys

def parse_holvi_csv(input_file):
    """Lukee Holvi CSV:n ja palauttaa datatiedot listana"""
    data_rows = []
    
    with open(input_file, 'r', encoding='utf-8') as file:
        content = file.read()
        lines = content.strip().split('\n')
    
    # Etsi varsinaisen datan alkurivi (otsikot)
    header_row_index = -1
    for i, line in enumerate(lines):
        if 'Arvopäivä' in line and 'Kirjauspäivä' in line:
            header_row_index = i
            break
    
    if header_row_index == -1:
        raise ValueError("Ei löydetty otsikkoriviä CSV:stä")
    
    # Lue otsikot
    headers = lines[header_row_index].split(';')
    
    # Lue datatiedot
    for i in range(header_row_index + 1, len(lines)):
        if lines[i].strip():  # Ohita tyhjät rivit
            row = lines[i].split(';')
            data_rows.append(row)
    
    return headers, data_rows

def get_account_number(category, subcategory, amount_float):
    """Määrittää tilinumeron kategorian perusteella"""
    
    # Perustilit suomalaisessa tilikarttajärjestelmässä
    if category == 'income':
        if 'invoice' in subcategory:
            return '3000'  # Myyntitulot
        elif 'iban_payment' in subcategory:
            return '3000'  # Myyntitulot 
        elif 'uploadmoney' in subcategory:
            return '2000'  # Oma pääoma (siirrot)
        else:
            return '3000'  # Myyntitulot (oletus)
    
    elif category == 'expense':
        if 'Palvelumaksut' in subcategory or 'Holvi' in subcategory:
            return '6000'  # Palvelumaksut
        elif 'Yrityskulut' in subcategory:
            return '6100'  # Muut kulut
        elif 'ALV maksettavaa' in subcategory:
            return '2940'  # ALV-velka
        else:
            return '6000'  # Kulut (oletus)
    
    else:
        # Tuntematon kategoria
        if amount_float > 0:
            return '3000'  # Tulot
        else:
            return '6000'  # Kulut

def convert_for_kitsas_kirjaukset(headers, data_rows):
    """Muuntaa Kitsas kirjausviennit-muotoon (debet/kredit + tilinumerot)"""
    
    # Kitsas kirjausviennit-otsikot (täsmälliset nimet joita Kitsas tunnistaa)
    kitsas_headers = ['Päivämäärä', 'Tilin numero', 'Debet euroa', 'Kredit euroa', 'Selite', 'alv %']
    kitsas_rows = []
    
    # Etsi sarakkeiden indeksit
    date_idx = next((i for i, h in enumerate(headers) if 'Arvopäivä' in h), 0)
    amount_idx = next((i for i, h in enumerate(headers) if 'Yhteensä' in h), -1)
    description_idx = next((i for i, h in enumerate(headers) if 'Kuvaus' in h), -1)
    payer_idx = next((i for i, h in enumerate(headers) if 'Maksaja' in h), -1)
    vat_percent_idx = next((i for i, h in enumerate(headers) if 'ALV %' in h), -1)
    category_idx = next((i for i, h in enumerate(headers) if 'Luokka' in h), -1)
    subcategory_idx = next((i for i, h in enumerate(headers) if 'Alaluokka' in h), -1)
    
    bank_account = '1910'  # Pankkitili
    
    for row in data_rows:
        if len(row) <= date_idx:
            continue
            
        # Päivämäärä (säilytetään suomalaisessa muodossa)
        date = row[date_idx].strip()
        
        # Rahamäärä ja sen käsittely
        amount_str = row[amount_idx].strip() if amount_idx >= 0 and len(row) > amount_idx else "0"
        amount_str = amount_str.replace(',', '.')  # Muunna desimaalipilkku pisteeksi
        
        try:
            amount_float = float(amount_str)
        except ValueError:
            amount_float = 0
            
        # Ohita 0-summat
        if abs(amount_float) < 0.01:
            continue
            
        # Selite (yhdistetään kuvaus ja maksaja)
        description = row[description_idx].strip() if description_idx >= 0 and len(row) > description_idx else ""
        payer = row[payer_idx].strip() if payer_idx >= 0 and len(row) > payer_idx else ""
        
        if payer and description:
            full_description = f"{description} ({payer})"
        elif payer:
            full_description = payer
        else:
            full_description = description
        
        # ALV%
        vat_percent = row[vat_percent_idx].strip() if vat_percent_idx >= 0 and len(row) > vat_percent_idx else "0"
        
        # Kategoriat
        category = row[category_idx].strip() if category_idx >= 0 and len(row) > category_idx else ""
        subcategory = row[subcategory_idx].strip() if subcategory_idx >= 0 and len(row) > subcategory_idx else ""
        
        # Määritä tilikarttanumero kategorian perusteella
        account_number = get_account_number(category, subcategory, amount_float)
        
        # Luo kaksi kirjausvientiä: pankkitili + vastakitili
        amount_abs = abs(amount_float)
        amount_str_abs = f"{amount_abs:.2f}".replace('.', ',')
        
        if amount_float > 0:
            # Tulo: Pankki DEBET, Tulotili KREDIT
            # Pankkitili debet
            bank_row = [date, bank_account, amount_str_abs, '', full_description, '0']
            kitsas_rows.append(bank_row)
            
            # Tulotili kredit
            income_row = [date, account_number, '', amount_str_abs, full_description, vat_percent]
            kitsas_rows.append(income_row)
            
        else:
            # Meno: Kulutili DEBET, Pankki KREDIT
            # Kulutili debet
            expense_row = [date, account_number, amount_str_abs, '', full_description, vat_percent]
            kitsas_rows.append(expense_row)
            
            # Pankkitili kredit
            bank_row = [date, bank_account, '', amount_str_abs, full_description, '0']
            kitsas_rows.append(bank_row)
    
    return kitsas_headers, kitsas_rows

def main():
    if len(sys.argv) < 2:
        print("Käyttö: python holvi_to_kitsas_kirjaukset.py <holvi_tiedosto.csv> [tuloste.csv]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "kitsas_kirjaukset_tilikartta.csv"
    
    try:
        # Lue Holvi CSV
        headers, data_rows = parse_holvi_csv(input_file)
        print(f"Luettu {len(data_rows)} datariviä Holvi CSV:stä")
        
        # Muunna Kitsas-muotoon
        kitsas_headers, kitsas_rows = convert_for_kitsas_kirjaukset(headers, data_rows)
        
        # Kirjoita tuloste
        with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
            writer = csv.writer(outfile, delimiter=';')
            writer.writerow(kitsas_headers)
            writer.writerows(kitsas_rows)
        
        print(f"Kirjoitettu {len(kitsas_rows)} riviä tiedostoon {output_file}")
        print(f"Käytä Kitsasissa 'Kirjauksia' -tuontimuotoa")
        print(f"Tilinumerot: 1910=Pankki, 3000=Tulot, 6000=Kulut, 6100=Yrityskulut")
        
    except Exception as e:
        print(f"Virhe: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 