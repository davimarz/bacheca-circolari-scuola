import os
import time
import glob
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from supabase import create_client
import urllib.parse
import re

print("🤖 Robot avviato")

# ==============================================================================
# 🛑 CONFIGURAZIONE DA VARIABILI D'AMBIENTE
# ==============================================================================
config = {
    'ARGO_USER': os.environ.get('ARGO_USER'),
    'ARGO_PASS': os.environ.get('ARGO_PASS'),
    'SUPABASE_URL': os.environ.get('SUPABASE_URL'),
    'SUPABASE_KEY': os.environ.get('SUPABASE_KEY')
}

# ==============================================================================

# --- PREPARAZIONE CARTELLA TEMPORANEA ---
cartella_download = os.path.join(os.getcwd(), "scaricati")
if not os.path.exists(cartella_download):
    os.makedirs(cartella_download)

# Pulizia iniziale
files = glob.glob(os.path.join(cartella_download, "*"))
for f in files:
    os.remove(f)

# --- CONFIGURAZIONE CHROME ---
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

# Configurazione download PDF
prefs = {
    "download.default_directory": cartella_download,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True
}
chrome_options.add_experimental_option("prefs", prefs)

# --- INIZIALIZZAZIONE SUPABASE ---
print("📡 Mi collego a Supabase...")
supabase = create_client(config['SUPABASE_URL'], config['SUPABASE_KEY'])

print("🤖 Avvio il browser...")
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 30)

def attendi_e_trova_file():
    """Attende il download del file e restituisce il percorso"""
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

def estrai_data_dal_testo(testo):
    """Estrae la data di pubblicazione dal testo della circolare"""
    if not testo:
        return None
    
    # Cerca diversi pattern di data nel testo
    pattern_data = [
        # Pattern più comune: "Data: 25/10/2024" o "Data 25/10/2024"
        r'Data\s*[:\-]?\s*(\d{2})/(\d{2})/(\d{4})',
        
        # "Pubblicato il 25/10/2024"
        r'Pubblicato\s*(?:il)?\s*(\d{2})/(\d{2})/(\d{4})',
        
        # "Del 25/10/2024"
        r'Del\s*(\d{2})/(\d{2})/(\d{4})',
        
        # "In data 25/10/2024"
        r'In\s*data\s*(\d{2})/(\d{2})/(\d{4})',
        
        # Formato standard 25/10/2024 (cerca le prime occorrenze)
        r'(\d{2})/(\d{2})/(\d{4})',
    ]
    
    for pattern in pattern_data:
        match = re.search(pattern, testo, re.IGNORECASE)
        if match:
            try:
                giorno, mese, anno = map(int, match.groups())
                # Validazione base della data
                if 1 <= giorno <= 31 and 1 <= mese <= 12 and anno >= 2020:
                    return datetime(anno, mese, giorno)
            except:
                continue
    
    return None

def aggiorna_date_dal_contenuto():
    """Aggiorna le date di pubblicazione analizzando il contenuto delle circolari"""
    print("📅 Aggiorno le date di pubblicazione dal contenuto...")
    
    # Ottieni tutte le circolari dal database
    res = supabase.table('circolari').select("id, titolo, contenuto, data_pubblica").execute()
    
    if not res.data:
        print("   ✅ Nessuna circolare nel database.")
        return
    
    circolari_da_aggiornare = []
    
    for circolare in res.data:
        contenuto = circolare.get('contenuto', '')
        if not contenuto:
            continue
        
        # Estrai la data dal contenuto
        data_dal_contenuto = estrai_data_dal_testo(contenuto)
        
        if data_dal_contenuto:
            # Formatta la data per il database
            nuova_data = data_dal_contenuto.strftime("%Y-%m-%d %H:%M:%S")
            data_attuale = circolare.get('data_pubblica', '')
            
            # Se la data è diversa da quella attuale, aggiorna
            if nuova_data != data_attuale:
                circolari_da_aggiornare.append({
                    'id': circolare['id'],
                    'titolo': circolare['titolo'],
                    'nuova_data': nuova_data,
                    'vecchia_data': data_attuale
                })
    
    # Aggiorna le circolari con le nuove date
    if circolari_da_aggiornare:
        print(f"   🔄 Trovate {len(circolari_da_aggiornare)} circolari con date da aggiornare")
        
        for circ in circolari_da_aggiornare:
            try:
                supabase.table('circolari').update({
                    'data_pubblica': circ['nuova_data']
                }).eq('id', circ['id']).execute()
                
                print(f"      ✅ '{circ['titolo'][:50]}...'")
                print(f"         Da: {circ['vecchia_data'][:10] if circ['vecchia_data'] else 'Nessuna'}")
                print(f"         A:  {circ['nuova_data'][:10]}")
            except Exception as e:
                print(f"      ⚠️  Errore aggiornamento {circ['titolo'][:50]}...: {e}")
    else:
        print("   ✅ Tutte le date sono già aggiornate.")

