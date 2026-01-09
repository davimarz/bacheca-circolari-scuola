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
    
    # Cerca pattern di data nel formato DD/MM/YYYY
    pattern = r'(\d{2})/(\d{2})/(\d{4})'
    matches = re.findall(pattern, testo)
    
    for match in matches:
        try:
            giorno, mese, anno = map(int, match)
            # Validazione base
            if 1 <= giorno <= 31 and 1 <= mese <= 12 and anno >= 2020:
                return datetime(anno, mese, giorno)
        except:
            continue
    
    return None

def aggiorna_date_dal_contenuto():
    """Aggiorna le date di pubblicazione analizzando il contenuto delle circolari"""
    print("📅 Aggiorno le date di pubblicazione dal contenuto...")
    
    try:
        res = supabase.table('circolari').select("id, titolo, contenuto, data_pubblica").execute()
        
        if not res.data:
            print("   ✅ Nessuna circolare nel database.")
            return
        
        aggiornate = 0
        for circolare in res.data:
            contenuto = circolare.get('contenuto', '')
            if not contenuto:
                continue
            
            # Estrai la data dal contenuto
            data_dal_contenuto = estrai_data_dal_testo(contenuto)
            
            if data_dal_contenuto:
                nuova_data = data_dal_contenuto.strftime("%Y-%m-%d %H:%M:%S")
                data_attuale = circolare.get('data_pubblica', '')
                
                if nuova_data != data_attuale:
                    try:
                        supabase.table('circolari').update({
                            'data_pubblica': nuova_data
                        }).eq('id', circolare['id']).execute()
                        aggiornate += 1
                        print(f"   ✅ Aggiornata: {circolare['titolo'][:50]}...")
                    except Exception as e:
                        print(f"   ⚠️  Errore: {e}")
        
        print(f"   🎉 Date aggiornate: {aggiornate}")
    except Exception as e:
        print(f"   ⚠️  Errore aggiornamento date: {e}")

def rimuovi_circolari_vecchie():
    """Rimuove dal database le circolari più vecchie di 30 giorni"""
    print("🧹 Controllo circolari vecchie...")
    
    try:
        # Calcola la data limite
        data_limite = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        
        # Trova circolari vecchie
        res = supabase.table('circolari').select("*").lt('data_pubblica', data_limite).execute()
        
        if not res.data:
            print("   ✅ Nessuna circolare vecchia da eliminare.")
            return
        
        print(f"   🗑️  Trovate {len(res.data)} circolari vecchie da eliminare...")
        
        for circolare in res.data:
            # Elimina file dallo storage se presenti
            pdf_url = circolare.get('pdf_url', '')
            if pdf_url:
                try:
                    urls = pdf_url.split(';;;')
                    for url in urls:
                        if url.strip():
                            filename = url.split('/')[-1]
                            if filename:
                                supabase.storage.from_("documenti").remove([filename])
                except:
                    pass
            
            # Elimina dal database
            supabase.table('circolari').delete().eq('id', circolare['id']).execute()
        
        print(f"   🎉 Eliminate {len(res.data)} circolari vecchie")
    except Exception as e:
        print(f"   ⚠️  Errore pulizia circolari: {e}")

