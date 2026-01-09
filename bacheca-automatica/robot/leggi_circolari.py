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

def find_all_circolari_elements():
    """Cerca tutti gli elementi delle circolari con diversi selettori"""
    all_elements = []
    
    # Prova diversi selettori comuni
    selectors = [
        ".circolare-item",
        ".circolare",
        ".item-circolare",
        "div[class*='circolare']",
        "li[class*='circolare']",
        ".list-item",
        ".elenco-item",
        "tr[class*='circolare']",
        ".table-row",
        "a[href*='circolare']",
        "a[href*='circolari']",
        "div.card",
        ".panel",
        ".box"
    ]
    
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"Trovati {len(elements)} elementi con selettore: {selector}")
                # Filtra solo elementi che sembrano circolari (hanno testo e possibilmente una data)
                for elem in elements:
                    text = elem.text.strip()
                    if text and len(text) > 10:  # Almeno un minimo di testo
                        # Cerca indicatori di una circolare
                        if any(keyword in text.lower() for keyword in ['circolare', 'n.', 'prot.', 'data', '/202', '/2023', '/2024', '/2025']):
                            if elem not in all_elements:
                                all_elements.append(elem)
        except:
            continue
    
    # Se non abbiamo trovato abbastanza, proviamo con XPath più generici
    if len(all_elements) < 10:
        try:
            # Cerca elementi che contengono date
            date_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '/202') or contains(text(), '-202')]")
            for elem in date_elements:
                parent = elem.find_element(By.XPATH, "./ancestor::div[1]")
                if parent not in all_elements:
                    all_elements.append(parent)
        except:
            pass
    
    return all_elements

