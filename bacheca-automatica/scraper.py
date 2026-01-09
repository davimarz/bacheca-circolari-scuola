"""
Scraper per scaricare le circolari dal sito della scuola
DA MODIFICARE in base alla struttura reale del sito
"""

import requests  # IMPORT AGGIUNTO
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import re

def scarica_circolari_reali(url_sito):
    """
    Funzione da adattare alla struttura reale del sito della scuola
    
    Args:
        url_sito: URL della pagina delle circolari
    
    Returns:
        Lista di dizionari con le circolari
    """
    circolari = []
    
    try:
        # 1. Scarica la pagina
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url_sito, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 2. Parsing HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 3. ESTRAZIONE CIRCOLARI - DA ADATTARE
        # Esempio di struttura (modificare in base al sito reale):
        
        # Cerca tabelle, liste o div che contengono le circolari
        # Tipici selettori:
        # - Articoli: soup.find_all('article')
        # - Righe tabella: soup.find_all('tr')
        # - Elementi lista: soup.find_all('li', class_='circolare')
        
        # ESEMPIO per tabelle:
        tabelle = soup.find_all('table')
        for tabella in tabelle:
            righe = tabella.find_all('tr')[1:]  # Salta intestazione
            
            for riga in righe:
                celle = riga.find_all('td')
                if len(celle) >= 3:
                    data_pub = parse_data(celle[2].text.strip())
                    circolare = {
                        'titolo': celle[0].text.strip(),
                        'contenuto': celle[1].text.strip(),
                        'data_pubblicazione': data_pub.strftime("%Y-%m-%d %H:%M:%S"),
                        'pdf_url': extract_pdf_url(celle[0])  # Cerca link PDF
                    }
                    circolari.append(circolare)
        
        # Se non trovi con i selettori standard, usa ricerca per testo
        if not circolari:
            # Cerca elementi che contengono "circolare" nel testo o classe
            elementi_circolari = soup.find_all(
                lambda tag: ('circolare' in tag.get('class', []) or 
                            'circolare' in tag.text.lower()) and 
                            tag.name in ['div', 'article', 'li']
            )
            
            for elem in elementi_circolari:
                # Estrai titolo (primo h2, h3, o testo in grassetto)
                titolo_elem = elem.find(['h2', 'h3', 'h4', 'strong', 'b'])
                titolo = titolo_elem.text.strip() if titolo_elem else "Circolare"
                
                # Estrai contenuto
                contenuto = ' '.join([p.text for p in elem.find_all('p')]) or elem.text
                
                # Estrai data (cerca pattern di data)
                data_text = extract_data_da_testo(elem.text)
                
                # Estrai PDF
                pdf_link = elem.find('a', href=re.compile(r'\.pdf$', re.I))
                pdf_url = pdf_link['href'] if pdf_link else ""
                
                circolari.append({
                    'titolo': titolo,
                    'contenuto': contenuto[:500],  # Limita lunghezza
                    'data_pubblicazione': data_text or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    'pdf_url': pdf_url
                })
        
        return circolari
        
    except Exception as e:
        print(f"Errore nello scraping: {e}")
        return []

def parse_data(testo_data):
    """Converte testo data in formato standard - VERSIONE CORRETTA"""
    try:
        # Pattern comuni per date italiane
        patterns = [
            (r'(\d{2})/(\d{2})/(\d{4})', "%d/%m/%Y"),      # dd/mm/yyyy
            (r'(\d{2})-(\d{2})-(\d{4})', "%d-%m-%Y"),      # dd-mm-yyyy
            (r'(\d{4})-(\d{2})-(\d{2})', "%Y-%m-%d"),      # yyyy-mm-dd
            (r'(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})', "%d/%m/%Y %H:%M"),  # dd/mm/yyyy HH:MM
        ]
        
        for pattern, fmt in patterns:
            match = re.search(pattern, testo_data)
            if match:
                # Costruisci stringa data
                if len(match.groups()) == 3:
                    data_str = f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
                    return datetime.strptime(data_str, "%Y-%m-%d")
                elif len(match.groups()) == 5:
                    data_str = f"{match.group(3)}-{match.group(2)}-{match.group(1)} {match.group(4)}:{match.group(5)}"
                    return datetime.strptime(data_str, "%Y-%m-%d %H:%M")
        
        # Se non trova pattern, usa oggi
        return datetime.now(timezone.utc)
        
    except Exception:
        # In caso di errore, ritorna datetime UTC corrente
        return datetime.now(timezone.utc)

def extract_data_da_testo(testo):
    """Estrae data da testo"""
    # Cerca pattern di data nel testo
    date_patterns = [
        r'\d{2}/\d{2}/\d{4}',
        r'\d{2}-\d{2}-\d{4}',
        r'\d{4}-\d{2}-\d{2}',
        r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, testo)
        if match:
            parsed_date = parse_data(match.group())
            return parsed_date.strftime("%Y-%m-%d %H:%M:%S")
    
    return None

def extract_pdf_url(elemento):
    """Estrae URL PDF da un elemento HTML"""
    pdf_links = elemento.find_all('a', href=re.compile(r'\.pdf$', re.I))
    if pdf_links:
        # Combina tutti i PDF trovati con separatore ;;;
        urls = [link['href'] for link in pdf_links]
        return ';;;'.join(urls)
    return ""

# Per test
if __name__ == "__main__":
    # URL di esempio - SOSTITUIRE con URL reale
    url_test = "https://www.icannafrankag.edu.it/circolari"
    
    circolari = scarica_circolari_reali(url_test)
    print(f"Trovate {len(circolari)} circolari")
    for c in circolari[:3]:  # Mostra prime 3
        print(f"- {c['titolo']} ({c['data_pubblicazione']})")
