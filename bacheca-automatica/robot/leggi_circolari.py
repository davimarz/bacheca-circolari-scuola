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

def rimuovi_circolari_vecchie():
    """Rimuove dal database le circolari più vecchie di 30 giorni"""
    print("🧹 Controllo circolari vecchie...")
    
    # Calcola la data di 30 giorni fa
    data_limite = (datetime.now() - timedelta(days=30)).isoformat()
    
    # Trova tutte le circolari più vecchie di 30 giorni
    res = supabase.table('circolari').select("*").lt('data_pubblica', data_limite).execute()
    
    circolari_vecchie = res.data
    if not circolari_vecchie:
        print("   ✅ Nessuna circolare vecchia da eliminare.")
        return
    
    print(f"   🗑️  Trovate {len(circolari_vecchie)} circolari vecchie da eliminare...")
    
    for circolare in circolari_vecchie:
        titolo = circolare['titolo']
        pdf_url = circolare.get('pdf_url', '')
        
        # Elimina i file dallo storage se presenti
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
            supabase.table('circolari').delete().eq('id', circolare['id']).execute()
            print(f"      ✅ Rimossa circolare: {titolo[:50]}...")
        except Exception as e:
            print(f"      ⚠️  Errore eliminazione circolare {titolo}: {e}")
    
    print(f"   🎉 Pulizia completata.")

def estrai_data_da_testo(testo):
    """Estrae una data dal testo della circolare"""
    if not testo:
        return None
    
    # Cerca diversi formati di data
    pattern_data = [
        r'(\d{2})/(\d{2})/(\d{4})',  # 25/10/2024
        r'(\d{2})-(\d{2})-(\d{4})',  # 25-10-2024
        r'(\d{2})\.(\d{2})\.(\d{4})',  # 25.10.2024
        r'Data:\s*(\d{2})/(\d{2})/(\d{4})',  # Data: 25/10/2024
        r'Pubblicato\s*il\s*(\d{2})/(\d{2})/(\d{4})',  # Pubblicato il 25/10/2024
        r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})',  # 25 Ottobre 2024
    ]
    
    for pattern in pattern_data:
        match = re.search(pattern, testo, re.IGNORECASE)
        if match:
            try:
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
                        giorno, mese, anno = int(g1), int(g2), int(g3)
                        return datetime(anno, mese, giorno)
            except:
                continue
    
    return None

