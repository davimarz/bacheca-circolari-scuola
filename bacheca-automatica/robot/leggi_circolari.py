import os
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from supabase import create_client
import urllib.parse
import re

print("🤖 Robot avviato")

config = {
    'ARGO_USER': os.environ.get('ARGO_USER'),
    'ARGO_PASS': os.environ.get('ARGO_PASS'),
    'SUPABASE_URL': os.environ.get('SUPABASE_URL'),
    'SUPABASE_KEY': os.environ.get('SUPABASE_KEY')
}

supabase = create_client(config['SUPABASE_URL'], config['SUPABASE_KEY'])

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=chrome_options)

def extract_date_from_text(data_text):
    """Estrae la data dal testo della circolare"""
    # Cerca diversi formati di data
    date_patterns = [
        r'(\d{2})/(\d{2})/(\d{4})',  # 25/10/2024
        r'(\d{2})-(\d{2})-(\d{4})',  # 25-10-2024
        r'(\d{2})\.(\d{2})\.(\d{4})',  # 25.10.2024
        r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})',  # 25 Ottobre 2024
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, data_text)
        if match:
            if len(match.groups()) == 3:
                g1, g2, g3 = match.groups()
                # Se il pattern contiene nomi di mesi
                if pattern == r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})':
                    mesi = {
                        'gennaio': '01', 'febbraio': '02', 'marzo': '03',
                        'aprile': '04', 'maggio': '05', 'giugno': '06',
                        'luglio': '07', 'agosto': '08', 'settembre': '09',
                        'ottobre': '10', 'novembre': '11', 'dicembre': '12'
                    }
                    mese = mesi.get(g2.lower(), '01')
                    return datetime(int(g3), int(mese), int(g1))
                else:
                    # Formati numerici
                    try:
                        giorno, mese, anno = int(g1), int(g2), int(g3)
                        return datetime(anno, mese, giorno)
                    except:
                        continue
    return None