try:
    # --- PRIMA AGGIORNA LE DATE DAL CONTENUTO ---
    aggiorna_date_dal_contenuto()
    
    # --- POI RIMUOVI LE CIRCOLARI VECCHIE ---
    rimuovi_circolari_vecchie()
    
    # --- LOGIN ---
    print("🌍 Login...")
    driver.get("https://www.portaleargo.it/famiglia")
    time.sleep(3)
    
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
    
    # Usa lo stesso approccio del tuo codice funzionante
    driver.find_element(By.XPATH, "//*[contains(text(), 'Bacheca')]").click()
    time.sleep(2)
    
    try:
        sub = driver.find_element(By.XPATH, "//*[contains(text(), 'Messaggi da leggere')]")
        driver.execute_script("arguments[0].click();", sub)
    except:
        try:
            sub = driver.find_element(By.XPATH, "//*[contains(text(), 'Gestione Bacheca')]")
            driver.execute_script("arguments[0].click();", sub)
        except: 
            pass
    
    print("⏳ Caricamento tabella...")
    time.sleep(8)
    
    # --- TROVA LE CIRCOLARI ---
    print("🔍 Cerco le circolari...")
    
    # Usa lo stesso selettore del tuo codice funzionante
    righe = driver.find_elements(By.CLASS_NAME, "x-grid-row")
    if not righe:
        # Prova altri selettori
        righe = driver.find_elements(By.CSS_SELECTOR, "tr")
    
    numero_totale = len(righe)
    print(f"✅ Trovate {numero_totale} circolari totali.")
    
    # --- CICLO PER OGNI CIRCOLARE ---
    circolari_elaborate = 0
    
    for i in range(numero_totale):
        print(f"\n{'='*60}")
        print(f"🔄 [{i+1}/{numero_totale}] Elaboro circolare...")
        
        try:
            # Ricarica le righe
            righe_fresche = driver.find_elements(By.CLASS_NAME, "x-grid-row")
            if not righe_fresche:
                righe_fresche = driver.find_elements(By.CSS_SELECTOR, "tr")
            
            if i >= len(righe_fresche):
                break
            
            riga_corrente = righe_fresche[i]
            colonne = riga_corrente.find_elements(By.TAG_NAME, "td")
            
            if len(colonne) < 5:
                print("   ⚠️  Troppo poche colonne, salto")
                continue
            
            # Estrai dati
            data_str = colonne[0].text.strip()  # Data dalla tabella
            categoria = colonne[1].text.strip()
            titolo = colonne[3].text.replace("\n", " ").strip()
            cella_file = colonne[4]
            
            print(f"   📅 Data tabella: {data_str}")
            print(f"   📌 Titolo: {titolo[:80]}...")
            
            # ===> FILTRO 30 GIORNI (USANDO LA DATA DALLA TABELLA) <===
            try:
                data_circolare = datetime.strptime(data_str, "%d/%m/%Y")
                giorni_passati = (datetime.now() - data_circolare).days
                
                if giorni_passati > 30:
                    print(f"⏹️  CIRCOLARE VECCHIA: {giorni_passati} giorni")
                    print(f"🛑 Fermo lo scaricamento.")
                    break
                
                print(f"   ✅ Circolare recente ({giorni_passati} giorni)")
            except Exception as e:
                print(f"   ⚠️  Errore data, salto: {e}")
                continue
            
            # SE SIAMO QUI, LA CIRCOLARE È RECENTE
            circolari_elaborate += 1
            
            # CLICCA PER VEDERE IL CONTENUTO COMPLETO
            print("   🔍 Apro per estrarre contenuto...")
            contenuto_completo = ""
            data_dal_contenuto = None
            
            try:
                # Clicca sulla circolare
                colonne[3].click()  # Clicca sul titolo
                time.sleep(4)
                
                # Estrai il contenuto
                try:
                    # Prova diversi selettori
                    selettori = [
                        ".x-panel-body",
                        ".content",
                        ".contenuto",
                        "body"
                    ]
                    
                    for selettore in selettori:
                        try:
                            elemento = driver.find_element(By.CSS_SELECTOR, selettore)
                            contenuto_completo = elemento.text
                            if contenuto_completo and len(contenuto_completo) > 100:
                                break
                        except:
                            continue
                except:
                    pass
                
                # Estrai data dal contenuto
                if contenuto_completo:
                    data_dal_contenuto = estrai_data_dal_testo(contenuto_completo)
                    if data_dal_contenuto:
                        print(f"   📅 Data dal contenuto: {data_dal_contenuto.strftime('%d/%m/%Y')}")
                
                # Torna indietro
                driver.back()
                time.sleep(3)
                
            except Exception as e:
                print(f"   ⚠️  Errore apertura circolare: {e}")
                # Tenta di tornare
                try:
                    driver.back()
                    time.sleep(3)
                except:
                    pass
            
            # CONTROLLA ALLEGATI
            ha_allegati = False
            public_links_string = ""
            
            if cella_file.text.strip() != "" or len(cella_file.find_elements(By.TAG_NAME, "div")) > 0:
                ha_allegati = True
            
            if ha_allegati:
                print("   📎 Scarico allegati...")
                try:
                    cella_file.click()
                    time.sleep(3)
                    
                    # Cerca PDF
                    links_pdf = driver.find_elements(By.PARTIAL_LINK_TEXT, ".pdf")
                    if not links_pdf:
                        links_pdf = driver.find_elements(By.CSS_SELECTOR, "a[href$='.pdf']")
                    
                    lista_url = []
                    
                    for idx, link in enumerate(links_pdf):
                        try:
                            print(f"      ⬇️ Download {idx+1}...")
                            link.click()
                            
                            file_scaricato = attendi_e_trova_file()
                            if file_scaricato:
                                nome_unico = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{idx+1}.pdf"
                                
                                with open(file_scaricato, "rb") as f:
                                    supabase.storage.from_("documenti").upload(
                                        path=nome_unico,
                                        file=f,
                                        file_options={"content-type": "application/pdf"}
                                    )
                                
                                url_pubblico = supabase.storage.from_("documenti").get_public_url(nome_unico)
                                lista_url.append(url_pubblico)
                                
                                f.close()
                                os.remove(file_scaricato)
                                print(f"      ✅ Caricato: {nome_unico}")
                        except Exception as e:
                            print(f"      ⚠️  Errore: {e}")
                            continue
                    
                    public_links_string = ";;;".join(lista_url)
                    
                    # Torna indietro
                    driver.back()
                    time.sleep(3)
                    
                except Exception as e:
                    print(f"   ⚠️  Errore allegati: {e}")
            
            # SALVATAGGIO NEL DATABASE
            try:
                # Usa la data dal contenuto se disponibile, altrimenti dalla tabella
                if data_dal_contenuto:
                    data_pubblica = data_dal_contenuto.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    data_pubblica = data_circolare.strftime("%Y-%m-%d %H:%M:%S")
                
                # Controlla se esiste già
                res = supabase.table('circolari').select("*").eq('titolo', titolo).execute()
                
                if not res.data:
                    # Inserisci nuova
                    supabase.table('circolari').insert({
                        "titolo": titolo,
                        "contenuto": contenuto_completo if contenuto_completo else f"Data: {data_str} | Categoria: {categoria}",
                        "data_pubblica": data_pubblica,
                        "pdf_url": public_links_string
                    }).execute()
                    print("   ✅ Salvata nel database.")
                else:
                    # Aggiorna se ci sono nuovi allegati
                    if public_links_string and not res.data[0].get('pdf_url'):
                        supabase.table('circolari').update({
                            "pdf_url": public_links_string
                        }).eq('titolo', titolo).execute()
                        print("   🔄 Allegati aggiunti.")
                    else:
                        print("   💤 Già presente.")
                        
            except Exception as e:
                print(f"   ⚠️  Errore database: {e}")
                
        except Exception as e:
            print(f"⚠️ Errore circolare {i+1}: {e}")
            continue
    
    print(f"\n{'='*60}")
    print(f"🎉 ELABORAZIONE COMPLETATA")
    print(f"   • Circolari trovate: {numero_totale}")
    print(f"   • Circolari elaborate: {circolari_elaborate}")
    print(f"   • Circolari scartate: {numero_totale - circolari_elaborate}")

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