def rimuovi_circolari_vecchie():
    """Rimuove dal database le circolari più vecchie di 30 giorni BASANDOSI SUL CONTENUTO"""
    print("🧹 Controllo circolari vecchie (basato sul contenuto)...")
    
    # Ottieni tutte le circolari
    res = supabase.table('circolari').select("id, titolo, contenuto, pdf_url").execute()
    
    if not res.data:
        print("   ✅ Nessuna circolare nel database.")
        return
    
    circolari_vecchie = []
    
    for circolare in res.data:
        contenuto = circolare.get('contenuto', '')
        if not contenuto:
            continue
        
        # Estrai la data dal contenuto
        data_circolare = estrai_data_dal_testo(contenuto)
        
        if data_circolare:
            # Calcola quanti giorni sono passati
            giorni_passati = (datetime.now() - data_circolare).days
            
            if giorni_passati > 30:
                circolari_vecchie.append({
                    'id': circolare['id'],
                    'titolo': circolare['titolo'],
                    'data': data_circolare.strftime("%d/%m/%Y"),
                    'giorni': giorni_passati,
                    'pdf_url': circolare.get('pdf_url', '')
                })
    
    if not circolari_vecchie:
        print("   ✅ Nessuna circolare vecchia (>30gg) da eliminare.")
        return
    
    print(f"   🗑️  Trovate {len(circolari_vecchie)} circolari vecchie (>30gg) da eliminare...")
    
    for circ in circolari_vecchie:
        # Elimina i file dallo storage se presenti
        pdf_url = circ['pdf_url']
        if pdf_url:
            try:
                # Estrai i nomi dei file dagli URL
                urls = pdf_url.split(';;;')
                for url in urls:
                    if url.strip():
                        # Estrai il nome del file dall'URL
                        filename = url.split('/')[-1]
                        if filename:
                            try:
                                # Elimina dal bucket 'documenti'
                                supabase.storage.from_("documenti").remove([filename])
                                print(f"      📄 Rimosso file: {filename}")
                            except Exception as e:
                                print(f"      ⚠️  Errore rimozione file {filename}: {e}")
            except Exception as e:
                print(f"      ⚠️  Errore elaborazione URL: {e}")
        
        # Elimina la circolare dal database
        try:
            supabase.table('circolari').delete().eq('id', circ['id']).execute()
            print(f"      ✅ Rimossa: {circ['titolo'][:50]}... ({circ['data']}, {circ['giorni']} giorni)")
        except Exception as e:
            print(f"      ⚠️  Errore eliminazione circolare {circ['titolo']}: {e}")
    
    print(f"   🎉 Pulizia completata.")

