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
    'DB_HOST': 'db.ojnofjebrlwrlowovvjd.supabase.co',
    'DB_PORT': '5432',
    'DB_NAME': 'postgres',
    'DB_USER': 'postgres',
    'DB_PASSWORD': os.environ.get('DB_PASSWORD'),
}

# Verifica configurazione
if not config['ARGO_USER'] or not config['ARGO_PASS']:
    print("❌ ERRORE: Configura ARGO_USER e ARGO_PASS nelle variabili d'ambiente")
    exit(1)

if not config['DB_PASSWORD']:
    print("❌ ERRORE: Configura DB_PASSWORD (password di Supabase PostgreSQL)")
    exit(1)

# ==============================================================================

# --- CONFIGURAZIONE CHROME SEMPLIFICATA ---
# --- CONFIGURAZIONE CHROME PER RENDER FREE ---
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

# Per Render Free, usa ChromeDriver binary incluso
service = Service()
driver = webdriver.Chrome(service=service, options=chrome_options)

# Configurazione download PDF
cartella_download = os.path.join(os.getcwd(), "downloads_temp")
if not os.path.exists(cartella_download):
    os.makedirs(cartella_download)

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
            sslmode='require'
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

# ==============================================================================
# FUNZIONI UTILITY
# ==============================================================================

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

def salva_circolare_db(titolo, contenuto, data_pubblica, pdf_url=""):
    """Salva una circolare nel database PostgreSQL"""
    try:
        # Prima controlla se esiste già
        cur.execute(
            "SELECT id FROM circolari WHERE titolo = %s AND data_pubblica = %s",
            (titolo, data_pubblica)
        )
        if cur.fetchone():
            print("   💤 Già presente nel database")
            return False
        
        # Inserisci nuova circolare
        cur.execute(
            """INSERT INTO circolari (titolo, contenuto, data_pubblica, pdf_url, created_at)
               VALUES (%s, %s, %s, %s, NOW())""",
            (titolo, contenuto, data_pubblica, pdf_url)
        )
        conn.commit()
        print("   ✅ Salvata nel database PostgreSQL")
        return True
    except Exception as e:
        print(f"   ❌ Errore salvataggio database: {e}")
        conn.rollback()
        return False

def pulisci_circolari_vecchie():
    """Rimuove le circolari più vecchie di 30 giorni"""
    print("🧹 Pulizia circolari vecchie (>30 giorni)...")
    try:
        data_limite = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("DELETE FROM circolari WHERE data_pubblica < %s", (data_limite,))
        conn.commit()
        print("   ✅ Pulizia completata")
    except Exception as e:
        print(f"   ⚠️  Errore pulizia: {e}")

# ==============================================================================
# LOGICA PRINCIPALE
# ==============================================================================

