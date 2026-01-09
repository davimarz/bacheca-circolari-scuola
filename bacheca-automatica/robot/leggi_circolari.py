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
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

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
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, data_text)
        if match:
            try:
                giorno, mese, anno = map(int, match.groups())
                return datetime(anno, mese, giorno)
            except:
                continue
    
    return None

def click_load_more_button():
    """Cerca e clicca il pulsante 'Carica altre' o simile"""
    print("Cerco pulsante 'Carica altre'...")
    
    # Prova diversi testi per il pulsante
    button_texts = [
        "Carica altre",
        "Carica più",
        "Mostra altre",
        "Mostra più",
        "Altri risultati",
        "Altre circolari",
        "Visualizza tutte",
        "Vedi tutte",
        "Load more",
        "Show more"
    ]
    
    for text in button_texts:
        try:
            # Cerca per testo esatto o parziale
            buttons = driver.find_elements(By.XPATH, f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')] | //a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')] | //input[@value[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]]")
            
            for btn in buttons:
                if btn.is_displayed() and btn.is_enabled():
                    print(f"  Trovato pulsante: '{btn.text}'")
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(3)
                    return True
        except:
            continue
    
    # Cerca per ID o classe comune
    button_selectors = [
        "#loadMore",
        ".load-more",
        ".btn-more",
        ".more-button",
        "[onclick*='load']",
        "[onclick*='more']"
    ]
    
    for selector in button_selectors:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for btn in buttons:
                if btn.is_displayed() and btn.is_enabled():
                    print(f"  Trovato pulsante con selettore: {selector}")
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(3)
                    return True
        except:
            continue
    
    print("  Nessun pulsante 'Carica altre' trovato")
    return False

def find_all_circolari_blocks():
    """Trova tutti i blocchi delle circolari"""
    print("Cerco blocchi delle circolari...")
    
    all_blocks = []
    
    # STRATEGIA 1: Cerca blocchi che iniziano con pattern tipo "S.A. X°"
    try:
        # Usa XPath per trovare elementi che contengono "S.A." seguito da un numero
        sa_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'S.A.')]")
        
        for elem in sa_elements:
            try:
                # Prendi il blocco genitore (div, p, o altro)
                parent = elem.find_element(By.XPATH, "./ancestor::div[1] | ./ancestor::p[1] | ./ancestor::td[1] | ./ancestor::li[1]")
                if parent not in all_blocks:
                    all_blocks.append(parent)
            except:
                if elem not in all_blocks:
                    all_blocks.append(elem)
        
        print(f"  Trovati {len(sa_elements)} elementi con 'S.A.'")
    except Exception as e:
        print(f"  Errore ricerca 'S.A.': {e}")
    
    # STRATEGIA 2: Cerca per date (pattern DD/MM/YYYY)
    try:
        date_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '/202')]")
        
        for elem in date_elements:
            try:
                # Prendi il blocco genitore
                parent = elem.find_element(By.XPATH, "./ancestor::div[1] | ./ancestor::p[1]")
                if parent not in all_blocks:
                    all_blocks.append(parent)
            except:
                if elem not in all_blocks:
                    all_blocks.append(elem)
        
        print(f"  Trovati {len(date_elements)} elementi con date")
    except Exception as e:
        print(f"  Errore ricerca date: {e}")
    
    # STRATEGIA 3: Cerca elementi con testo lungo (probabilmente circolari)
    try:
        all_elements = driver.find_elements(By.CSS_SELECTOR, "div, p, td, li")
        
        for elem in all_elements:
            try:
                text = elem.text.strip()
                if text and len(text) > 100:  # Testo lungo = probabile circolare
                    # Controlla se ha caratteristiche di una circolare
                    has_date = re.search(r'\d{2}/\d{2}/\d{4}', text)
                    has_circ_keywords = any(keyword in text.lower() for keyword in ['oggetto', 'circolare', 'prot.', 'n.'])
                    
                    if has_date or has_circ_keywords:
                        if elem not in all_blocks:
                            all_blocks.append(elem)
            except:
                continue
        
        print(f"  Trovati {len(all_elements)} elementi totali, filtrati {len(all_blocks)} blocchi lunghi")
    except Exception as e:
        print(f"  Errore ricerca generica: {e}")
    
    # Rimuovi duplicati (per sicurezza)
    unique_blocks = []
    seen_texts = set()
    
    for block in all_blocks:
        try:
            text = block.text.strip()
            if text and text not in seen_texts:
                seen_texts.add(text)
                unique_blocks.append(block)
        except:
            continue
    
    print(f"  Blocchi unici trovati: {len(unique_blocks)}")
    return unique_blocks

