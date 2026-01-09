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

try:
    oggi = datetime.now()
    limite_30_giorni = oggi - timedelta(days=30)
    
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
    
    circolari_elements = driver.find_elements(By.CSS_SELECTOR, ".circolare-item")
    
    for elem in circolari_elements:
        try:
            titolo_elem = elem.find_element(By.CSS_SELECTOR, ".circolare-titolo")
            data_elem = elem.find_element(By.CSS_SELECTOR, ".circolare-data")
            link_elem = elem.find_element(By.CSS_SELECTOR, "a")
            
            titolo = titolo_elem.text.strip()
            data_testo = data_elem.text.strip()
            link = link_elem.get_attribute("href")
            
            match = re.search(r'(\d{2})/(\d{2})/(\d{4})', data_testo)
            if match:
                giorno, mese, anno = match.groups()
                data_pubblica = f"{anno}-{mese}-{giorno} 00:00:00"
                data_obj = datetime(int(anno), int(mese), int(giorno))
                
                if data_obj >= limite_30_giorni:
                    pdf_urls = []
                    if link and link.endswith('.pdf'):
                        pdf_urls.append(link)
                    
                    all_circolari.append({
                        'titolo': titolo,
                        'contenuto': "",
                        # CORREZIONE FINALE: 'data_pubblica' (senza "zione")
                        'data_pubblica': data_pubblica,
                        'pdf_url': ';;;'.join(pdf_urls) if pdf_urls else None
                    })
            else:
                data_pubblica = oggi.strftime("%Y-%m-%d %H:%M:%S")
                
                pdf_urls = []
                if link and link.endswith('.pdf'):
                    pdf_urls.append(link)
                
                all_circolari.append({
                    'titolo': titolo,
                    'contenuto': "",
                    # CORREZIONE FINALE: 'data_pubblica' (senza "zione")
                    'data_pubblica': data_pubblica,
                    'pdf_url': ';;;'.join(pdf_urls) if pdf_urls else None
                })
                
        except Exception as e:
            print(f"Errore processamento circolare: {e}")
            continue
    
    print(f"Trovate {len(all_circolari)} circolari (ultimi 30 giorni)")
    
    # CORREZIONE: Cerca 'data_pubblica'
    existing_response = supabase.table('circolari').select("titolo, data_pubblica").execute()
    
    nuove_circolari = []
    for circ in all_circolari:
        esiste = False
        for existing in existing_response.data:
            if existing['titolo'] == circ['titolo']:
                esiste = True
                break
        if not esiste:
            nuove_circolari.append(circ)
    
    if nuove_circolari:
        for circ in nuove_circolari:
            supabase.table('circolari').insert(circ).execute()
        print(f"Inserite {len(nuove_circolari)} nuove circolari")
    else:
        print("Nessuna nuova circolare trovata")
    
    # CORREZIONE: Usa 'data_pubblica'
    for existing in existing_response.data:
        try:
            if 'data_pubblica' in existing:
                data_existing = datetime.strptime(existing['data_pubblica'], "%Y-%m-%d %H:%M:%S")
                if data_existing < limite_30_giorni:
                    supabase.table('circolari').delete().eq('titolo', existing['titolo']).execute()
                    print(f"Eliminata circolare vecchia: {existing['titolo']}")
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
