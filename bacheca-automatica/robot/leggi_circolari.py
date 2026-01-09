import time
import os
import glob
import requests 
from datetime import datetime, timedelta # <--- Importiamo timedelta per calcolare i giorni
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from supabase import create_client

# ==============================================================================
# 🛑 CONFIGURAZIONE
# ==============================================================================
ARGO_USER = "davide.marziano.sc26953"
ARGO_PASS = "dvd2Frank." 

SUPABASE_URL = "https://ojnofjebrlwrlowovvjd.supabase.co" 
SUPABASE_KEY = "sb_publishable_uXCA_4jkxA2qSB7Mik3j1A_uo7b6eLq"
# ==============================================================================

# --- PREPARAZIONE CARTELLA TEMPORANEA ---
cartella_download = os.path.join(os.getcwd(), "scaricati")
if not os.path.exists(cartella_download):
    os.makedirs(cartella_download)

# Pulizia iniziale
files = glob.glob(os.path.join(cartella_download, "*"))
for f in files: os.remove(f)

# --- CONFIGURAZIONE CHROME ---
chrome_options = Options()
prefs = {
    "download.default_directory": cartella_download,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True
}
chrome_options.add_experimental_option("prefs", prefs)

print("📡 Mi collego a Supabase...")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🤖 Avvio il browser...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
wait = WebDriverWait(driver, 30)
driver.maximize_window()

def attendi_e_trova_file():
    tempo_max = 20
    timer = 0
    while timer < tempo_max:
        files = glob.glob(os.path.join(cartella_download, "*.*"))
        files_completi = [f for f in files if not f.endswith('.crdownload') and not f.endswith('.tmp')]
        if files_completi:
            return max(files_completi, key=os.path.getctime)
        time.sleep(1)
        timer += 1
    return None