try:
    oggi = datetime.now()
    
    # Definisco l'anno scolastico corrente (settembre 2024 - giugno 2025)
    if oggi.month >= 9:  # Da settembre a dicembre
        anno_scolastico_inizio = datetime(oggi.year, 9, 1)
        anno_scolastico_fine = datetime(oggi.year + 1, 6, 30)
    else:  # Da gennaio ad agosto
        anno_scolastico_inizio = datetime(oggi.year - 1, 9, 1)
        anno_scolastico_fine = datetime(oggi.year, 6, 30)
    
    print(f"Anno scolastico considerato: {anno_scolastico_inizio.strftime('%d/%m/%Y')} - {anno_scolastico_fine.strftime('%d/%m/%Y')}")
    
    driver.get("https://www.portaleargo.it/famiglia")
    time.sleep(3)
    
    username = driver.find_element(By.ID, "username")
    password = driver.find_element(By.ID, "password")
    
    username.send_keys(config['ARGO_USER'])
    password.send_keys(config['ARGO_PASS'])
    
    login_button = driver.find_element(By.ID, "login-button")
    login_button.click()
    
    time.sleep(5)
    
    circolari_link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Circolari"))
    )
    circolari_link.click()
    
    time.sleep(5)
    
    all_circolari = []
    page_number = 1
    
    while True:
        print(f"Scansionando pagina {page_number}...")
        
        # Aspetta che le circolari siano caricate
        time.sleep(3)
        
        # Trova tutti gli elementi delle circolari
        circolari_elements = driver.find_elements(By.CSS_SELECTOR, ".circolare-item")
        
        if not circolari_elements:
            print("Nessuna circolare trovata sulla pagina.")
            break
        
        print(f"Trovate {len(circolari_elements)} circolari sulla pagina {page_number}")
        
        for elem in circolari_elements:
            try:
                # Estrai titolo, data e link
                titolo_elem = elem.find_element(By.CSS_SELECTOR, ".circolare-titolo")
                data_elem = elem.find_element(By.CSS_SELECTOR, ".circolare-data")
                link_elem = elem.find_element(By.CSS_SELECTOR, "a")
                
                titolo = titolo_elem.text.strip()
                data_testo = data_elem.text.strip()
                link = link_elem.get_attribute("href")
                
                # Estrai la data
                data_obj = extract_date_from_text(data_testo)
                
                if data_obj is None:
                    print(f"Data non riconosciuta per '{titolo}': {data_testo}")
                    data_obj = oggi
                
                # Controlla se la circolare è nell'anno scolastico corrente
                if anno_scolastico_inizio <= data_obj <= anno_scolastico_fine:
                    # Estrai URL PDF
                    pdf_urls = []
                    if link and link.endswith('.pdf'):
                        pdf_urls.append(link)
                    else:
                        # Potrebbe esserci un link interno che porta ad un PDF
                        # Controlla se ci sono link PDF nell'elemento
                        try:
                            pdf_links = elem.find_elements(By.CSS_SELECTOR, "a[href$='.pdf']")
                            for pdf_link in pdf_links:
                                href = pdf_link.get_attribute("href")
                                if href:
                                    pdf_urls.append(href)
                        except:
                            pass
                    
                    # Formatta la data per il database
                    data_pubblica = data_obj.strftime("%Y-%m-%d %H:%M:%S")
                    
                    all_circolari.append({
                        'titolo': titolo,
                        'contenuto': "",
                        'data_pubblica': data_pubblica,
                        'pdf_url': ';;;'.join(pdf_urls) if pdf_urls else None
                    })
                    
                    print(f"  ✓ {titolo} ({data_obj.strftime('%d/%m/%Y')}) - PDF: {len(pdf_urls)}")
                
            except Exception as e:
                print(f"Errore processamento circolare: {e}")
                continue
        
        # Controlla se c'è una pagina successiva
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, ".pagination-next:not(.disabled), .next-page:not(.disabled)")
            if next_button.is_enabled() and next_button.is_displayed():
                # Scrolla fino al pulsante e clicca
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(1)
                next_button.click()
                page_number += 1
                time.sleep(3)  # Attendi il caricamento della nuova pagina
            else:
                print("Nessuna altra pagina disponibile.")
                break
        except Exception as e:
            print(f"Fine della paginazione o errore: {e}")
            break
    
    print(f"\nTotale circolari trovate per l'anno scolastico corrente: {len(all_circolari)}")
    
    # Rimuovi duplicati basati sul titolo
    unique_circolari = []
    seen_titles = set()
    
    for circ in all_circolari:
        if circ['titolo'] not in seen_titles:
            seen_titles.add(circ['titolo'])
            unique_circolari.append(circ)
    
    print(f"Dopo rimozione duplicati: {len(unique_circolari)} circolari")
    
    # Ottieni le circolari esistenti dal database
    existing_response = supabase.table('circolari').select("titolo, data_pubblica").execute()
    existing_titles = {item['titolo'] for item in existing_response.data}
    
    # Filtra solo le nuove circolari
    nuove_circolari = []
    for circ in unique_circolari:
        if circ['titolo'] not in existing_titles:
            nuove_circolari.append(circ)
    
    # Inserisci le nuove circolari
    if nuove_circolari:
        for circ in nuove_circolari:
            try:
                supabase.table('circolari').insert(circ).execute()
                print(f"Inserita: {circ['titolo']}")
            except Exception as e:
                print(f"Errore inserimento circolare '{circ['titolo']}': {e}")
        print(f"\nInserite {len(nuove_circolari)} nuove circolari")
    else:
        print("Nessuna nuova circolare trovata")
    
    # Pulisci le circolari troppo vecchie (fuori dall'anno scolastico)
    for existing in existing_response.data:
        try:
            if 'data_pubblica' in existing:
                data_existing = datetime.strptime(existing['data_pubblica'], "%Y-%m-%d %H:%M:%S")
                if data_existing < anno_scolastico_inizio:
                    supabase.table('circolari').delete().eq('titolo', existing['titolo']).execute()
                    print(f"Eliminata circolare fuori anno scolastico: {existing['titolo']}")
        except Exception as e:
            print(f"Errore eliminazione circolare: {e}")
            continue
    
    driver.quit()
    
except Exception as e:
    print(f"Errore durante lo scraping: {e}")
    import traceback
    print(traceback.format_exc())
    try:
        driver.quit()
    except:
        pass

print("✅ Robot completato")
