import os
import time
from datetime import datetime
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
    page_num = 1
    
    while True:
        print(f"Scraping pagina {page_num}")
        
        circolari_elements = driver.find_elements(By.CSS_SELECTOR, ".circolare-item")
        
        if not circolari_elements:
            break
            
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
                    data_pubblicazione = f"{anno}-{mese}-{giorn} 00:00:00"
                else:
                    data_pubblicazione = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                pdf_urls = []
                if link and link.endswith('.pdf'):
                    pdf_urls.append(link)
                
                all_circolari.append({
                    'titolo': titolo,
                    'contenuto': "",
                    'data_pubblicazione': data_pubblicazione,
                    'pdf_url': ';;;'.join(pdf_urls) if pdf_urls else None
                })
                
            except Exception as e:
                print(f"Errore processamento circolare: {e}")
                continue
        
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, ".pagination .next")
            if "disabled" in next_button.get_attribute("class"):
                break
            next_button.click()
            time.sleep(3)
            page_num += 1
        except:
            break
    
    print(f"Trovate {len(all_circolari)} circolari")
    
    existing_response = supabase.table('circolari').select("titolo").execute()
    existing_titles = [item['titolo'] for item in existing_response.data] if existing_response.data else []
    
    nuove_circolari = []
    for circ in all_circolari:
        if circ['titolo'] not in existing_titles:
            nuove_circolari.append(circ)
    
    if nuove_circolari:
        for circ in nuove_circolari:
            supabase.table('circolari').insert(circ).execute()
        print(f"Inserite {len(nuove_circolari)} nuove circolari")
    else:
        print("Nessuna nuova circolare trovata")
    
    driver.quit()
    
except Exception as e:
    print(f"Errore durante lo scraping: {e}")
    driver.quit()

print("✅ Robot completato")
