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

def click_all_years_buttons():
    """Clicca su tutti i pulsanti degli anni per espandere le circolari"""
    print("Cerco pulsanti degli anni/accordion...")
    
    # Prova diversi selettori per pulsanti di anni
    year_selectors = [
        "button[class*='anno']",
        "button[class*='year']",
        ".anno-button",
        ".year-button",
        "a[href*='anno']",
        "a[href*='year']",
        "li > a",  # Potrebbero essere link in una lista
        ".dropdown-toggle",
        ".btn-group > button"
    ]
    
    all_year_buttons = []
    
    for selector in year_selectors:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for btn in buttons:
                text = btn.text.strip()
                # Se il testo sembra un anno (contiene 2022, 2023, 2024, 2025, ecc.)
                if any(year in text for year in ['2022', '2023', '2024', '2025', '2026']):
                    if btn not in all_year_buttons:
                        all_year_buttons.append(btn)
                        print(f"  Trovato pulsante anno: '{text}'")
        except:
            continue
    
    # Se non trovati, cerca per testo
    if not all_year_buttons:
        try:
            # Cerca elementi che contengono anni
            year_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '2022') or contains(text(), '2023') or contains(text(), '2024') or contains(text(), '2025')]")
            for elem in year_elements:
                # Cerca un elemento cliccabile vicino
                try:
                    parent = elem.find_element(By.XPATH, "./ancestor::button | ./ancestor::a | ./ancestor::div[@onclick]")
                    if parent not in all_year_buttons:
                        all_year_buttons.append(parent)
                        print(f"  Trovato elemento anno (per testo): '{elem.text[:50]}...'")
                except:
                    continue
        except:
            pass
    
    # Clicca su tutti i pulsanti degli anni
    for btn in all_year_buttons:
        try:
            print(f"  Clicco su: '{btn.text[:50]}...'")
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(1)
            
            # Prova prima con JavaScript click
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(2)
            
            # Controlla se si è espanso
            try:
                btn.click()
                time.sleep(1)
            except:
                pass
                
        except Exception as e:
            print(f"  Errore clic pulsante: {e}")
            continue
    
    return len(all_year_buttons)

def find_and_click_pagination():
    """Cerca e clicca su elementi di paginazione"""
    print("Cerco elementi di paginazione...")
    
    # Prova diversi selettori di paginazione
    pagination_selectors = [
        ".pagination",
        ".page-numbers",
        ".pager",
        ".pages",
        ".load-more",
        "#loadMore",
        ".show-more",
        "button:contains('Carica')",
        "a:contains('altre')",
        "a:contains('more')",
        "a:contains('tutte')",
        "a:contains('all')"
    ]
    
    for selector in pagination_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for elem in elements:
                if elem.is_displayed():
                    print(f"  Trovato elemento paginazione: {selector}")
                    driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", elem)
                    time.sleep(3)
                    return True
        except:
            continue
    
    # Cerca per testo
    pagination_texts = ['Carica più', 'Mostra più', 'Altri risultati', 'Vedi tutte', 'Tutte le circolari']
    for text in pagination_texts:
        try:
            elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{text}')]")
            for elem in elements:
                if elem.is_displayed():
                    print(f"  Trovato per testo: '{text}'")
                    driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", elem)
                    time.sleep(3)
                    return True
        except:
            continue
    
    return False