def extract_circolare_info(block):
    """Estrae informazioni da un blocco circolare"""
    try:
        text = block.text.strip()
        if not text or len(text) < 50:
            return None
        
        print(f"\n  Analizzo blocco (primi 150 caratteri):")
        print(f"    {text[:150]}...")
        
        # Cerca il titolo/oggetto
        titolo = ""
        
        # Pattern 1: Cerca riga che inizia con "S.A." o simile
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line and (line.startswith('S.A.') or line.startswith('OGGETTO:') or line.startswith('Oggetto:')):
                titolo = line
                break
        
        # Pattern 2: Se non trovato, prendi la prima riga significativa
        if not titolo:
            for line in lines:
                line = line.strip()
                if line and len(line) > 20:
                    titolo = line[:200]  # Limita la lunghezza
                    break
        
        # Cerca la data
        data_testo = ""
        
        # Cerca pattern di data nel testo
        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
        if date_match:
            data_testo = date_match.group(1)
        else:
            # Cerca nel titolo
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', titolo)
            if date_match:
                data_testo = date_match.group(1)
        
        # Cerca link PDF nel blocco
        pdf_urls = []
        try:
            links = block.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href:
                        # Controlla se è un PDF
                        if href.lower().endswith('.pdf'):
                            pdf_urls.append(href)
                        elif 'download' in href.lower() or 'pdf' in href.lower():
                            pdf_urls.append(href)
                except:
                    continue
        except:
            pass
        
        return {
            'full_text': text,
            'titolo': titolo or "Circolare senza titolo",
            'data_testo': data_testo,
            'pdf_urls': pdf_urls
        }
        
    except Exception as e:
        print(f"  Errore estrazione info: {e}")
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
    
    # STRATEGIA: Prova a caricare più circolari cliccando "Carica altre"
    print("\n=== TENTATIVO DI CARICARE PIÙ CIRCOLARI ===")
    
    # Prima cerca e clicca il pulsante "Carica altre" più volte
    for attempt in range(5):  # Prova fino a 5 volte
        print(f"\nTentativo {attempt + 1}/5:")
        found = click_load_more_button()
        if not found:
            print("Nessun pulsante trovato, provo scrolling...")
            # Fai scroll per caricare contenuti lazy
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
    
    time.sleep(3)
    
    # Ora cerca tutti i blocchi delle circolari
    print("\n=== RICERCA CIRCOLARI ===")
    circolari_blocks = find_all_circolari_blocks()
    
    print(f"\nTotale blocchi trovati: {len(circolari_blocks)}")
    
    # Processa tutti i blocchi
    all_circolari = []
    
    for idx, block in enumerate(circolari_blocks, 1):
        print(f"\n[{idx}] Processing block...")
        
        info = extract_circolare_info(block)
        if not info:
            print("  ⚠️  Info non estratta, salto")
            continue
        
        titolo = info['titolo']
        data_testo = info['data_testo']
        pdf_urls = info['pdf_urls']
        
        print(f"  Titolo: {titolo[:80]}...")
        print(f"  Data testo: {data_testo}")
        print(f"  PDF trovati: {len(pdf_urls)}")
        
        # Estrai la data
        data_obj = extract_date_from_text(data_testo)
        
        if data_obj is None:
            print(f"  ⚠️  Data non riconosciuta: '{data_testo}'")
            # Assegna data di oggi
            data_obj = oggi
        else:
            print(f"  Data estratta: {data_obj.strftime('%d/%m/%Y')}")
        
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
            
            print(f"  ✅ AGGIUNTA - {data_obj.strftime('%d/%m/%Y')}")
        else:
            print(f"  ❌ SCARTATA - Troppo vecchia: {data_obj.strftime('%d/%m/%Y')}")
    
    print(f"\n=== RISULTATO FINALE ===")
    print(f"Circolari negli ultimi 30 giorni: {len(all_circolari)}")
    
    # Stampa riepilogo
    for i, circ in enumerate(all_circolari, 1):
        data_str = circ['data_pubblica'][:10] if circ['data_pubblica'] else "N/D"
        print(f"{i:2}. {data_str} - {circ['titolo'][:80]}...")
    
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
                    print(f"  ✅ Inserita: {circ['titolo'][:80]}...")
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
