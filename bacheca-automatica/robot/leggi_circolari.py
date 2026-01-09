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
    
    print("⏳ Caricamento tabella circolari...")
    time.sleep(8)
    
    # --- CERCA LA TABELLA DELLE CIRCOLARI ---
    print("🔍 Cerco la tabella delle circolari...")
    
    # Prova diversi selettori per la tabella
    table_selectors = [
        "table",
        ".x-grid-table",
        ".table",
        "#gridview",
        "[role='grid']"
    ]
    
    tabella = None
    for selector in table_selectors:
        try:
            tabella = driver.find_element(By.CSS_SELECTOR, selector)
            print(f"✅ Trovata tabella con selettor e: {selector}")
            break
        except:
            continue
    
    if not tabella:
        print("⚠️ Non trovo la tabella, cerco righe direttamente")
    
    # --- TROVA TUTTE LE RIGHE DELLA TABELLA ---
    righe = []
    
    if tabella:
        # Trova tutte le righe della tabella
        righe = tabella.find_elements(By.CSS_SELECTOR, "tr")
        # Rimuovi l'header se presente (prima riga)
        if righe and ("DATA" in righe[0].text or "DATA" in righe[0].get_attribute('innerHTML')):
            righe = righe[1:]
    else:
        # Se non trova tabella, cerca direttamente le righe
        righe = driver.find_elements(By.CSS_SELECTOR, "tr, .x-grid-row, .list-item")
    
    numero_totale = len(righe)
    print(f"✅ Trovate {numero_totale} circolari.")
    
    # --- CICLO PER OGNI CIRCOLARE ---
    circolari_elaborate = 0
    
    for i in range(numero_totale):
        try:
            # Ricarica le righe per evitare elementi stantii
            if tabella:
                righe_fresche = tabella.find_elements(By.CSS_SELECTOR, "tr")
                if righe_fresche and ("DATA" in righe_fresche[0].text):
                    righe_fresche = righe_fresche[1:]
            else:
                righe_fresche = driver.find_elements(By.CSS_SELECTOR, "tr, .x-grid-row, .list-item")
            
            if i >= len(righe_fresche):
                break
                
            riga_corrente = righe_fresche[i]
            
            # ESTRAI LE COLONNE DELLA RIGA
            colonne = riga_corrente.find_elements(By.TAG_NAME, "td")
            
            # Se non trova td, prova con altri elementi
            if not colonne:
                colonne = riga_corrente.find_elements(By.CSS_SELECTOR, "div, span")
            
            # Se non ci sono abbastanza colonne, salta
            if len(colonne) < 5:
                print(f"⚠️ Riga {i+1}: Troppo poche colonne ({len(colonne)}), salto")
                continue
            
            # COLONNA 3: TITOLO DELLA CIRCOLARE (es: "CIRCOLARE N.160 OGGETTO: ...")
            titolo = colonne[3].text.strip()
            
            # COLONNA 4: FILE/ALLEGATI
            cella_file = colonne[4]
            
            print(f"\n🔄 [{i+1}] Apro circolare: {titolo[:80]}...")
            
            # VARIABILI PER I DATI DA ESTRARRE
            contenuto_completo = ""
            data_pubblicazione = None
            
            # CLICCA SULLA CIRCOLARE PER VEDERE IL CONTENUTO COMPLETO
            try:
                # Salva URL corrente per poter tornare
                url_lista = driver.current_url
                
                # Clicca sulla circolare per aprirla (colonna del titolo)
                colonne[3].click()
                time.sleep(4)
                
                # Estrai il CONTENUTO COMPLETO della circolare
                contenuto_selectors = [
                    ".circolare-contenuto",
                    ".contenuto",
                    ".messaggio-contenuto",
                    ".content",
                    ".body",
                    ".testo",
                    "div[class*='contenuto']",
                    "div[class*='messaggio']",
                    ".x-panel-body",
                    "#content",
                    "div.x-grid-item-container"
                ]
                
                for selector in contenuto_selectors:
                    try:
                        elemento = driver.find_element(By.CSS_SELECTOR, selector)
                        contenuto_completo = elemento.text
                        if contenuto_completo and len(contenuto_completo) > 100:
                            print(f"   ✅ Contenuto estratto con selettore: {selector}")
                            break
                    except:
                        continue
                
                # Se non trova selettori specifici, prova con tutto il body
                if not contenuto_completo or len(contenuto_completo) < 100:
                    try:
                        body = driver.find_element(By.TAG_NAME, "body")
                        contenuto_completo = body.text
                        print("   ✅ Contenuto estratto dal body")
                    except:
                        print("   ⚠️  Non riesco ad estrarre il contenuto")
                
                # ORA ESTRAI LA DATA DI PUBBLICAZIONE DAL CONTENUTO
                if contenuto_completo:
                    data_pubblicazione = estrai_data_dal_testo(contenuto_completo)
                    
                    if data_pubblicazione:
                        print(f"   📅 Data pubblicazione estratta dal contenuto: {data_pubblicazione.strftime('%d/%m/%Y')}")
                    else:
                        print("   ⚠️  Data non trovata nel contenuto")
                else:
                    print("   ⚠️  Nessun contenuto da analizzare")
                
                # Torna indietro alla lista
                driver.get(url_lista)
                time.sleep(4)
                
                # Ricarica la tabella
                if tabella:
                    tabella = driver.find_element(By.CSS_SELECTOR, table_selectors[0])
                    righe_fresche = tabella.find_elements(By.CSS_SELECTOR, "tr")
                    if righe_fresche and ("DATA" in righe_fresche[0].text):
                        righe_fresche = righe_fresche[1:]
                
            except Exception as e:
                print(f"   ❌ Errore apertura circolare: {e}")
                # Se c'è errore, ricarica la pagina
                driver.get(driver.current_url)
                time.sleep(5)
                continue
            
            # ===> FILTRO 30 GIORNI (USANDO LA DATA ESTRATTA DAL CONTENUTO) <===
            if not data_pubblicazione:
                print("   ⚠️  Data non estratta, salto questa circolare")
                continue
            
            giorni_passati = (datetime.now() - data_pubblicazione).days
            
            if giorni_passati > 30:
                print(f"⏹️  INCONTRATA CIRCOLARE VECCHIA: {data_pubblicazione.strftime('%d/%m/%Y')} (Vecchia di {giorni_passati} giorni)")
                print(f"🛑 Fermo lo scaricamento. Ho elaborato {circolari_elaborate} circolari recenti.")
                # Esci completamente dal ciclo
                break
            
            # SE SIAMO QUI, LA CIRCOLARE È RECENTE (<30 giorni) -> PROCEDIAMO
            circolari_elaborate += 1
            
            print(f"   ✅ Circolare recente ({giorni_passati} giorni)")
            
            # CONTROLLA SE CI SONO ALLEGATI
            ha_allegati = False
            public_links_string = ""
            
            # Controlla se la cella file ha contenuto
            if (cella_file.text.strip() != "" or 
                len(cella_file.find_elements(By.TAG_NAME, "div")) > 0 or
                len(cella_file.find_elements(By.TAG_NAME, "a")) > 0 or
                len(cella_file.find_elements(By.TAG_NAME, "img")) > 0):
                ha_allegati = True
            
            # GESTIONE ALLEGATI
            if ha_allegati:
                print("   📎 Scarico allegati...")
                try:
                    # Salva l'URL corrente per poter tornare indietro
                    url_corrente = driver.current_url
                    
                    # Clicca sulla cella degli allegati
                    cella_file.click()
                    time.sleep(3)
                    
                    # Cerca link PDF nella pagina corrente
                    links_pdf = driver.find_elements(By.PARTIAL_LINK_TEXT, ".pdf")
                    if not links_pdf:
                        # Prova con altri selettori per PDF
                        links_pdf = driver.find_elements(By.CSS_SELECTOR, 
                            "a[href$='.pdf'], " +
                            "a[href*='download'], " +
                            "a[href*='allegato'], " +
                            "a[href*='file'], " +
                            "a[href*='document']"
                        )
                    
                    lista_url_pubblici = []
                    
                    for index_file, link in enumerate(links_pdf):
                        try:
                            print(f"      ⬇️ Download allegato {index_file+1}...")
                            
                            # Clicca sul link per avviare il download
                            link.click()
                            time.sleep(2)
                            
                            # Attendi il download
                            file_scaricato = attendi_e_trova_file()
                            
                            if file_scaricato:
                                # Carica su Supabase Storage
                                nome_semplice = f"circolare_{data_pubblicazione.strftime('%Y%m%d')}_{index_file + 1}.pdf"
                                nome_unico = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{nome_semplice}"
                                
                                with open(file_scaricato, "rb") as f:
                                    print("      ⬆️ Upload su Cloud...")
                                    supabase.storage.from_("documenti").upload(
                                        path=nome_unico,
                                        file=f,
                                        file_options={"content-type": "application/pdf"}
                                    )
                                
                                # Ottieni URL pubblico
                                url_pubblico = supabase.storage.from_("documenti").get_public_url(nome_unico)
                                lista_url_pubblici.append(url_pubblico)
                                
                                # Chiudi il file e rimuovilo dal disco
                                f.close()
                                os.remove(file_scaricato)
                                print(f"      ✅ Allegato {index_file+1} caricato: {nome_unico}")
                        except Exception as e:
                            print(f"      ⚠️ Errore download allegato {index_file+1}: {e}")
                            continue
                    
                    public_links_string = ";;;".join(lista_url_pubblici)
                    
                    # TORNA ALLA LISTA DELLE CIRCOLARI
                    print("   🔙 Torno alla lista delle circolari...")
                    driver.get(url_corrente)
                    time.sleep(5)
                    
                except Exception as e:
                    print(f"   ⚠️ Errore nella gestione allegati: {e}")
                    # In caso di errore, torna alla lista
                    try:
                        driver.back()
                        time.sleep(3)
                    except:
                        pass
            
            # SALVATAGGIO NEL DATABASE (CON DATA ESTRATTA DAL CONTENUTO)
            try:
                # Formatta la data per il database
                data_pubblica_db = data_pubblicazione.strftime("%Y-%m-%d %H:%M:%S")
                
                # Crea il contenuto per il database
                if contenuto_completo:
                    contenuto_db = contenuto_completo
                else:
                    contenuto_db = f"Titolo: {titolo}\nData estratta dal contenuto: {data_pubblicazione.strftime('%d/%m/%Y')}"
                
                # Controlla se la circolare esiste già (per titolo e data)
                res = supabase.table('circolari').select("*").eq('titolo', titolo).eq('data_pubblica', data_pubblica_db).execute()
                
                if not res.data:
                    # Inserisci nuova circolare
                    supabase.table('circolari').insert({
                        "titolo": titolo,
                        "contenuto": contenuto_db,
                        "data_pubblica": data_pubblica_db,
                        "pdf_url": public_links_string
                    }).execute()
                    print("   ✅ Circolare salvata nel database.")
                    print(f"   📅 Data pubblicazione: {data_pubblica_db[:10]}")
                else:
                    # Aggiorna circolare esistente (solo allegati se nuovi)
                    if public_links_string and not res.data[0].get('pdf_url'):
                        supabase.table('circolari').update({"pdf_url": public_links_string}).eq('id', res.data[0]['id']).execute()
                        print("   🔄 Allegati aggiunti.")
                    else:
                        print("   💤 Circolare già presente nel database.")
                        
            except Exception as e:
                print(f"   ⚠️ Errore nel salvataggio database: {e}")
                
        except Exception as e:
            print(f"⚠️ Errore nell'elaborazione riga {i+1}: {e}")
            continue
    
    print(f"\n🎉 Elaborazione completata. Circolari recenti elaborate: {circolari_elaborate}")
    
    # RIEPILOGO FINALE
    print(f"\n📊 RIEPILOGO FINALE:")
    print(f"   • Circolari totali trovate in tabella: {numero_totale}")
    print(f"   • Circolari recenti (<30gg) elaborate: {circolari_elaborate}")
    print(f"   • Date estratte dal CONTENUTO delle circolari")
    
    # AGGIORNA NUOVAMENTE LE DATE PER VERIFICA FINALE
    print("\n🔄 Verifica finale date dal contenuto...")
    aggiorna_date_dal_contenuto()

except Exception as e:
    print(f"❌ ERRORE CRITICO: {e}")
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

print("✅ Robot completato con successo!")
