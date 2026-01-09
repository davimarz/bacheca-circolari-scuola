import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta, timezone
import urllib.parse
import os
import re

# Importa configurazione se disponibile
try:
    from config import CONFIG, DATE_FORMATS
    UPDATE_INTERVAL = CONFIG['UPDATE_INTERVAL']
    CIRCOLARI_VALIDITA_GIORNI = CONFIG['CIRCOLARI_VALIDITA_GIORNI']
    SCUOLA_NOME = CONFIG['SCUOLA_NOME']
    APP_NOME = CONFIG['APP_NOME']
    # Nuova variabile per anni scolastici
    ANNI_SCOLASTICI = CONFIG.get('ANNI_SCOLASTICI', ['2024/25', '2025/26', '2026/27'])
    ANNO_SCOLASTICO_DEFAULT = CONFIG.get('ANNO_SCOLASTICO_DEFAULT', '2025/26')
except ImportError:
    # Valori di default se config.py non esiste
    UPDATE_INTERVAL = 30
    CIRCOLARI_VALIDITA_GIORNI = 30
    SCUOLA_NOME = "IC Anna Frank - Agrigento"
    APP_NOME = "Bacheca Circolari"
    ANNI_SCOLASTICI = ['2024/25', '2025/26', '2026/27']
    ANNO_SCOLASTICO_DEFAULT = '2025/26'