try:
    # --- PRIMA AGGIORNA LE DATE DAL CONTENUTO ---
    aggiorna_date_dal_contenuto()
    
    # --- POI RIMUOVI LE CIRCOLARI VECCHIE ---
    rimuovi_circolari_vecchie()
    
    # --- LOGIN ---
    print("🌍 Login...")
    driver.get("https://www.portaleargo.it/famiglia")
    
    # Attendi e compila i campi di login
    wait.until(EC.presence_of_element_located((By.ID, "username")))
    username = driver.find_element(By.ID, "username")
    password = driver.find_element(By.ID, "password")
    
    username.send_keys(config['ARGO_USER'])
    password.send_keys(config['ARGO_PASS'])
    
    login_button = driver.find_element(By.ID, "login-button")
    login_button.click()
    
    print("⏳ Attendo Dashboard...")
    time.sleep(5)
    
    # --- NAVIGAZIONE ALLA BACHECA CIRCOLARI ---
    print("👉 Vado alle Circolari...")
    try:
        # Prima prova con il link "Circolari"
        circolari_link = wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Circolari"))
        )
        circolari_link.click()
    except:
        # Se non trova "Circolari", prova con "Bacheca"
        try:
            bacheca_link = driver.find_element(By.XPATH, "//*[contains(text(), 'Bacheca')]")
            bacheca_link.click()
            time.sleep(2)
            # Cerca "Circolari" o "Messaggi" nella sottopagina
            try:
                circ_sub = driver.find_element(By.XPATH, "//*[contains(text(), 'Circolari')]")
                circ_sub.click()
            except:
                try:
                    mess_sub = driver.find_element(By.XPATH, "//*[contains(text(), 'Messaggi')]")
                    mess_sub.click()
                except:
                    pass
        except:
            print("⚠️ Non riesco a trovare il link delle circolari")
            raise
    
    print("⏳ Caricamento pagina circolari...")
    time.sleep(8)
    
    # --- DEBUG: SALVA SCREENSHOT E HTML PER VEDERE LA STRUTTURA ---
    print("📸 Faccio screenshot per debug...")
    driver.save_screenshot("debug_circolari.png")
    print("✅ Screenshot salvato come debug_circolari.png")
    
    # Salva anche l'HTML per analisi
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("✅ HTML salvato come debug_page.html")
    
    # --- CERCA GLI ELEMENTI DELLE CIRCOLARI IN MODO PIÙ FLESSIBILE ---
    print("🔍 Cerco le circolari...")
    
    # Prova diversi approcci per trovare le circolari
    circolari_trovate = []
    
    # APPROCCIO 1: Cerca per testo "CIRCOLARE N."
    try:
        elementi_circolare = driver.find_elements(By.XPATH, "//*[contains(text(), 'CIRCOLARE N.') or contains(text(), 'Circolare n.')]")
        print(f"✅ Trovati {len(elementi_circolare)} elementi con 'CIRCOLARE N.'")
        
        for elem in elementi_circolare:
            # Prendi l'elemento genitore più probabile
            try:
                parent = elem.find_element(By.XPATH, "./ancestor::tr[1]")
                if parent not in circolari_trovate:
                    circolari_trovate.append(parent)
            except:
                try:
                    parent = elem.find_element(By.XPATH, "./ancestor::div[1]")
                    if parent not in circolari_trovate:
                        circolari_trovate.append(parent)
                except:
                    if elem not in circolari_trovate:
                        circolari_trovate.append(elem)
    except Exception as e:
        print(f"⚠️ Errore ricerca per testo: {e}")
    
    # APPROCCIO 2: Cerca tutte le righe di tabella
    try:
        righe_tabella = driver.find_elements(By.TAG_NAME, "tr")
        print(f"✅ Trovate {len(righe_tabella)} righe di tabella")
        
        # Filtra le righe che sembrano circolari (hanno testo significativo)
        for riga in righe_tabella:
            testo = riga.text.strip()
            if testo and len(testo) > 50:  # Testo lungo = probabile circolare
                if riga not in circolari_trovate:
                    circolari_trovate.append(riga)
    except Exception as e:
        print(f"⚠️ Errore ricerca righe tabella: {e}")
    
    # APPROCCIO 3: Cerca elementi con classi comuni
    class_selectors = [
        ".x-grid-row",
        ".list-item",
        ".item",
        ".row",
        ".circolare-item",
        ".messaggio-item"
    ]
    
    for selector in class_selectors:
        try:
            elementi = driver.find_elements(By.CSS_SELECTOR, selector)
            if elementi:
                print(f"✅ Trovati {len(elementi)} elementi con selettore: {selector}")
                for elem in elementi:
                    if elem not in circolari_trovate:
                        circolari_trovate.append(elem)
        except:
            continue
    
    # APPROCCIO 4: Cerca per date (pattern DD/MM/YYYY)
    try:
        elementi_data = driver.find_elements(By.XPATH, "//*[contains(text(), '/202')]")
        print(f"✅ Trovati {len(elementi_data)} elementi con date")
        
        for elem in elementi_data:
            try:
                parent = elem.find_element(By.XPATH, "./ancestor::tr[1]")
                if parent not in circolari_trovate:
                    circolari_trovate.append(parent)
            except:
                continue
    except Exception as e:
        print(f"⚠️ Errore ricerca per date: {e}")
    
    numero_totale = len(circolari_trovate)
    print(f"\n🎯 TOTALE CIRCOLARI TROVATE: {numero_totale}")
    
    if numero_totale == 0:
        print("❌ Nessuna circolare trovata. Controlla gli screenshot di debug.")
        print("   File creati: debug_circolari.png e debug_page.html")
        exit(1)
    
    # Stampa anteprima delle prime 5 circolari
    print("\n📋 Anteprima prime 5 circolari:")
    for i, circ in enumerate(circolari_trovate[:5]):
        print(f"  {i+1}. {circ.text[:100]}...")
    
    # --- CICLO PER OGNI CIRCOLARE ---
    circolari_elaborate = 0
    
    for i, circolare_elem in enumerate(circolari_trovate):
        try:
            print(f"\n{'='*60}")
            print(f"🔄 [{i+1}/{numero_totale}] Elaboro circolare...")
            
            # Estrai il testo della circolare
            testo_circolare = circolare_elem.text.strip()
            if not testo_circolare or len(testo_circolare) < 20:
                print("   ⚠️  Testo troppo corto, salto")
                continue
            
            print(f"   📄 Testo (primi 150 caratteri):")
            print(f"      {testo_circolare[:150]}...")
            
            # Estrai il titolo (prima riga o parte significativa)
            titolo = ""
            lines = testo_circolare.split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 10:
                    titolo = line[:200]  # Limita la lunghezza
                    break
            
            if not titolo:
                titolo = testo_circolare[:100]
            
            print(f"   📌 Titolo estratto: {titolo[:80]}...")
            
            # Ora clicca sulla circolare per vedere il contenuto completo
            try:
                print("   🔍 Apro circolare per estrarre contenuto completo...")
                
                # Prova a cliccare sull'elemento
                circolare_elem.click()
                time.sleep(4)
                
                # Estrai il contenuto completo
                contenuto_completo = ""
                
                # Prova diversi selettori per il contenuto
                contenuto_selectors = [
                    "body",
                    ".x-panel-body",
                    ".content",
                    ".contenuto",
                    ".testo",
                    "#content",
                    "div[class*='contenuto']",
                    "div[class*='messaggio']"
                ]
                
                for selector in contenuto_selectors:
                    try:
                        elemento = driver.find_element(By.CSS_SELECTOR, selector)
                        testo = elemento.text.strip()
                        if testo and len(testo) > len(contenuto_completo):
                            contenuto_completo = testo
                    except:
                        continue
                
                # Se il contenuto è troppo corto, prova a prendere tutto il body
                if len(contenuto_completo) < 100:
                    try:
                        body = driver.find_element(By.TAG_NAME, "body")
                        contenuto_completo = body.text.strip()
                    except:
                        pass
                
                if contenuto_completo:
                    print(f"   ✅ Contenuto estratto ({len(contenuto_completo)} caratteri)")
                    
                    # Estrai la data dal contenuto
                    data_pubblicazione = estrai_data_dal_testo(contenuto_completo)
                    
                    if data_pubblicazione:
                        print(f"   📅 Data estratta dal contenuto: {data_pubblicazione.strftime('%d/%m/%Y')}")
                    else:
                        print("   ⚠️  Data non trovata nel contenuto")
                        # Prova a cercare nel testo originale
                        data_pubblicazione = estrai_data_dal_testo(testo_circolare)
                        if data_pubblicazione:
                            print(f"   📅 Data estratta dal titolo: {data_pubblicazione.strftime('%d/%m/%Y')}")
                else:
                    print("   ⚠️  Contenuto non estratto")
                    contenuto_completo = testo_circolare
                    data_pubblicazione = estrai_data_dal_testo(testo_circolare)
                    if data_pubblicazione:
                        print(f"   📅 Data estratta dal titolo: {data_pubblicazione.strftime('%d/%m/%Y')}")
                
                # Torna indietro
                driver.back()
                time.sleep(3)
                
            except Exception as e:
                print(f"   ⚠️  Errore apertura circolare: {e}")
                # Usa il testo che abbiamo già
                contenuto_completo = testo_circolare
                data_pubblicazione = estrai_data_dal_testo(testo_circolare)
                if data_pubblicazione:
                    print(f"   📅 Data estratta: {data_pubblicazione.strftime('%d/%m/%Y')}")
            
            # ===> FILTRO 30 GIORNI <===
            if not data_pubblicazione:
                print("   ⚠️  Data non estratta, salto questa circolare")
                continue
            
            giorni_passati = (datetime.now() - data_pubblicazione).days
            
            if giorni_passati > 30:
                print(f"⏹️  INCONTRATA CIRCOLARE VECCHIA: {data_pubblicazione.strftime('%d/%m/%Y')} ({giorni_passati} giorni)")
                print(f"🛑 Fermo lo scaricamento. Elaborate {circolari_elaborate} circolari recenti.")
                break
            
            print(f"   ✅ Circolare recente ({giorni_passati} giorni fa)")
            circolari_elaborate += 1
            
            # CERCA ALLEGATI (semplificato per ora)
            print("   🔍 Cerco allegati...")
            # Qui puoi aggiungere la logica per cercare allegati nell'elemento
            
            # SALVATAGGIO NEL DATABASE
            try:
                # Formatta la data per il database
                data_pubblica_db = data_pubblicazione.strftime("%Y-%m-%d %H:%M:%S")
                
                # Controlla se la circolare esiste già
                res = supabase.table('circolari').select("*").eq('titolo', titolo).eq('data_pubblica', data_pubblica_db).execute()
                
                if not res.data:
                    # Inserisci nuova circolare
                    supabase.table('circolari').insert({
                        "titolo": titolo,
                        "contenuto": contenuto_completo,
                        "data_pubblica": data_pubblica_db,
                        "pdf_url": ""  # Per ora vuoto, puoi aggiungere la logica allegati
                    }).execute()
                    print("   ✅ Circolare salvata nel database.")
                else:
                    print("   💤 Circolare già presente nel database.")
                    
            except Exception as e:
                print(f"   ⚠️  Errore salvataggio database: {e}")
                
        except Exception as e:
            print(f"⚠️ Errore elaborazione circolare {i+1}: {e}")
            continue
    
    print(f"\n{'='*60}")
    print(f"🎉 ELABORAZIONE COMPLETATA")
    print(f"   • Circolari trovate: {numero_totale}")
    print(f"   • Circolari recenti elaborate: {circolari_elaborate}")
    print(f"   • Circolari vecchie scartate: {max(0, numero_totale - circolari_elaborate)}")
    
    # AGGIORNA NUOVAMENTE LE DATE PER VERIFICA FINALE
    print("\n🔄 Verifica finale date dal contenuto...")
    aggiorna_date_dal_contenuto()

except Exception as e:
    print(f"\n❌ ERRORE CRITICO: {e}")
    import traceback
    traceback.print_exc()

finally:
    # --- PULIZIA FINALE ---
    print("\n🧹 Pulizia file temporanei...")
    files = glob.glob(os.path.join(cartella_download, "*"))
    for f in files:
        try:
            os.remove(f)
        except:
        pass
    
    # Rimuovi la cartella se è vuota
    try:
        if not os.listdir(cartella_download):
            os.rmdir(cartella_download)
    except:
        pass
    
    print("🔒 Chiusura browser...")
    try:
        driver.quit()
    except:
        pass

print("✅ Robot completato!")