try:
    # --- PULIZIA INIZIALE DELLE CIRCOLARI VECCHIE ---
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
    
    # --- TROVA TUTTE LE RIGHE DELLE CIRCOLARI ---
    try:
        # Prova diversi selettori per trovare le righe
        righe = driver.find_elements(By.CLASS_NAME, "x-grid-row")
        if not righe:
            # Prova altri selettori comuni
            righe = driver.find_elements(By.CSS_SELECTOR, "tr, .list-item, .item, .row, .circolare-item")
        
        numero_totale = len(righe)
        print(f"✅ Trovate {numero_totale} circolari totali.")
        
    except Exception as e:
        print(f"⚠️ Errore nel trovare le righe: {e}")
        numero_totale = 0
        righe = []
    
    # --- CICLO PER OGNI CIRCOLARE ---
    circolari_elaborate = 0
    
    for i in range(numero_totale):
        
        # 1. RECUPERO DATI DELLA RIGA
        try:
            # Ricarica le righe per evitare elementi stantii
            righe_fresche = driver.find_elements(By.CLASS_NAME, "x-grid-row")
            if not righe_fresche:
                righe_fresche = driver.find_elements(By.CSS_SELECTOR, "tr, .list-item, .item, .row, .circolare-item")
            
            if i >= len(righe_fresche):
                break
                
            riga_corrente = righe_fresche[i]
            
            # Prova a cliccare sulla riga per vedere i dettagli completi
            try:
                riga_corrente.click()
                time.sleep(2)
                
                # Ora estrai il testo completo della circolare
                # Cerca il contenuto della circolare
                try:
                    # Prova diversi selettori per il contenuto
                    contenuto_selectors = [
                        ".circolare-contenuto",
                        ".contenuto-circolare",
                        ".messaggio-contenuto",
                        ".content",
                        ".body",
                        ".testo",
                        "div[class*='contenuto']",
                        "div[class*='messaggio']",
                        "div[class*='testo']"
                    ]
                    
                    contenuto_testo = ""
                    for selector in contenuto_selectors:
                        try:
                            elemento = driver.find_element(By.CSS_SELECTOR, selector)
                            contenuto_testo = elemento.text
                            if contenuto_testo:
                                break
                        except:
                            continue
                    
                    # Se non trovato, prova con selettori più generici
                    if not contenuto_testo:
                        try:
                            # Prendi tutto il testo della pagina dopo aver cliccato
                            body = driver.find_element(By.TAG_NAME, "body")
                            contenuto_testo = body.text
                        except:
                            pass
                    
                    # Estrai la data dal contenuto
                    data_circolare = estrai_data_da_testo(contenuto_testo)
                    
                    # Estrai titolo
                    titolo_selectors = [
                        ".circolare-titolo",
                        ".titolo-circolare",
                        ".messaggio-titolo",
                        "h1", "h2", "h3",
                        ".title",
                        ".subject"
                    ]
                    
                    titolo = ""
                    for selector in titolo_selectors:
                        try:
                            elemento = driver.find_element(By.CSS_SELECTOR, selector)
                            titolo = elemento.text.strip()
                            if titolo:
                                break
                        except:
                            continue
                    
                    # Se non trovato il titolo dai selettori, prova con la riga
                    if not titolo:
                        titolo = riga_corrente.text.split('\n')[0] if riga_corrente.text else "Circolare"
                    
                    # Torna indietro alla lista
                    driver.back()
                    time.sleep(3)
                    
                except Exception as e:
                    print(f"⚠️ Errore nell'estrazione dettagli: {e}")
                    driver.back()
                    time.sleep(3)
                    continue
                    
            except:
                # Se non riesci a cliccare, usa il testo della riga
                riga_testo = riga_corrente.text
                data_circolare = estrai_data_da_testo(riga_testo)
                titolo = riga_testo.split('\n')[0] if riga_testo else "Circolare"
                
            # Ora trova le colonne per gli altri dati
            colonne = riga_corrente.find_elements(By.TAG_NAME, "td")
            if not colonne:
                colonne = riga_corrente.find_elements(By.CSS_SELECTOR, "div, span")
            
            # Colonna per allegati
            cella_file = None
            if len(colonne) > 4:
                cella_file = colonne[4]
            elif len(colonne) > 3:
                cella_file = colonne[3]
            
        except Exception as e:
            print(f"⚠️ Errore nel recuperare la riga {i}: {e}")
            continue
        
        # ===> FILTRO 30 GIORNI <===
        if data_circolare:
            # Calcola quanti giorni sono passati
            giorni_passati = (datetime.now() - data_circolare).days
            
            if giorni_passati > 30:
                print(f"\n⏹️  INCONTRATA CIRCOLARE VECCHIA: {data_circolare.strftime('%d/%m/%Y')} (Vecchia di {giorni_passati} giorni)")
                print(f"🛑 Fermo lo scaricamento. Ho elaborato {circolari_elaborate} circolari recenti.")
                # Esci completamente dal ciclo
                break
            
            data_str = data_circolare.strftime('%d/%m/%Y')
            print(f"\n🔄 Elaboro circolare recente: {data_str} - {titolo[:50]}...")
        else:
            print(f"⚠️ Data non trovata per: {titolo[:50]}...")
            # Se non trovi la data, salta questa circolare
            continue
        
        # SE SIAMO QUI, LA CIRCOLARE È RECENTE (<30 giorni) -> PROCEDIAMO
        circolari_elaborate += 1
        
        ha_allegati = False
        public_links_string = ""
        
        # Controlla se ci sono allegati
        if cella_file and (cella_file.text.strip() != "" or len(cella_file.find_elements(By.TAG_NAME, "div")) > 0):
            ha_allegati = True
        
        # GESTIONE ALLEGATI
        if ha_allegati:
            print("   📎 Scarico allegati...")
            try:
                # Clicca sulla cella degli allegati
                cella_file.click()
                time.sleep(2)
                
                # Prova a cliccare su eventuali div interni
                try:
                    cella_file.find_element(By.TAG_NAME, "div").click()
                except:
                    pass
                
                time.sleep(4)
                
                # Cerca link PDF
                links_pdf = driver.find_elements(By.PARTIAL_LINK_TEXT, ".pdf")
                if not links_pdf:
                    # Prova con altri selettori per PDF
                    links_pdf = driver.find_elements(By.CSS_SELECTOR, "a[href$='.pdf'], a[href*='download'], a[href*='allegato']")
                
                lista_url_pubblici = []
                
                for index_file, link in enumerate(links_pdf):
                    print(f"      ⬇️ Download allegato {index_file+1}...")
                    
                    # Clicca sul link per avviare il download
                    link.click()
                    
                    # Attendi il download
                    file_scaricato = attendi_e_trova_file()
                    
                    if file_scaricato:
                        # Carica su Supabase Storage
                        nome_semplice = f"circolare_{data_str.replace('/', '_')}_{index_file + 1}.pdf"
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
                
                public_links_string = ";;;".join(lista_url_pubblici)
                
                # TORNA ALLA LISTA DELLE CIRCOLARI
                print("   🔙 Torno alla lista delle circolari...")
                try:
                    # Prova a tornare indietro
                    driver.back()
                    time.sleep(3)
                    
                    # Ricarica la pagina se necessario
                    wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "x-grid-row")))
                    
                except Exception as e:
                    print(f"   ⚠️ Errore nel tornare indietro: {e}")
                    # Se non riesce a tornare, ricarica la pagina
                    driver.get(driver.current_url)
                    time.sleep(5)

            except Exception as e:
                print(f"   ⚠️ Errore nella gestione allegati: {e}")
                # In caso di errore, continua senza allegati
                pass
        
        # SALVATAGGIO NEL DATABASE
        try:
            # Formatta la data per il database
            data_pubblica = data_circolare.strftime("%Y-%m-%d %H:%M:%S")
            
            # Controlla se la circolare esiste già (per titolo e data)
            res = supabase.table('circolari').select("*").eq('titolo', titolo).eq('data_pubblica', data_pubblica).execute()
            
            if not res.data:
                # Inserisci nuova circolare
                supabase.table('circolari').insert({
                    "titolo": titolo,
                    "contenuto": f"Data pubblicazione: {data_str}",
                    "data_pubblica": data_pubblica,
                    "pdf_url": public_links_string
                }).execute()
                print("   ✅ Circolare salvata nel database.")
            else:
                # Aggiorna circolare esistente (solo allegati se nuovi)
                if public_links_string and not res.data[0].get('pdf_url'):
                    supabase.table('circolari').update({"pdf_url": public_links_string}).eq('id', res.data[0]['id']).execute()
                    print("   🔄 Allegati aggiunti.")
                else:
                    print("   💤 Circolare già presente nel database.")
                    
        except Exception as e:
            print(f"   ⚠️ Errore nel salvataggio database: {e}")
    
    print(f"\n🎉 Elaborazione completata. Circolari recenti elaborate: {circolari_elaborate}")

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