try:
    # --- LOGIN ---
    print("🌍 Login...")
    driver.get("https://www.portaleargo.it/voti/?classic") 
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']")))
    driver.find_element(By.CSS_SELECTOR, "input[type='text']").send_keys(ARGO_USER)
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(ARGO_PASS)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    
    print("⏳ Attendo Dashboard...")
    time.sleep(15) 

    # --- APERTURA ---
    print("👉 Vado ai Messaggi...")
    driver.get("https://www.portaleargo.it/voti/?classic")
    time.sleep(5)
    
    driver.find_element(By.XPATH, "//*[contains(text(), 'Bacheca')]").click()
    time.sleep(2)
    try:
        sub = driver.find_element(By.XPATH, "//*[contains(text(), 'Messaggi da leggere')]")
        driver.execute_script("arguments[0].click();", sub)
    except:
        try:
            sub = driver.find_element(By.XPATH, "//*[contains(text(), 'Gestione Bacheca')]")
            driver.execute_script("arguments[0].click();", sub)
        except: pass

    print("⏳ Caricamento tabella...")
    time.sleep(8)

    # --- CICLO ---
    righe_iniziali = driver.find_elements(By.CLASS_NAME, "x-grid-row")
    numero_totale = len(righe_iniziali)
    print(f"✅ Trovate {numero_totale} circolari totali.")

    for i in range(numero_totale):
        
        # 1. RECUPERO DATI
        try:
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "x-grid-row")))
            time.sleep(1)
            righe_fresche = driver.find_elements(By.CLASS_NAME, "x-grid-row")
            if i >= len(righe_fresche): break
            riga_corrente = righe_fresche[i]
            colonne = riga_corrente.find_elements(By.TAG_NAME, "td")
        except:
            driver.refresh()
            time.sleep(10)
            continue

        if len(colonne) < 5: continue
        
        data_str = colonne[0].text # Es: 05/01/2026
        categoria = colonne[1].text
        titolo = colonne[3].text.replace("\n", " ").strip()
        cella_file = colonne[4]

        # ===> FILTRO 30 GIORNI <===
        try:
            # Convertiamo la scritta "05/01/2026" in una data vera
            data_circolare = datetime.strptime(data_str, "%d/%m/%Y")
            
            # Calcoliamo quanti giorni sono passati
            giorni_passati = (datetime.now() - data_circolare).days
            
            if giorni_passati > 30:
                print(f"⏩ Salto circolare del {data_str} (Vecchia di {giorni_passati} giorni)")
                continue # PASSA ALLA PROSSIMA, NON FARE NULLA
            
            print(f"\n🔄 Elaboro recente: {data_str} - {titolo[:30]}...")

        except Exception as e:
            print(f"⚠️ Errore data ({data_str}), provo a elaborare comunque...")

        # SE SIAMO QUI, LA CIRCOLARE È RECENTE -> PROCEDIAMO
        
        ha_allegati = False
        if cella_file.text.strip() != "" or len(cella_file.find_elements(By.TAG_NAME, "div")) > 0:
            ha_allegati = True

        public_links_string = ""

        if ha_allegati:
            print("   📎 Scarico allegati...")
            try:
                cella_file.click()
                try: cella_file.find_element(By.TAG_NAME, "div").click()
                except: pass
                
                time.sleep(4) 
                links_pdf_argo = driver.find_elements(By.PARTIAL_LINK_TEXT, ".pdf")
                lista_url_pubblici = []

                for index_file, link in enumerate(links_pdf_argo):
                    print(f"      ⬇️ Download {index_file+1}...")
                    link.click()
                    file_scaricato = attendi_e_trova_file()
                    
                    if file_scaricato:
                        # Carica su Supabase
                        nome_semplice = f"allegato_{index_file + 1}.pdf"
                        nome_unico = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{nome_semplice}"
                        
                        with open(file_scaricato, "rb") as f:
                            print("      ⬆️ Upload Cloud...")
                            supabase.storage.from_("documenti").upload(
                                path=nome_unico,
                                file=f,
                                file_options={"content-type": "application/pdf"}
                            )
                        
                        url_pubblico = supabase.storage.from_("documenti").get_public_url(nome_unico)
                        lista_url_pubblici.append(url_pubblico)
                        
                        # CANCELLA DAL PC (Pulizia immediata)
                        f.close()
                        os.remove(file_scaricato)

                public_links_string = ";;;".join(lista_url_pubblici)

                # RITORNO
                print("   🔙 Torno indietro...")
                menu_bacheca = driver.find_element(By.XPATH, "//*[contains(text(), 'Bacheca')]")
                driver.execute_script("arguments[0].click();", menu_bacheca)
                time.sleep(2)
                try:
                    sub = driver.find_element(By.XPATH, "//*[contains(text(), 'Messaggi da leggere')]")
                    driver.execute_script("arguments[0].click();", sub)
                except:
                    sub = driver.find_element(By.XPATH, "//*[contains(text(), 'Gestione Bacheca')]")
                    driver.execute_script("arguments[0].click();", sub)
                time.sleep(5) 
                wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "x-grid-row")))

            except Exception as e:
                print(f"   ⚠️ Errore allegati: {e}")
                driver.get("https://www.portaleargo.it/voti/?classic")
                time.sleep(5)
                continue

        # SALVATAGGIO
        res = supabase.table('circolari').select("*").eq('titolo', titolo).execute()
        if not res.data:
            supabase.table('circolari').insert({
                "titolo": titolo,
                "contenuto": f"Categoria: {categoria} - Data: {data_str}",
                "data_pubblicazione": datetime.now().isoformat(),
                "pdf_url": public_links_string
            }).execute()
            print("   ✅ Salvata.")
        else:
            if public_links_string:
                supabase.table('circolari').update({"pdf_url": public_links_string}).eq('titolo', titolo).execute()
                print("   🔄 Aggiornata.")
            else:
                print("   💤 Già presente.")

except Exception as e:
    print(f"❌ CRASH: {e}")

finally:
    print("Chiusura...")
    driver.quit()