st.set_page_config(
    page_title=APP_NOME,
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================================
# NUOVI STILI CON COLORI PASTELLO
# =============================================
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Sfondo principale - Verde menta chiaro */
    .stApp {
        background-color: #f0f9f4;
        font-family: 'Arial', sans-serif;
    }
    
    /* Header principale - Beige pastello */
    .main-header {
        text-align: center;
        padding: 2rem 1rem;
        background: linear-gradient(135deg, #fff9f0 0%, #f5f0e6 100%);
        border-radius: 12px;
        margin-bottom: 1rem;
        color: #5a6c7d;
        border: 1px solid #e8e2d6;
        box-shadow: 0 4px 12px rgba(168, 155, 128, 0.1);
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #4a6572;
    }
    
    .school-info {
        font-size: 1.3rem;
        color: #6a7b8c;
        margin-bottom: 0.5rem;
    }
    
    .author-info {
        font-size: 0.9rem;
        color: #8a9aab;
        font-style: italic;
    }
    
    /* Card circolari - Beige chiaro con bordi arrotondati */
    .circolare-card {
        background-color: #fffefb;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 3px 10px rgba(168, 155, 128, 0.08);
        border-left: 5px solid #a8d8ea;
        border-top: 1px solid #f0e6d8;
        border-right: 1px solid #f0e6d8;
        border-bottom: 1px solid #f0e6d8;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .circolare-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(168, 155, 128, 0.12);
    }
    
    .circolare-header {
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Numero circolare - Turchese pastello */
    .circolare-number {
        font-size: 0.9rem;
        color: #2a7a8c;
        font-weight: 600;
        background-color: #e8f4f8;
        padding: 4px 10px;
        border-radius: 6px;
        border: 1px solid #c8e4f0;
    }
    
    .circolare-date {
        font-size: 0.85rem;
        color: #7a8c9d;
    }
    
    .circolare-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #4a5a6a;
        margin-bottom: 0.8rem;
        line-height: 1.4;
    }
    
    /* Pulsanti documenti - Azzurro pastello */
    .doc-buttons-container {
        display: flex;
        flex-direction: row;
        gap: 8px;
        flex-wrap: wrap;
        align-items: center;
    }
    
    .doc-button {
        background: linear-gradient(135deg, #a8d8ea 0%, #8cc6e0 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        text-decoration: none;
        font-size: 0.85rem;
        font-weight: 500;
        transition: all 0.2s ease;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        white-space: nowrap;
        box-shadow: 0 2px 4px rgba(136, 198, 224, 0.2);
    }
    
    .doc-button:hover {
        background: linear-gradient(135deg, #8cc6e0 0%, #6ab4d6 100%);
        color: white;
        text-decoration: none;
        box-shadow: 0 3px 6px rgba(136, 198, 224, 0.3);
        transform: translateY(-1px);
    }
    
    /* Contenitore superiore - Beige pastello */
    .top-container {
        background-color: #fff9f0;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1.5rem;
        border: 1px solid #e8e2d6;
        box-shadow: 0 3px 8px rgba(168, 155, 128, 0.08);
    }
    
    .update-info-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        flex-wrap: wrap;
        gap: 15px;
    }
    
    .update-info {
        background-color: #e8f4f8;
        border-radius: 8px;
        padding: 10px 16px;
        font-size: 0.95rem;
        color: #2a7a8c;
        display: flex;
        align-items: center;
        gap: 8px;
        border: 1px solid #c8e4f0;
        font-weight: 500;
    }
    
    .anno-scolastico-container {
        display: flex;
        align-items: center;
        gap: 8px;
        background-color: #fff;
        padding: 6px 12px;
        border-radius: 8px;
        border: 1px solid #d8e2e8;
    }
    
    .anno-label {
        font-size: 0.9rem;
        color: #5a6c7d;
        font-weight: 500;
    }
    
    .anno-select {
        padding: 6px 10px;
        border: 1px solid #c8d8e0;
        border-radius: 6px;
        background-color: white;
        color: #4a5a6a;
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        min-width: 100px;
    }
    
    /* Barra di ricerca - Stessa riga */
    .search-row {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
        margin-top: 0.5rem;
    }
    
    .search-container {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-grow: 1;
        max-width: 600px;
    }
    
    .search-input {
        padding: 8px 14px;
        border: 1px solid #d8e2e8;
        border-radius: 8px;
        font-size: 0.95rem;
        flex-grow: 1;
        background-color: white;
        color: #4a5a6a;
        transition: border-color 0.2s;
    }
    
    .search-input:focus {
        outline: none;
        border-color: #a8d8ea;
        box-shadow: 0 0 0 2px rgba(168, 216, 234, 0.2);
    }
    
    .search-button {
        background: linear-gradient(135deg, #a8d8ea 0%, #8cc6e0 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 18px;
        font-size: 0.95rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        white-space: nowrap;
        box-shadow: 0 2px 4px rgba(136, 198, 224, 0.2);
    }
    
    .search-button:hover {
        background: linear-gradient(135deg, #8cc6e0 0%, #6ab4d6 100%);
        box-shadow: 0 3px 6px rgba(136, 198, 224, 0.3);
        transform: translateY(-1px);
    }
    
    .clear-search {
        background: linear-gradient(135deg, #f8a8b8 0%, #f58ca0 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 18px;
        font-size: 0.95rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        white-space: nowrap;
        box-shadow: 0 2px 4px rgba(245, 140, 160, 0.2);
    }
    
    .clear-search:hover {
        background: linear-gradient(135deg, #f58ca0 0%, #f27088 100%);
        box-shadow: 0 3px 6px rgba(245, 140, 160, 0.3);
        transform: translateY(-1px);
    }
    
    /* Badge - Rosa pastello per NUOVA, Grigio per ARCHIVIO */
    .badge {
        font-size: 0.7rem;
        padding: 3px 8px;
        border-radius: 6px;
        margin-left: 8px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    
    .badge-new {
        background: linear-gradient(135deg, #f8a8b8 0%, #f58ca0 100%);
        color: white;
        box-shadow: 0 2px 4px rgba(245, 140, 160, 0.2);
    }
    
    .badge-old {
        background: linear-gradient(135deg, #c8d8e0 0%, #b0c4d0 100%);
        color: white;
        box-shadow: 0 2px 4px rgba(176, 196, 208, 0.2);
    }
    
    .empty-state {
        text-align: center;
        padding: 3rem;
        color: #8a9aab;
        background-color: #fffefb;
        border-radius: 12px;
        border: 1px solid #e8e2d6;
        margin-top: 1rem;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        margin-top: 3rem;
        padding: 1.5rem;
        color: #8a9aab;
        font-size: 0.85rem;
        border-top: 1px solid #e8e2d6;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================
# FUNZIONI UTILI - CORRETTE PER TIMEZONE
# =============================================

def get_anno_scolastico_dates(anno_scolastico):
    """
    Restituisce le date di inizio e fine per un anno scolastico.
    Formato anno_scolastico: '2024/25'
    Ritorna date con timezone UTC per compatibilità
    """
    try:
        anno_inizio = int(anno_scolastico.split('/')[0])
        # Inizio: 1 settembre dell'anno di inizio
        data_inizio = datetime(anno_inizio, 9, 1)
        # Fine: 31 agosto dell'anno successivo (anno_inizio + 1)
        data_fine = datetime(anno_inizio + 1, 8, 31)
        
        # Converti in UTC timezone per compatibilità
        data_inizio_utc = data_inizio.replace(tzinfo=timezone.utc)
        data_fine_utc = data_fine.replace(tzinfo=timezone.utc)
        
        return data_inizio_utc, data_fine_utc
    except:
        # Fallback: anno corrente con UTC
        anno_corrente = datetime.now().year
        data_inizio = datetime(anno_corrente, 9, 1).replace(tzinfo=timezone.utc)
        data_fine = datetime(anno_corrente + 1, 8, 31).replace(tzinfo=timezone.utc)
        return data_inizio, data_fine

def normalize_date(date_obj):
    """
    Normalizza una data: se ha timezone la converte in UTC, 
    se non ha timezone le aggiunge UTC
    """
    if date_obj is None:
        return datetime.now(timezone.utc)
    
    if hasattr(date_obj, 'tzinfo'):
        if date_obj.tzinfo is None:
            # Date naive, aggiungi UTC
            return date_obj.replace(tzinfo=timezone.utc)
        else:
            # Date con timezone, converte in UTC
            return date_obj.astimezone(timezone.utc)
    else:
        # Non è un datetime, prova a convertire
        try:
            return pd.to_datetime(date_obj).replace(tzinfo=timezone.utc)
        except:
            return datetime.now(timezone.utc)

def extract_circolare_number(titolo):
    if isinstance(titolo, str):
        titolo_pulito = str(titolo).strip()
        match = re.search(r'N\.?\s*(\d+)', titolo_pulito, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except:
                return 0
    return 0

def safe_convert_to_local_date(timestamp):
    """
    Converte in modo sicuro un pandas Timestamp o datetime in data locale
    """
    try:
        if hasattr(timestamp, 'strftime'):
            # Rimuove timezone per la visualizzazione
            if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is not None:
                timestamp = timestamp.replace(tzinfo=None)
            return timestamp
        else:
            return datetime.now()
    except Exception:
        return datetime.now()

# =============================================
# HEADER PRINCIPALE
# =============================================
st.markdown(f"""
<div class="main-header">
    <div class="main-title">🏫 {APP_NOME}</div>
    <div class="school-info">{SCUOLA_NOME}</div>
    <div class="author-info">realizzato da: Davide prof. Marziano</div>
</div>
""", unsafe_allow_html=True)

# =============================================
# INIZIALIZZAZIONE SESSION STATE
# =============================================
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now(timezone.utc)

if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

if 'anno_scolastico_selezionato' not in st.session_state:
    # Default: anno configurato
    st.session_state.anno_scolastico_selezionato = ANNO_SCOLASTICO_DEFAULT

# =============================================
# CONTENITORE SUPERIORE CON CONTROLLI
# =============================================
st.markdown('<div class="top-container">', unsafe_allow_html=True)

# Prima riga: Contatore aggiornamento + Selettore anno scolastico
tempo_trascorso = (datetime.now(timezone.utc) - st.session_state.last_update).seconds / 60
tempo_rimanente = max(0, UPDATE_INTERVAL - int(tempo_trascorso))

# Crea opzioni per il dropdown anni scolastici
anno_options_html = ""
for anno in ANNI_SCOLASTICI:
    selected = "selected" if st.session_state.anno_scolastico_selezionato == anno else ""
    anno_options_html += f'<option value="{anno}" {selected}>{anno}</option>'

st.markdown(f"""
<div class="update-info-row">
    <div class="update-info">
        🔄 Prossimo aggiornamento automatico tra: <strong>{tempo_rimanente} minuti</strong>
    </div>
    
    <div class="anno-scolastico-container">
        <span class="anno-label">Anno Scolastico:</span>
        <select id="annoSelect" class="anno-select" onchange="cambiaAnnoScolastico()">
            {anno_options_html}
        </select>
    </div>
</div>
""", unsafe_allow_html=True)

# Seconda riga: Barra di ricerca
search_value = st.session_state.search_query if 'search_query' in st.session_state else ""
st.markdown(f"""
<div class="search-row">
    <div class="search-container">
        <input type="text" id="searchInput" class="search-input" placeholder="Cerca per numero o testo..." value="{search_value}" onkeydown="if(event.keyCode==13) searchCircolari()">
        <button class="search-button" onclick="searchCircolari()">🔍 Cerca</button>
        <button class="clear-search" onclick="clearSearch()">❌ Cancella</button>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # Chiusura top-container

# =============================================
# JAVASCRIPT PER INTERAZIONI
# =============================================
st.markdown("""
<script>
function searchCircolari() {
    var searchInput = document.getElementById('searchInput');
    var query = searchInput.value;
    
    if (query.trim() !== '') {
        // Mantieni anche l'anno scolastico nell'URL
        var currentUrl = new URL(window.location);
        currentUrl.searchParams.set('search', query);
        window.location.href = currentUrl.toString();
    }
}

function clearSearch() {
    // Rimuovi solo il parametro search, mantieni anno scolastico
    var currentUrl = new URL(window.location);
    currentUrl.searchParams.delete('search');
    window.location.href = currentUrl.toString();
}

function cambiaAnnoScolastico() {
    var select = document.getElementById('annoSelect');
    var annoSelezionato = select.value;
    
    // Aggiungi l'anno scolastico come parametro URL
    var url = new URL(window.location);
    url.searchParams.set('anno', annoSelezionato);
    // Rimuovi la ricerca quando cambi anno
    url.searchParams.delete('search');
    window.location.href = url.toString();
}
</script>
""", unsafe_allow_html=True)

# =============================================
# GESTIONE PARAMETRI URL
# =============================================
query_params = st.query_params

# Gestione anno scolastico
if 'anno' in query_params:
    anno_url = query_params['anno']
    if anno_url in ANNI_SCOLASTICI:
        st.session_state.anno_scolastico_selezionato = anno_url

# Gestione ricerca
if 'search' in query_params:
    st.session_state.search_query = query_params['search']

# =============================================
# CONNESSIONE AL DATABASE E FILTRI - VERSIONE CORRETTA
# =============================================
@st.cache_resource
def init_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        st.error("❌ Configura SUPABASE_URL e SUPABASE_KEY")
        return None
    
    if not url.startswith("https://"):
        st.error("❌ URL deve iniziare con https://")
        return None
    
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Errore connessione Supabase: {str(e)}")
        return None

supabase = init_supabase()

if supabase:
    try:
        # Ottieni date per l'anno scolastico selezionato (in UTC)
        data_inizio_anno, data_fine_anno = get_anno_scolastico_dates(
            st.session_state.anno_scolastico_selezionato
        )
        
        # Carica TUTTE le circolari
        response = supabase.table('circolari')\
            .select("*")\
            .execute()
        
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            # Identifica colonna data
            colonna_data = None
            possibili_nomi = ['data_pubblicazione', 'data_publicazione', 'data_pubblica', 'data']
            
            for nome in possibili_nomi:
                if nome in df.columns:
                    colonna_data = nome
                    break
            
            if colonna_data:
                # Converti in datetime con timezone UTC
                df['data_pubblicazione'] = pd.to_datetime(df[colonna_data], utc=True)
            else:
                # Se non trova colonna data, usa oggi come fallback
                df['data_pubblicazione'] = pd.to_datetime(datetime.now(timezone.utc))
            
            # Estrai numero circolare
            df['numero_circolare'] = df['titolo'].apply(extract_circolare_number)
            
            # CORREZIONE CRITICA: Normalizza tutte le date in UTC
            # Assicurati che tutte le date in df siano in UTC
            df['data_pubblicazione'] = df['data_pubblicazione'].apply(
                lambda x: normalize_date(x) if pd.notna(x) else datetime.now(timezone.utc)
            )
            
            # FILTRO ANNO SCOLASTICO: mantieni solo circolari tra 1 settembre e 31 agosto
            # Tutte le date ora sono in UTC
            df_filtered_by_year = df[
                (df['data_pubblicazione'] >= data_inizio_anno) & 
                (df['data_pubblicazione'] <= data_fine_anno)
            ].copy()
            
            # FILTRO RICERCA
            if st.session_state.search_query:
                query = st.session_state.search_query.lower()
                
                def matches_search(row):
                    titolo = str(row['titolo']).lower()
                    numero = str(row['numero_circolare'])
                    
                    if query.isdigit():
                        return query in str(numero)
                    else:
                        return query in titolo
                
                df_filtered = df_filtered_by_year[df_filtered_by_year.apply(matches_search, axis=1)]
                
                if df_filtered.empty:
                    st.info(f"🔍 Nessuna circolare trovata per: '{st.session_state.search_query}'")
                    df_display = df_filtered_by_year
                else:
                    st.info(f"🔍 Risultati per: '{st.session_state.search_query}' ({len(df_filtered)} circolari trovate)")
                    df_display = df_filtered
            else:
                df_display = df_filtered_by_year
            
            # VISUALIZZAZIONE CIRCOLARI
            if not df_display.empty:
                df_display = df_display.sort_values('numero_circolare', ascending=False)
                
                for idx, row in df_display.iterrows():
                    data_pub = row['data_pubblicazione']
                    oggi_utc = datetime.now(timezone.utc)
                    
                    # Determina se è nuova (< 7 giorni)
                    # Assicurati che entrambe le date siano in UTC
                    if hasattr(data_pub, 'tzinfo') and data_pub.tzinfo is not None:
                        diff_giorni = (oggi_utc - data_pub).days
                    else:
                        data_pub_utc = normalize_date(data_pub)
                        diff_giorni = (oggi_utc - data_pub_utc).days
                    
                    is_new = diff_giorni < 7
                    
                    data_pub_safe = safe_convert_to_local_date(data_pub)
                    
                    badge_html = f'<span class="badge badge-{"new" if is_new else "old"}">{"NUOVA" if is_new else "ARCHIVIO"}</span>'
                    
                    numero_html = ""
                    if row['numero_circolare'] > 0:
                        numero_html = f'<span class="circolare-number">N.{row["numero_circolare"]}</span>'
                    
                    titolo_pulito = str(row['titolo']).strip()
                    
                    card_html = f'''
                    <div class="circolare-card">
                        <div class="circolare-header">
                            {numero_html}
                            <span class="circolare-date">📅 Pubblicata il {data_pub_safe.strftime('%d/%m/%Y')}</span>
                        </div>
                        <div class="circolare-title">
                            {titolo_pulito} {badge_html}
                        </div>
                    '''
                    
                    if 'pdf_url' in row and pd.notna(row['pdf_url']) and str(row['pdf_url']).strip():
                        urls = str(row['pdf_url']).split(';;;')
                        valid_urls = [url.strip() for url in urls if url.strip()]
                        
                        if valid_urls:
                            card_html += '<div class="doc-buttons-container">'
                            
                            for i, url in enumerate(valid_urls):
                                base = os.environ.get("SUPABASE_URL", "").rstrip('/')
                                if url and not url.startswith('http'):
                                    url = f"{base}/storage/v1/object/public/documenti/{urllib.parse.quote(url)}"
                                
                                if url:
                                    card_html += f'<a href="{url}" target="_blank" class="doc-button">📄 Documento {i+1}</a>'
                            
                            card_html += '</div>'
                    
                    card_html += '</div>'
                    st.markdown(card_html, unsafe_allow_html=True)
            else:
                # Messaggio quando non ci sono circolari
                st.markdown(f'''
                <div class="empty-state">
                    <h3 style="color: #8a9aab; margin-bottom: 1rem;">📭 Nessuna circolare disponibile</h3>
                    <p style="color: #a8b8c8;">
                        Per l'anno scolastico <strong>{st.session_state.anno_scolastico_selezionato}</strong><br>
                        (periodo: {data_inizio_anno.strftime('%d/%m/%Y')} - {data_fine_anno.strftime('%d/%m/%Y')})
                    </p>
                </div>
                ''', unsafe_allow_html=True)
        
        else:
            # Database vuoto
            st.markdown(f'''
            <div class="empty-state">
                <h3 style="color: #8a9aab; margin-bottom: 1rem;">📭 Database vuoto</h3>
                <p style="color: #a8b8c8;">
                    Non ci sono circolari nel database per nessun anno scolastico.<br>
                    Controlla che il robot di scraping sia configurato correttamente.
                </p>
            </div>
            ''', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"❌ Errore nel caricamento dei dati: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
else:
    st.warning("⚠️ Impossibile connettersi al database.")

# =============================================
# FOOTER
# =============================================
st.markdown(f"""
<div class="footer">
    <hr style="border: none; height: 1px; background-color: #e8e2d6; margin: 1rem 0;">
    {APP_NOME} - {SCUOLA_NOME}<br>
    <small>Anno scolastico: {st.session_state.anno_scolastico_selezionato}</small>
</div>
""", unsafe_allow_html=True)
