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

def scroll_page_to_load_all_circolari():
    """Fa scrolling della pagina per caricare tutte le circolari"""
    print("Inizio scrolling per caricare tutte le circolari...")
    
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    max_attempts = 20  # Numero massimo di tentativi di scroll
    last_element_count = 0
    same_count_counter = 0
    
    while scroll_attempts < max_attempts:
        # Trova gli elementi attuali
        current_elements = driver.find_elements(By.CSS_SELECTOR, ".circolare-item")
        current_count = len(current_elements)
        
        print(f"Tentativo {scroll_attempts + 1}: {current_count} circolari trovate")
        
        # Se il numero di elementi non è cambiato per 3 volte consecutive, probabilmente abbiamo caricato tutto
        if current_count == last_element_count:
            same_count_counter += 1
            if same_count_counter >= 3:
                print(f"Numero di circolari stabile a {current_count} per 3 tentativi consecutivi. Stop.")
                break
        else:
            same_count_counter = 0
            last_element_count = current_count
        
        # Fai scroll fino in fondo
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Attendi il caricamento
        
        # Controlla se c'è un pulsante "Carica più" o simile
        try:
            load_more_button = driver.find_element(By.CSS_SELECTOR, ".load-more, .carica-altre, .more-button, button:contains('Carica')")
            if load_more_button.is_displayed():
                print("Trovato pulsante 'Carica più', clicco...")
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
                time.sleep(1)
                load_more_button.click()
                time.sleep(3)
        except:
            pass  # Nessun pulsante "Carica più" trovato
        
        # Calcola nuova altezza dopo scroll
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            scroll_attempts += 1
            print(f"Altezza non cambiata dopo scroll. Tentativo {scroll_attempts}/{max_attempts}")
        else:
            last_height = new_height
            scroll_attempts = 0  # Reset se c'è stato un cambiamento
        
        time.sleep(1.5)
    
    # Final scroll to top
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    final_elements = driver.find_elements(By.CSS_SELECTOR, ".circolare-item")
    print(f"Scrolling completato. Totale circolari caricate: {len(final_elements)}")
    
    return final_elements

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
    
    # Usa la funzione di scrolling per caricare TUTTE le circolari
    circolari_elements = scroll_page_to_load_all_circolari()
    
    print(f"\nElaborazione delle {len(circolari_elements)} circolari caricate...")
    
    for idx, elem in enumerate(circolari_elements, 1):
        try:
            # Scrolla l'elemento in vista per sicurezza
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elem)
            time.sleep(0.5)
            
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
                print(f"  [{idx}] Data non riconosciuta per '{titolo}': {data_testo}")
                data_obj = oggi
            
            # Controlla se la circolare è nell'anno scolastico corrente
            if anno_scolastico_inizio <= data_obj <= anno_scolastico_fine:
                # Estrai URL PDF
                pdf_urls = []
                if link and link.endswith('.pdf'):
                    pdf_urls.append(link)
                else:
                    # Cerca link PDF all'interno dell'elemento circolare
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
                
                print(f"  [{idx}] ✓ {titolo} ({data_obj.strftime('%d/%m/%Y')}) - PDF: {len(pdf_urls)}")
            else:
                print(f"  [{idx}] ✗ {titolo} ({data_obj.strftime('%d/%m/%Y')}) - FUORI ANNO SCOLASTICO")
                
        except Exception as e:
            print(f"  [{idx}] Errore processamento circolare: {e}")
            continue
    
    print(f"\nTotale circolari trovate per l'anno scolastico corrente: {len(all_circolari)}")
    
    # Ottieni le circolari esistenti dal database
    existing_response = supabase.table('circolari').select("titolo, data_pubblica").execute()
    existing_titles = {item['titolo'] for item in existing_response.data}
    
    # Filtra solo le nuove circolari
    nuove_circolari = []
    for circ in all_circolari:
        if circ['titolo'] not in existing_titles:
            nuove_circolari.append(circ)
    
    # Inserisci le nuove circolari
    if nuove_circolari:
        print(f"\nInserimento di {len(nuove_circolari)} nuove circolari...")
        for circ in nuove_circolari:
            try:
                supabase.table('circolari').insert(circ).execute()
                print(f"  Inserita: {circ['titolo']}")
            except Exception as e:
                print(f"  Errore inserimento circolare '{circ['titolo']}': {e}")
        print(f"\n✅ Inserite {len(nuove_circolari)} nuove circolari")
    else:
        print("✅ Nessuna nuova circolare trovata")
    
    # Pulisci le circolari troppo vecchie (fuori dall'anno scolastico)
    print("\nPulizia circolari fuori anno scolastico...")
    deleted_count = 0
    for existing in existing_response.data:
        try:
            if 'data_pubblica' in existing:
                data_existing = datetime.strptime(existing['data_pubblica'], "%Y-%m-%d %H:%M:%S")
                if data_existing < anno_scolastico_inizio:
                    supabase.table('circolari').delete().eq('titolo', existing['titolo']).execute()
                    deleted_count += 1
                    print(f"  Eliminata: {existing['titolo']}")
        except Exception as e:
            print(f"  Errore eliminazione circolare: {e}")
            continue
    
    if deleted_count > 0:
        print(f"🗑️  Eliminate {deleted_count} circolari fuori anno scolastico")
    
    driver.quit()
    
except Exception as e:
    print(f"❌ Errore durante lo scraping: {e}")
    import traceback
    print(traceback.format_exc())
    try:
        driver.quit()
    except:
        pass

print("✅ Robot completato")