def extract_circolare_info(element):
    """Estrae informazioni da un elemento circolare"""
    try:
        # Prima cerca titolo e data con selettori specifici
        titolo = ""
        data_testo = ""
        link = ""
        
        # Prova diversi selettori per il titolo
        title_selectors = [
            ".circolare-titolo",
            ".titolo",
            "h3", "h4", "h5",
            "strong", "b",
            ".title",
            ".subject"
        ]
        
        for selector in title_selectors:
            try:
                titolo_elem = element.find_element(By.CSS_SELECTOR, selector)
                titolo = titolo_elem.text.strip()
                if titolo:
                    break
            except:
                continue
        
        # Se non trovato, prendi il primo elemento con testo significativo
        if not titolo:
            try:
                # Prendi tutto il testo e estrai la prima riga significativa
                full_text = element.text.strip()
                lines = full_text.split('\n')
                for line in lines:
                    if line.strip() and len(line.strip()) > 5:
                        titolo = line.strip()
                        break
            except:
                pass
        
        # Cerca la data
        date_selectors = [
            ".circolare-data",
            ".data",
            ".date",
            ".pubblicazione",
            "span[class*='data']",
            "small",
            "em"
        ]
        
        for selector in date_selectors:
            try:
                data_elem = element.find_element(By.CSS_SELECTOR, selector)
                data_testo = data_elem.text.strip()
                if data_testo:
                    break
            except:
                continue
        
        # Se non trovata, cerca nel testo completo
        if not data_testo:
            try:
                full_text = element.text
                # Cerca pattern di data
                date_patterns = [
                    r'(\d{2}/\d{2}/\d{4})',
                    r'(\d{2}-\d{2}-\d{4})',
                    r'(\d{2}\.\d{2}\.\d{4})',
                    r'Data:\s*(\d{2}/\d{2}/\d{4})',
                    r'Pubblicato:\s*(\d{2}/\d{2}/\d{4})'
                ]
                for pattern in date_patterns:
                    match = re.search(pattern, full_text)
                    if match:
                        data_testo = match.group(1)
                        break
            except:
                pass
        
        # Cerca link
        try:
            link_elem = element.find_element(By.CSS_SELECTOR, "a")
            link = link_elem.get_attribute("href")
        except:
            # Cerca qualsiasi link nell'elemento
            try:
                links = element.find_elements(By.CSS_SELECTOR, "a")
                for link_elem in links:
                    href = link_elem.get_attribute("href")
                    if href:
                        link = href
                        break
            except:
                pass
        
        return {
            'titolo': titolo or "Circolare senza titolo",
            'data_testo': data_testo,
            'link': link,
            'element': element
        }
    
    except Exception as e:
        print(f"Errore estrazione info: {e}")
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
    
    circolari_link = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Circolari"))
    )
    circolari_link.click()
    
    print("Aspetto caricamento pagina circolari...")
    time.sleep(5)
    
    # Aspetta che la pagina sia completamente caricata
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    
    all_circolari = []
    
    # PRIMA: Fai una screenshot per debug
    print("Faccio screenshot per debug...")
    driver.save_screenshot("debug_page.png")
    print("Screenshot salvato come debug_page.png")
    
    # SECONDA: Stampa il codice HTML per capire la struttura
    print("\n=== ANALISI STRUTTURA PAGINA ===")
    page_html = driver.page_source[:5000]  # Primi 5000 caratteri
    print(page_html)
    print("=== FINE ANALISI ===\n")
    
    # TERZA: Cerca elementi con diversi approcci
    print("Cerco elementi delle circolari...")
    
    # Approccio 1: Cerca per testo che contiene "Circolare"
    try:
        circolari_by_text = driver.find_elements(By.XPATH, "//*[contains(text(), 'Circolare') or contains(text(), 'circolare')]")
        print(f"Trovati {len(circolari_by_text)} elementi che contengono 'Circolare' nel testo")
        
        # Prendi i genitori di questi elementi
        for elem in circolari_by_text[:20]:  # Limita per non esagerare
            try:
                parent = elem.find_element(By.XPATH, "./ancestor::div[1] | ./ancestor::tr[1] | ./ancestor::li[1]")
                info = extract_circolare_info(parent)
                if info:
                    print(f"Trovata circolare: {info['titolo'][:50]}...")
            except:
                continue
    except Exception as e:
        print(f"Errore ricerca per testo: {e}")
    
    # Approccio 2: Cerca tutti i link
    try:
        all_links = driver.find_elements(By.TAG_NAME, "a")
        print(f"Trovati {len(all_links)} link totali")
        
        # Filtra link che potrebbero essere circolari
        circolari_links = []
        for link in all_links:
            try:
                href = link.get_attribute("href")
                text = link.text.strip()
                if href and text:
                    # Cerca indicatori di circolare
                    if any(indicator in text.lower() for indicator in ['circolare', 'n.', 'prot.', 'circ.']) or \
                       any(indicator in href.lower() for indicator in ['circolare', 'circolari']):
                        circolari_links.append(link)
            except:
                continue
        
        print(f"Trovati {len(circolari_links)} link che sembrano circolari")
    except Exception as e:
        print(f"Errore ricerca link: {e}")
    
    # QUARTA: Usa la funzione di ricerca migliorata
    print("\n=== RICERCA APPROFONDITA ===")
    circolari_elements = find_all_circolari_elements()
    print(f"Totale elementi trovati: {len(circolari_elements)}")
    
    # Processa gli elementi trovati
    for idx, elem in enumerate(circolari_elements[:50], 1):  # Limita a 50 per test
        try:
            info = extract_circolare_info(elem)
            if not info:
                continue
            
            titolo = info['titolo']
            data_testo = info['data_testo']
            link = info['link']
            
            print(f"\n[{idx}] Analizzo: {titolo[:80]}...")
            print(f"    Data testo: {data_testo}")
            print(f"    Link: {link[:100] if link else 'Nessun link'}")
            
            # Estrai la data
            data_obj = extract_date_from_text(data_testo)
            
            if data_obj is None:
                print(f"    ⚠️  Data non riconosciuta: '{data_testo}'")
                # Prova a cercare la data nel titolo
                data_obj = extract_date_from_text(titolo)
                if data_obj is None:
                    data_obj = oggi
            
            # Controlla se la circolare è nell'anno scolastico corrente
            if anno_scolastico_inizio <= data_obj <= anno_scolastico_fine:
                # Estrai URL PDF
                pdf_urls = []
                if link and link.endswith('.pdf'):
                    pdf_urls.append(link)
                else:
                    # Cerca link PDF nell'elemento
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
                
                print(f"    ✅ AGGIUNTA - {data_obj.strftime('%d/%m/%Y')} - PDF: {len(pdf_urls)}")
            else:
                print(f"    ❌ SCARTATA - Fuori anno scolastico: {data_obj.strftime('%d/%m/%Y')}")
                
        except Exception as e:
            print(f"    ❌ ERRORE elaborazione: {e}")
            continue
    
    print(f"\n=== RISULTATO FINALE ===")
    print(f"Totale circolari trovate per l'anno scolastico corrente: {len(all_circolari)}")
    
    # Stampa riepilogo
    for i, circ in enumerate(all_circolari, 1):
        print(f"{i:2}. {circ['titolo'][:60]}... ({circ['data_pubblica'][:10]})")
    
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
                print(f"  ✅ Inserita: {circ['titolo'][:60]}...")
            except Exception as e:
                print(f"  ❌ Errore inserimento: {e}")
        print(f"\n✅ Completato! Inserite {len(nuove_circolari)} nuove circolari")
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
        except Exception as e:
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
