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
    if not data_text:
        return None
    
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
    
    # Cerca anche nel formato Data: 25/10/2024
    match = re.search(r'Data\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})', data_text, re.IGNORECASE)
    if match:
        try:
            giorno, mese, anno = map(int, match.group(1).split('/'))
            return datetime(anno, mese, giorno)
        except:
            pass
    
    return None

try:
    oggi = datetime.now()
    limite_30_giorni = oggi - timedelta(days=30)
    
    print(f"Data limite (ultimi 30 giorni): {limite_30_giorni.strftime('%d/%m/%Y')}")
    
    driver.get("https://www.portaleargo.it/famiglia")
    time.sleep(3)
    
    username = driver.find_element(By.ID, "username")
    password = driver.find_element(By.ID, "password")
    
    username.send_keys(config['ARGO_USER'])
    password.send_keys(config['ARGO_PASS'])
    
    login_button = driver.find_element(By.ID, "login-button")
    login_button.click()
    
    time.sleep(5)
    
    circolari_link = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Circolari"))
    )
    circolari_link.click()
    
    print("Aspetto caricamento pagina circolari...")
    time.sleep(5)
    
    # Fai screenshot per debug
    driver.save_screenshot("circolari_page.png")
    print("Screenshot salvato come circolari_page.png")
    
    all_circolari = []
    
    # PRIMO TENTATIVO: Usa i selettori originali del tuo codice
    try:
        circolari_elements = driver.find_elements(By.CSS_SELECTOR, ".circolare-item")
        print(f"Trovate {len(circolari_elements)} circolari con .circolare-item")
    except:
        circolari_elements = []
        print("Nessuna circolare trovata con .circolare-item")
    
    # SECONDO TENTATIVO: Se non trovi abbastanza, prova altri selettori
    if len(circolari_elements) < 5:
        try:
            # Cerca qualsiasi elemento che sembra una circolare
            all_elements = driver.find_elements(By.CSS_SELECTOR, "div, tr, li, .card, .panel")
            for elem in all_elements:
                try:
                    text = elem.text.strip()
                    if text and len(text) > 30:
                        # Controlla se sembra una circolare
                        if any(keyword in text.lower() for keyword in ['circolare', 'prot.', 'n. ']):
                            if re.search(r'\d{2}/\d{2}/\d{4}', text):
                                circolari_elements.append(elem)
                except:
                    continue
            print(f"Trovate {len(circolari_elements)} circolari con ricerca generica")
        except Exception as e:
            print(f"Errore ricerca generica: {e}")
    
    # TERZO TENTATIVO: Cerca per testo "Circolare"
    if len(circolari_elements) < 5:
        try:
            circolari_by_text = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'CIRC', 'circ'), 'circolare')]")
            for elem in circolari_by_text:
                try:
                    parent = elem.find_element(By.XPATH, "./ancestor::div[1]")
                    if parent not in circolari_elements:
                        circolari_elements.append(parent)
                except:
                    if elem not in circolari_elements:
                        circolari_elements.append(elem)
            print(f"Trovate {len(circolari_elements)} circolari per testo")
        except Exception as e:
            print(f"Errore ricerca per testo: {e}")
    
    print(f"\nElaborazione di {len(circolari_elements)} elementi trovati...")
    
    for idx, elem in enumerate(circolari_elements, 1):
        try:
            # Prendi il testo completo
            full_text = elem.text.strip()
            if not full_text or len(full_text) < 20:
                continue
            
            print(f"\n[{idx}] Testo completo (primi 100 caratteri): {full_text[:100]}...")
            
            # Dividi in linee
            lines = full_text.split('\n')
            
            # Cerca titolo (prima linea significativa)
            titolo = ""
            for line in lines:
                line = line.strip()
                if line and len(line) > 5:
                    titolo = line
                    break
            
            # Cerca data
            data_testo = ""
            for line in lines:
                line = line.strip()
                # Cerca pattern di data
                if re.search(r'\d{2}/\d{2}/\d{4}', line):
                    data_testo = line
                    break
            
            # Se non trovata, cerca nel testo completo
            if not data_testo:
                match = re.search(r'(\d{2}/\d{2}/\d{4})', full_text)
                if match:
                    data_testo = match.group(1)
            
            # Cerca link PDF
            pdf_urls = []
            try:
                links = elem.find_elements(By.TAG_NAME, "a")
                for link in links:
                    try:
                        href = link.get_attribute("href")
                        if href and (href.endswith('.pdf') or 'pdf' in href.lower()):
                            pdf_urls.append(href)
                    except:
                        continue
            except:
                pass
            
            print(f"    Titolo: {titolo[:60]}...")
            print(f"    Data testo: {data_testo}")
            print(f"    PDF trovati: {len(pdf_urls)}")
            
            # Estrai la data
            data_obj = extract_date_from_text(data_testo)
            
            if data_obj is None:
                print(f"    ⚠️  Data non riconosciuta: '{data_testo}'")
                # Assegna data di oggi
                data_obj = oggi
            
            # Controlla se la circolare è negli ultimi 30 giorni
            if data_obj >= limite_30_giorni:
                # Formatta la data per il database
                data_pubblica = data_obj.strftime("%Y-%m-%d %H:%M:%S")
                
                all_circolari.append({
                    'titolo': titolo,
                    'contenuto': "",
                    'data_pubblica': data_pubblica,
                    'pdf_url': ';;;'.join(pdf_urls) if pdf_urls else None
                })
                
                print(f"    ✅ AGGIUNTA - {data_obj.strftime('%d/%m/%Y')}")
            else:
                print(f"    ❌ SCARTATA - Troppo vecchia: {data_obj.strftime('%d/%m/%Y')}")
                
        except Exception as e:
            print(f"    ❌ ERRORE elaborazione: {str(e)[:100]}...")
            continue
    
    print(f"\n=== RISULTATO FINALE ===")
    print(f"Circolari negli ultimi 30 giorni: {len(all_circolari)}")
    
    # Stampa riepilogo
    for i, circ in enumerate(all_circolari, 1):
        data_str = circ['data_pubblica'][:10] if circ['data_pubblica'] else "N/D"
        print(f"{i:2}. {data_str} - {circ['titolo'][:60]}...")
    
    # Inserisci nel database
    if all_circolari:
        print(f"\nInserimento nel database...")
        
        # Ottieni le circolari esistenti
        existing_response = supabase.table('circolari').select("titolo, data_pubblica").execute()
        existing_titles = {item['titolo'] for item in existing_response.data}
        
        # Filtra solo le nuove
        nuove_circolari = []
        for circ in all_circolari:
            if circ['titolo'] not in existing_titles:
                nuove_circolari.append(circ)
        
        if nuove_circolari:
            print(f"Trovate {len(nuove_circolari)} nuove circolari da inserire")
            for circ in nuove_circolari:
                try:
                    supabase.table('circolari').insert(circ).execute()
                    print(f"  ✅ Inserita: {circ['titolo'][:60]}...")
                except Exception as e:
                    print(f"  ❌ Errore inserimento: {str(e)[:100]}...")
            
            print(f"\n✅ Completato! Inserite {len(nuove_circolari)} nuove circolari")
        else:
            print("✅ Nessuna nuova circolare trovata")
        
        # Pulisci le circolari più vecchie di 30 giorni
        print("\nPulizia circolari vecchie (>30 giorni)...")
        deleted_count = 0
        for existing in existing_response.data:
            try:
                if 'data_pubblica' in existing:
                    data_existing = datetime.strptime(existing['data_pubblica'], "%Y-%m-%d %H:%M:%S")
                    if data_existing < limite_30_giorni:
                        supabase.table('circolari').delete().eq('titolo', existing['titolo']).execute()
                        deleted_count += 1
            except Exception as e:
                print(f"  Errore eliminazione {existing.get('titolo', 'N/D')}: {str(e)[:100]}...")
                continue
        
        if deleted_count > 0:
            print(f"🗑️  Eliminate {deleted_count} circolari vecchie")
    else:
        print("Nessuna circolare trovata negli ultimi 30 giorni")
    
    driver.quit()
    
except Exception as e:
    print(f"❌ Errore durante lo scraping: {e}")
    import traceback
    traceback.print_exc()
    try:
        driver.quit()
    except:
        pass

print("✅ Robot completato")