def get_all_circolari_from_page():
    """Ottiene tutte le circolari dalla pagina corrente"""
    all_circ = []
    
    # Prova diversi selettori per trovare le righe delle circolari
    row_selectors = [
        "tr",  # Righe di tabella
        ".list-group-item",
        ".item",
        ".row",
        "div[class*='circ']",
        "li",
        ".card",
        ".panel"
    ]
    
    for selector in row_selectors:
        try:
            rows = driver.find_elements(By.CSS_SELECTOR, selector)
            print(f"  Trovate {len(rows)} righe con selettore: {selector}")
            
            for row in rows:
                try:
                    text = row.text.strip()
                    if not text or len(text) < 20:
                        continue
                    
                    # Cerca indicatori di circolare
                    has_circ_keyword = any(keyword in text.lower() for keyword in ['circolare', 'circ.', 'prot.', 'n. '])
                    has_date = re.search(r'\d{2}/\d{2}/\d{4}', text) or re.search(r'\d{2}-\d{2}-\d{4}', text)
                    
                    if has_circ_keyword or has_date:
                        # Estrai informazioni
                        lines = text.split('\n')
                        titolo = ""
                        data_testo = ""
                        
                        # Cerca la prima linea significativa come titolo
                        for line in lines:
                            if line.strip() and len(line.strip()) > 5:
                                titolo = line.strip()
                                break
                        
                        # Cerca una data
                        for line in lines:
                            if re.search(r'\d{2}/\d{2}/\d{4}', line) or re.search(r'\d{2}-\d{2}-\d{4}', line):
                                data_testo = line.strip()
                                break
                        
                        if not data_testo:
                            # Cerca la data nel testo completo
                            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
                            if date_match:
                                data_testo = date_match.group(1)
                        
                        # Cerca link PDF
                        pdf_urls = []
                        try:
                            links = row.find_elements(By.TAG_NAME, "a")
                            for link in links:
                                href = link.get_attribute("href")
                                if href and href.endswith('.pdf'):
                                    pdf_urls.append(href)
                        except:
                            pass
                        
                        if titolo:
                            all_circ.append({
                                'element': row,
                                'titolo': titolo,
                                'data_testo': data_testo,
                                'pdf_urls': pdf_urls,
                                'full_text': text[:200] + "..." if len(text) > 200 else text
                            })
                except Exception as e:
                    continue
                    
            if all_circ:
                break
                
        except:
            continue
    
    return all_circ

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
    
    circolari_link = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Circolari"))
    )
    circolari_link.click()
    
    print("Aspetto caricamento pagina circolari...")
    time.sleep(5)
    
    # STRATEGIA 1: Clicca su tutti i pulsanti degli anni
    print("\n=== STRATEGIA 1: Espansione anni ===")
    years_clicked = click_all_years_buttons()
    print(f"Cliccati {years_clicked} pulsanti anni")
    time.sleep(3)
    
    # STRATEGIA 2: Cerca paginazione
    print("\n=== STRATEGIA 2: Paginazione ===")
    pagination_found = find_and_click_pagination()
    if pagination_found:
        print("Trovata e cliccata paginazione")
        time.sleep(3)
    
    # STRATEGIA 3: Scrolling multiplo
    print("\n=== STRATEGIA 3: Scrolling approfondito ===")
    for i in range(5):
        print(f"  Scroll {i+1}/5")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
    
    # STRATEGIA 4: Cerca sezioni nascoste
    print("\n=== STRATEGIA 4: Ricerca sezioni nascoste ===")
    try:
        # Cerca elementi collassati/accordion
        collapsed_selectors = [
            ".collapse",
            ".collapsed",
            "[aria-expanded='false']",
            ".hidden",
            ".d-none"
        ]
        
        for selector in collapsed_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"  Trovati {len(elements)} elementi con: {selector}")
                
                for elem in elements:
                    try:
                        # Prova ad espandere
                        driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                        driver.execute_script("arguments[0].setAttribute('class', arguments[0].getAttribute('class').replace('collapse', '').replace('collapsed', ''));", elem)
                        driver.execute_script("arguments[0].setAttribute('aria-expanded', 'true');", elem)
                        driver.execute_script("arguments[0].style.display = 'block';", elem)
                    except:
                        continue
            except:
                continue
    except Exception as e:
        print(f"  Errore ricerca sezioni nascoste: {e}")
    
    time.sleep(3)
    
    # STRATEGIA 5: Cerca e clicca su tutte le tab
    print("\n=== STRATEGIA 5: Ricerca tab ===")
    try:
        tabs = driver.find_elements(By.CSS_SELECTOR, ".nav-tabs a, .nav-pills a, .tab-pane a, [role='tab']")
        print(f"  Trovate {len(tabs)} tab/links")
        
        for tab in tabs:
            try:
                if tab.is_displayed():
                    tab_text = tab.text.strip()
                    if tab_text and len(tab_text) > 0:
                        print(f"  Clicco tab: '{tab_text}'")
                        driver.execute_script("arguments[0].click();", tab)
                        time.sleep(2)
            except:
                continue
    except Exception as e:
        print(f"  Errore gestione tab: {e}")
    
    time.sleep(3)
    
    # Fai screenshot finale per debug
    print("\nFaccio screenshot finale...")
    driver.save_screenshot("circolari_finale.png")
    print("Screenshot salvato come circolari_finale.png")
    
    # ORA raccogli tutte le circolari
    print("\n=== RACCOLTA CIRCOLARI ===")
    all_circolari_data = get_all_circolari_from_page()
    
    print(f"\nTotale elementi trovati: {len(all_circolari_data)}")
    
    # Processa e filtra per anno scolastico
    all_circolari = []
    
    for idx, circ_data in enumerate(all_circolari_data, 1):
        try:
            titolo = circ_data['titolo']
            data_testo = circ_data['data_testo']
            pdf_urls = circ_data['pdf_urls']
            
            print(f"\n[{idx}] Analizzo: {titolo[:80]}...")
            print(f"    Data: {data_testo}")
            print(f"    PDF: {len(pdf_urls)} trovati")
            
            # Estrai la data
            data_obj = extract_date_from_text(data_testo)
            
            if data_obj is None:
                # Prova a cercare la data nel titolo
                data_obj = extract_date_from_text(titolo)
                if data_obj is None:
                    data_obj = oggi
            
            # Controlla se la circolare è nell'anno scolastico corrente
            if anno_scolastico_inizio <= data_obj <= anno_scolastico_fine:
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
                print(f"    ❌ SCARTATA - Fuori anno scolastico: {data_obj.strftime('%d/%m/%Y')}")
                
        except Exception as e:
            print(f"    ❌ ERRORE elaborazione: {e}")
            continue
    
    print(f"\n=== RISULTATO FINALE ===")
    print(f"Circolari valide per l'anno scolastico corrente: {len(all_circolari)}")
    
    # Stampa riepilogo
    for i, circ in enumerate(all_circolari, 1):
        print(f"{i:2}. {circ['titolo'][:60]}... ({circ['data_pubblica'][:10]})")
    
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
                    print(f"  ❌ Errore: {e}")
        else:
            print("Nessuna nuova circolare da inserire")
    else:
        print("Nessuna circolare trovata")
    
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