try:
    # --- PULIZIA INIZIALE ---
    pulisci_circolari_vecchie()
    
    # --- LOGIN SEMPLICE ---
    print("🌍 Login su Argo...")
    driver.get("https://www.portaleargo.it/famiglia")
    time.sleep(3)
    
    # Compila login
    driver.find_element(By.ID, "username").send_keys(config['ARGO_USER'])
    driver.find_element(By.ID, "password").send_keys(config['ARGO_PASS'])
    driver.find_element(By.ID, "login-button").click()
    
    print("⏳ Attendo login...")
    time.sleep(5)
    
    # --- VAI ALLE CIRCOLARI ---
    print("👉 Navigo alle Circolari...")
    
    # Cerca il link "Circolari" - APPROCCIO DIRETTO
    try:
        # Prima prova con link esatto
        circolari_link = driver.find_element(By.LINK_TEXT, "Circolari")
        circolari_link.click()
    except:
        # Se non trova, prova con testo parziale
        try:
            circolari_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Circolari')]")
            circolari_link.click()
        except:
            # Ultimo tentativo: cerca qualsiasi link che contenga "circolari" (case insensitive)
            try:
                links = driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    if 'circolari' in link.text.lower():
                        link.click()
                        break
            except:
                print("❌ Non trovo il link delle circolari")
                # Fa screenshot per debug
                driver.save_screenshot("errore_circolari.png")
                print("📸 Screenshot salvato come 'errore_circolari.png'")
                exit(1)
    
    print("⏳ Caricamento pagina circolari...")
    time.sleep(8)
    
    # --- CERCA LE CIRCOLARI ---
    print("🔍 Cerco le circolari nella pagina...")
    
    # APPROCCIO 1: Cerca righe di tabella
    righe = driver.find_elements(By.TAG_NAME, "tr")
    print(f"📊 Trovate {len(righe)} righe di tabella")
    
    # Filtra solo righe che sembrano circolari (hanno testo e possibilmente date)
    circolari_trovate = []
    for riga in righe:
        testo = riga.text.strip()
        if testo and len(testo) > 30:  # Almeno un po' di testo
            # Cerca indicatori di circolare
            if any(keyword in testo.lower() for keyword in ['circolare', 'prot.', 'n.', '/202']):
                circolari_trovate.append(riga)
    
    print(f"✅ Identificate {len(circolari_trovate)} possibili circolari")
    
    if not circolari_trovate:
        print("⚠️ Nessuna circolare identificata. Controllo struttura pagina...")
        
        # Cerca altri elementi che potrebbero essere circolari
        elementi_testo = driver.find_elements(By.XPATH, "//*[contains(text(), 'CIRCOLARE') or contains(text(), 'Circolare')]")
        print(f"📝 Elementi con testo 'CIRCOLARE': {len(elementi_testo)}")
        
        for elem in elementi_testo[:10]:  # Mostra primi 10
            print(f"  - {elem.text[:100]}...")
        
        exit(1)
    
    # --- ELABORA OGNI CIRCOLARE ---
    print(f"\n🎯 Inizio elaborazione di {len(circolari_trovate)} circolari...")
    
    for idx, riga in enumerate(circolari_trovate):
        print(f"\n{'='*60}")
        print(f"🔄 [{idx+1}/{len(circolari_trovate)}] Processo circolare...")
        
        try:
            # Estrai testo della riga
            testo_riga = riga.text.strip()
            print(f"   📄 Testo riga ({len(testo_riga)} caratteri):")
            print(f"      {testo_riga[:150]}...")
            
            # Dividi in linee
            linee = testo_riga.split('\n')
            
            # Estrai titolo (prima linea significativa)
            titolo = ""
            for linea in linee:
                linea = linea.strip()
                if linea and len(linea) > 10:
                    titolo = linea[:200]
                    break
            
            if not titolo:
                titolo = f"Circolare {idx+1}"
            
            print(f"   📌 Titolo estratto: {titolo[:80]}...")
            
            # Cerca data nel testo della riga
            data_circolare = estrai_data_dal_testo(testo_riga)
            
            if data_circolare:
                print(f"   📅 Data trovata nel testo: {data_circolare.strftime('%d/%m/%Y')}")
                
                # FILTRO 30 GIORNI
                giorni_passati = (datetime.now() - data_circolare).days
                if giorni_passati > 30:
                    print(f"⏹️  CIRCOLARE VECCHIA: {giorni_passati} giorni")
                    print(f"🛑 Fermo elaborazione.")
                    break
                
                print(f"   ✅ Circolare recente ({giorni_passati} giorni fa)")
                
                # CLICCA PER VEDERE IL CONTENUTO COMPLETO
                print("   🔍 Apro per contenuto completo...")
                contenuto_completo = ""
                
                try:
                    # Salva URL corrente
                    url_corrente = driver.current_url
                    
                    # Clicca sulla riga
                    riga.click()
                    time.sleep(4)
                    
                    # Estrai tutto il testo della pagina
                    try:
                        body = driver.find_element(By.TAG_NAME, "body")
                        contenuto_completo = body.text
                        
                        # Cerca la data anche nel contenuto completo
                        data_dal_contenuto = estrai_data_dal_testo(contenuto_completo)
                        if data_dal_contenuto:
                            print(f"   📅 Data dal contenuto: {data_dal_contenuto.strftime('%d/%m/%Y')}")
                            data_circolare = data_dal_contenuto  # Usa la data più precisa
                    except Exception as e:
                        print(f"   ⚠️  Errore estrazione contenuto: {e}")
                    
                    # Torna indietro
                    driver.back()
                    time.sleep(3)
                    
                except Exception as e:
                    print(f"   ⚠️  Errore apertura circolare: {e}")
                    # Usa il testo della riga come contenuto
                    contenuto_completo = testo_riga
                
                # SALVA NEL DATABASE
                data_pubblica_db = data_circolare.strftime("%Y-%m-%d %H:%M:%S")
                
                if salva_circolare_db(titolo, contenuto_completo, data_pubblica_db):
                    print(f"   💾 Data pubblicazione: {data_pubblica_db[:10]}")
                else:
                    print("   ⚠️  Saltata (già presente)")
                    
            else:
                print("   ⚠️  Data non trovata, salto questa circolare")
                
        except Exception as e:
            print(f"   ❌ Errore elaborazione: {e}")
            continue
    
    print(f"\n{'='*60}")
    print(f"🎉 ELABORAZIONE COMPLETATA!")
    print(f"   • Circolari trovate: {len(circolari_trovate)}")
    print(f"   • Database PostgreSQL aggiornato")

except Exception as e:
    print(f"\n❌ ERRORE CRITICO: {e}")
    import traceback
    traceback.print_exc()
    
    # Fa screenshot dell'errore
    try:
        driver.save_screenshot("errore_finale.png")
        print("📸 Screenshot errore salvato come 'errore_finale.png'")
    except:
        pass

finally:
    # --- PULIZIA FINALE ---
    print("\n🧹 Pulizia finale...")
    
    # Chiudi database
    try:
        cur.close()
        conn.close()
        print("   🔒 Connessione database chiusa")
    except:
        pass
    
    # Chiudi browser
    try:
        driver.quit()
        print("   🔒 Browser chiuso")
    except:
        pass
    
    # Pulisci cartella download
    try:
        files = glob.glob(os.path.join(cartella_download, "*"))
        for f in files:
            try:
                os.remove(f)
            except:
                pass
        if os.path.exists(cartella_download):
            os.rmdir(cartella_download)
        print("   🗑️  Cartella temporanea pulita")
    except:
        pass

print("\n✅ Robot completato con successo!")
