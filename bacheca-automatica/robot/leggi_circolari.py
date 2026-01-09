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

def converti_data_argo(data_str):
    """Converte la data dal formato Argo (DD/MM/YYYY) a datetime"""
    try:
        return datetime.strptime(data_str.strip(), "%d/%m/%Y")
    except Exception as e:
        print(f"⚠️ Errore conversione data '{data_str}': {e}")
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
            print(f"✅ Trovata tabella con selettore: {selector}")
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
    print(f"✅ Trovate {numero_totale} righe di circolari.")
    
    # --- CICLO PER OGNI RIGA/CIRCOLARE ---
    circolari_elaborate = 0
    
    for i in range(numero_totale):
        try:
            # Ricarica le righe per evitare elementi stantii
            if tabella:
                righe_fresche = tabella.find_elements(By.CSS_SELECTOR, "tr")
                if righe_fresche and ("DATA" in righe_fresche[0].text or "DATA" in righe_fresche[0].get_attribute('innerHTML')):
                    righe_fresche = righe_fresche[1:]
            else:
                righe_fresche = driver.find_elements(By.CSS_SELECTOR, "tr, .x-grid-row, .list-item")
            
            if i >= len(righe_fresche):
                break
                
            riga_corrente = righe_fresche[i]
            
            # ESTRAI LE COLONNE DELLA RIGA
            # Prima prova con le celle td
            colonne = riga_corrente.find_elements(By.TAG_NAME, "td")
            
            # Se non trova td, prova con altri elementi
            if not colonne:
                colonne = riga_corrente.find_elements(By.CSS_SELECTOR, "div, span")
            
            # Se non ci sono abbastanza colonne, salta
            if len(colonne) < 5:
                print(f"⚠️ Riga {i+1}: Troppo poche colonne ({len(colonne)}), salto")
                continue
            
            # COLONNA 0: DATA (es: 09/01/2026)
            data_str = colonne[0].text.strip()
            if not data_str:
                print(f"⚠️ Riga {i+1}: Data vuota, salto")
                continue
            
            # COLONNA 1: CATEGORIA (es: CIRCOLARI INTERNE)
            categoria = colonne[1].text.strip()
            
            # COLONNA 2: NUM. DOC. (di solito vuoto o numero)
            num_doc = colonne[2].text.strip()
            
            # COLONNA 3: MESSAGGIO/TITOLO (es: CIRCOLARE N.160 OGGETTO: ...)
            titolo = colonne[3].text.strip()
            
            # COLONNA 4: FILE/ALLEGATI
            cella_file = colonne[4]
            
            # CONVERTI LA DATA
            data_circolare = converti_data_argo(data_str)
            if not data_circolare:
                print(f"⚠️ Riga {i+1}: Data '{data_str}' non valida, salto")
                continue
            
            # ===> FILTRO 30 GIORNI <===
            giorni_passati = (datetime.now() - data_circolare).days
            
            if giorni_passati > 30:
                print(f"\n⏹️  INCONTRATA CIRCOLARE VECCHIA: {data_str} (Vecchia di {giorni_passati} giorni)")
                print(f"🛑 Fermo lo scaricamento. Ho elaborato {circolari_elaborate} circolari recenti.")
                # Esci completamente dal ciclo
                break
            
            print(f"\n🔄 [{i+1}] Elaboro circolare recente: {data_str} - {categoria}")
            print(f"   📄 Titolo: {titolo[:80]}...")
            
            # SE SIAMO QUI, LA CIRCOLARE È RECENTE (<30 giorni) -> PROCEDIAMO
            circolari_elaborate += 1
            
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
                        except Exception as e:
                            print(f"      ⚠️ Errore download allegato {index_file+1}: {e}")
                            continue
                    
                    public_links_string = ";;;".join(lista_url_pubblici)
                    
                    # TORNA ALLA LISTA DELLE CIRCOLARI
                    print("   🔙 Torno alla lista delle circolari...")
                    driver.get(url_corrente)
                    time.sleep(5)
                    
                    # Ricarica la tabella
                    if tabella:
                        tabella = driver.find_element(By.CSS_SELECTOR, table_selectors[0])
                        righe_fresche = tabella.find_elements(By.CSS_SELECTOR, "tr")
                        if righe_fresche and ("DATA" in righe_fresche[0].text):
                            righe_fresche = righe_fresche[1:]
                    
                except Exception as e:
                    print(f"   ⚠️ Errore nella gestione allegati: {e}")
                    # In caso di errore, torna alla lista
                    try:
                        driver.back()
                        time.sleep(3)
                    except:
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
                        "contenuto": f"Categoria: {categoria} | Num. Doc: {num_doc}",
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
                
        except Exception as e:
            print(f"⚠️ Errore nell'elaborazione riga {i+1}: {e}")
            continue
    
    print(f"\n🎉 Elaborazione completata. Circolari recenti elaborate: {circolari_elaborate}")
    
    # Riepilogo finale
    if circolari_elaborate > 0:
        print(f"\n📊 RIEPILOGO:")
        print(f"   • Circolari totali trovate: {numero_totale}")
        print(f"   • Circolari recenti (<30gg) elaborate: {circolari_elaborate}")
        print(f"   • Circolari vecchie scartate: {max(0, numero_totale - circolari_elaborate)}")

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
