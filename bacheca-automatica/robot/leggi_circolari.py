import os
import time
import glob
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import psycopg2
from psycopg2.extras import RealDictCursor
import re

print("🤖 Robot avviato")

# ==============================================================================
# 🛑 CONFIGURAZIONE DA VARIABILI D'AMBIENTE
# ==============================================================================
config = {
    'ARGO_USER': os.environ.get('ARGO_USER'),
    'ARGO_PASS': os.environ.get('ARGO_PASS'),
    'DB_HOST': os.environ.get('DB_HOST', 'db.ojnofjebrlwrlowovvjd.supabase.co'),
    'DB_PORT': os.environ.get('DB_PORT', '5432'),
    'DB_NAME': os.environ.get('DB_NAME', 'postgres'),
    'DB_USER': os.environ.get('DB_USER', 'postgres'),
    'DB_PASSWORD': os.environ.get('DB_PASSWORD'),
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

# --- CONNESSIONE POSTGRESQL ---
def get_db_connection():
    """Crea e restituisce una connessione al database PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=config['DB_HOST'],
            port=config['DB_PORT'],
            database=config['DB_NAME'],
            user=config['DB_USER'],
            password=config['DB_PASSWORD'],
            sslmode='require'  # Supabase richiede SSL
        )
        return conn
    except Exception as e:
        print(f"❌ Errore connessione database: {e}")
        raise

print("📡 Mi collego al database PostgreSQL...")
conn = get_db_connection()
cur = conn.cursor(cursor_factory=RealDictCursor)

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
        # Ottieni tutte le circolari
        cur.execute("SELECT id, titolo, contenuto, data_pubblica FROM circolari")
        circolari = cur.fetchall()
        
        if not circolari:
            print("   ✅ Nessuna circolare nel database.")
            return
        
        aggiornate = 0
        for circolare in circolari:
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
                        cur.execute(
                            "UPDATE circolari SET data_pubblica = %s WHERE id = %s",
                            (nuova_data, circolare['id'])
                        )
                        conn.commit()
                        aggiornate += 1
                        print(f"   ✅ Aggiornata: {circolare['titolo'][:50]}...")
                    except Exception as e:
                        print(f"   ⚠️  Errore aggiornamento: {e}")
                        conn.rollback()
        
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
        cur.execute(
            "SELECT id, titolo, pdf_url FROM circolari WHERE data_pubblica < %s",
            (data_limite,)
        )
        circolari_vecchie = cur.fetchall()
        
        if not circolari_vecchie:
            print("   ✅ Nessuna circolare vecchia da eliminare.")
            return
        
        print(f"   🗑️  Trovate {len(circolari_vecchie)} circolari vecchie da eliminare...")
        
        for circolare in circolari_vecchie:
            try:
                # Elimina dal database
                cur.execute("DELETE FROM circolari WHERE id = %s", (circolare['id'],))
                conn.commit()
                print(f"      ✅ Rimossa: {circolare['titolo'][:50]}...")
            except Exception as e:
                print(f"      ⚠️  Errore eliminazione: {e}")
                conn.rollback()
        
        print(f"   🎉 Eliminate {len(circolari_vecchie)} circolari vecchie")
    except Exception as e:
        print(f"   ⚠️  Errore pulizia circolari: {e}")

def circolare_esiste(titolo, data_pubblica):
    """Controlla se una circolare esiste già nel database"""
    try:
        cur.execute(
            "SELECT id FROM circolari WHERE titolo = %s AND data_pubblica = %s",
            (titolo, data_pubblica)
        )
        return cur.fetchone() is not None
    except Exception as e:
        print(f"   ⚠️  Errore controllo esistenza: {e}")
        return False

def salva_circolare(titolo, contenuto, data_pubblica, pdf_url):
    """Salva una circolare nel database"""
    try:
        cur.execute(
            """INSERT INTO circolari (titolo, contenuto, data_pubblica, pdf_url, created_at)
               VALUES (%s, %s, %s, %s, NOW())""",
            (titolo, contenuto, data_pubblica, pdf_url)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"   ⚠️  Errore salvataggio: {e}")
        conn.rollback()
        return False

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
    
    # Cerca il link Circolari
    try:
        circolari_link = wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Circolari"))
        )
        circolari_link.click()
    except:
        # Fallback: cerca Bacheca
        try:
            driver.find_element(By.XPATH, "//*[contains(text(), 'Bacheca')]").click()
            time.sleep(2)
            
            # Cerca sottomenu
            try:
                driver.find_element(By.XPATH, "//*[contains(text(), 'Messaggi da leggere')]").click()
            except:
                try:
                    driver.find_element(By.XPATH, "//*[contains(text(), 'Gestione Bacheca')]").click()
                except:
                    pass
        except Exception as e:
            print(f"⚠️ Errore navigazione: {e}")
    
    print("⏳ Caricamento tabella...")
    time.sleep(8)
    
    # --- TROVA LE CIRCOLARI ---
    print("🔍 Cerco le circolari...")
    
    # Prova diversi selettori
    righe = driver.find_elements(By.CLASS_NAME, "x-grid-row")
    if not righe:
        righe = driver.find_elements(By.CSS_SELECTOR, "tr")
    if not righe:
        righe = driver.find_elements(By.CSS_SELECTOR, ".list-item, .item")
    
    numero_totale = len(righe)
    print(f"✅ Trovate {numero_totale} circolari totali.")
    
    if numero_totale == 0:
        print("❌ Nessuna circolare trovata. Verifica la navigazione.")
        exit(1)
    
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
            
            # Estrai colonne
            colonne = riga_corrente.find_elements(By.TAG_NAME, "td")
            if not colonne or len(colonne) < 5:
                colonne = riga_corrente.find_elements(By.CSS_SELECTOR, "div")
            
            if len(colonne) < 5:
                print("   ⚠️  Struttura non valida, salto")
                continue
            
            # Estrai dati base
            data_str = colonne[0].text.strip() if colonne[0].text.strip() else ""
            categoria = colonne[1].text.strip() if len(colonne) > 1 else ""
            titolo = colonne[3].text.strip() if len(colonne) > 3 else ""
            cella_file = colonne[4] if len(colonne) > 4 else None
            
            if not titolo:
                titolo = riga_corrente.text.split('\n')[0] if riga_corrente.text else f"Circolare {i+1}"
            
            print(f"   📅 Data: {data_str}")
            print(f"   📌 Titolo: {titolo[:80]}...")
            
            # ===> FILTRO 30 GIORNI <===
            data_circolare = None
            if data_str:
                try:
                    data_circolare = datetime.strptime(data_str, "%d/%m/%Y")
                    giorni_passati = (datetime.now() - data_circolare).days
                    
                    if giorni_passati > 30:
                        print(f"⏹️  CIRCOLARE VECCHIA: {giorni_passati} giorni")
                        print(f"🛑 Fermo lo scaricamento.")
                        break
                    
                    print(f"   ✅ Recente ({giorni_passati} giorni)")
                except:
                    print("   ⚠️  Formato data non valido")
            
            # SE CIRCOLARE RECENTE, PROCEDI
            circolari_elaborate += 1
            
            # CLICCA PER CONTENUTO
            print("   🔍 Estraggo contenuto...")
            contenuto_completo = ""
            data_dal_contenuto = None
            
            try:
                # Salva URL corrente
                url_corrente = driver.current_url
                
                # Clicca sulla circolare
                if len(colonne) > 3:
                    colonne[3].click()
                else:
                    riga_corrente.click()
                
                time.sleep(4)
                
                # Estrai contenuto
                try:
                    # Prova vari selettori
                    selettori = [
                        "body",
                        ".x-panel-body",
                        ".content",
                        ".contenuto",
                        "#content",
                        "div[class*='content']",
                        "div[class*='body']"
                    ]
                    
                    for selettore in selettori:
                        try:
                            elem = driver.find_element(By.CSS_SELECTOR, selettore)
                            testo = elem.text.strip()
                            if testo and len(testo) > len(contenuto_completo):
                                contenuto_completo = testo
                        except:
                            continue
                    
                    if contenuto_completo:
                        print(f"   📄 Contenuto estratto ({len(contenuto_completo)} caratteri)")
                        
                        # Estrai data dal contenuto
                        data_dal_contenuto = estrai_data_dal_testo(contenuto_completo)
                        if data_dal_contenuto:
                            print(f"   📅 Data dal contenuto: {data_dal_contenuto.strftime('%d/%m/%Y')}")
                except Exception as e:
                    print(f"   ⚠️  Errore estrazione contenuto: {e}")
                
                # Torna indietro
                driver.get(url_corrente)
                time.sleep(3)
                
            except Exception as e:
                print(f"   ⚠️  Errore apertura circolare: {e}")
                # Tenta di tornare
                try:
                    driver.back()
                    time.sleep(3)
                except:
                    pass
            
            # DETERMINA DATA FINALE
            if data_dal_contenuto:
                data_finale = data_dal_contenuto
            elif data_circolare:
                data_finale = data_circolare
            else:
                data_finale = datetime.now()
            
            data_pubblica_db = data_finale.strftime("%Y-%m-%d %H:%M:%S")
            
            # CONTROLLA SE ESISTE GIA'
            if circolare_esiste(titolo, data_pubblica_db):
                print("   💤 Già presente nel database")
                continue
            
            # ALLEGATI (semplificato)
            print("   📎 Controllo allegati...")
            pdf_url = ""
            # Qui puoi aggiungere la logica per scaricare allegati se necessario
            
            # SALVATAGGIO
            if salva_circolare(titolo, contenuto_completo, data_pubblica_db, pdf_url):
                print("   ✅ Salvata nel database PostgreSQL")
            else:
                print("   ❌ Errore salvataggio")
                
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
    
    # Chiudi connessioni
    print("🔒 Chiudo connessioni...")
    try:
        cur.close()
        conn.close()
    except:
        pass
    
    print("🔒 Chiusura browser...")
    try:
        driver.quit()
    except:
        pass

print("✅ Robot completato!")
