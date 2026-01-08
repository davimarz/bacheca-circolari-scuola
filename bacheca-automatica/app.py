import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta, timezone
import urllib.parse
import os
import hashlib
import json

# ============================================
# CONFIGURAZIONE E STILE
# ============================================

st.set_page_config(
    page_title="Bacheca Circolari",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS con colori pastello e stile migliorato
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Sfondo e container principale */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4edf5 100%);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Header principale */
    .main-header {
        text-align: center;
        padding: 2rem 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        color: white;
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 1%, transparent 1%);
        background-size: 20px 20px;
        opacity: 0.3;
    }
    
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        letter-spacing: 1px;
    }
    
    .school-info {
        font-size: 1.5rem;
        font-weight: 500;
        opacity: 0.95;
        margin-bottom: 0.5rem;
    }
    
    .author-info {
        font-size: 1rem;
        font-style: italic;
        opacity: 0.85;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255,255,255,0.2);
    }
    
    /* Card circolare */
    .circolare-card {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 6px 20px rgba(0,0,0,0.08);
        border-left: 6px solid #764ba2;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        position: relative;
    }
    
    .circolare-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 25px rgba(0,0,0,0.12);
    }
    
    .circolare-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #2d3748;
        margin-bottom: 0.8rem;
        line-height: 1.3;
    }
    
    .circolare-content {
        font-size: 1.1rem;
        color: #4a5568;
        line-height: 1.6;
        margin-bottom: 1.2rem;
        padding-right: 50px;
    }
    
    .circolare-date {
        font-size: 0.9rem;
        color: #a0aec0;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Pulsanti documenti */
    .doc-buttons-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 1rem;
    }
    
    .doc-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 8px 20px;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    
    .doc-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(102, 126, 234, 0.4);
        color: white;
        text-decoration: none;
    }
    
    /* Pulsante condividi */
    .share-button {
        position: absolute;
        top: 1.5rem;
        right: 1.5rem;
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        border: none;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(240, 147, 251, 0.3);
    }
    
    .share-button:hover {
        transform: scale(1.1) rotate(15deg);
        box-shadow: 0 6px 15px rgba(240, 147, 251, 0.5);
    }
    
    /* Info aggiornamento */
    .update-info {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 2rem;
        text-align: center;
        font-weight: 600;
        color: #2d3748;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid rgba(255,255,255,0.5);
    }
    
    /* Messaggi di stato */
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        background: white;
        border-radius: 15px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.08);
    }
    
    .empty-state-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
        opacity: 0.3;
    }
    
    .empty-state-text {
        font-size: 1.3rem;
        color: #a0aec0;
        font-weight: 500;
    }
    
    /* Badge */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 10px;
    }
    
    .badge-new {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
    }
    
    .badge-old {
        background: linear-gradient(135deg, #ff9a9e 0%, #fad0c4 100%);
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================
# HEADER
# ============================================

st.markdown("""
<div class="main-header">
    <div class="main-title">🏫 Bacheca Circolari</div>
    <div class="school-info">IC Anna Frank - Agrigento</div>
    <div class="author-info">realizzato da: Davide prof. Marziano</div>
</div>
""", unsafe_allow_html=True)

# ============================================
# FUNZIONI
# ============================================

@st.cache_resource
def init_supabase():
    """Inizializza connessione a Supabase"""
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

def is_circolare_scaduta(data_pubblicazione, giorni_scadenza=30):
    """Controlla se una circolare è scaduta - VERSIONE CORRETTA"""
    if isinstance(data_pubblicazione, str):
        data_pubblicazione = pd.to_datetime(data_pubblicazione)
    
    # Data limite in UTC (aware)
    data_limite = datetime.now(timezone.utc) - timedelta(days=giorni_scadenza)
    
    # Se la data di pubblicazione è naive (senza timezone)
    if data_pubblicazione.tzinfo is None:
        # Converti in aware con UTC
        data_pubblicazione = data_pubblicazione.replace(tzinfo=timezone.utc)
    
    # Confronto tra datetime entrambi aware
    return data_pubblicazione < data_limite

def scarica_circolari_dal_sito():
    """
    Simula lo scaricamento delle circolari dal sito della scuola
    DA MODIFICARE con la logica reale di scraping
    """
    try:
        # URL del sito della scuola (DA MODIFICARE)
        url_scuola = "https://www.icannafrankag.edu.it/circolari"  # ESEMPIO
        
        # Simulazione di dati (sostituire con scraping reale)
        circolari_mock = [
            {
                "titolo": "Avviso riunione docenti",
                "contenuto": "Si comunica che giorno 15 gennaio si terrà la riunione di tutti i docenti.",
                "data_pubblicazione": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "pdf_url": "circolare_001.pdf;;;allegato_001.pdf"
            },
            {
                "titolo": "Gita scolastica a Roma",
                "contenuto": "Informazioni sulla gita programmata per il mese di marzo.",
                "data_pubblicazione": (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),
                "pdf_url": "gita_roma.pdf"
            }
        ]
        
        return circolari_mock
        
    except Exception as e:
        st.error(f"Errore nel caricamento circolari: {str(e)}")
        return []

@st.cache_data(ttl=1800)  # Cache per 30 minuti
def aggiorna_database_automaticamente():
    """
    Controlla se ci sono nuove circolari e aggiorna il database
    Elimina quelle vecchie di oltre 30 giorni
    """
    supabase = init_supabase()
    if not supabase:
        return 0
    
    try:
        # 1. Scarica nuove circolari dal sito
        nuove_circolari = scarica_circolari_dal_sito()
        
        # 2. Recupera circolari esistenti
        response = supabase.table('circolari').select("*").execute()
        circolari_esistenti = response.data if response.data else []
        
        # 3. Calcola hash per confronto
        nuovi_hash = []
        for circ in nuove_circolari:
            contenuto_hash = hashlib.md5(
                f"{circ['titolo']}_{circ['contenuto']}".encode()
            ).hexdigest()
            circ['hash'] = contenuto_hash
            nuovi_hash.append(contenuto_hash)
        
        # 4. Aggiungi solo le nuove
        nuove_aggiunte = 0
        for circ in nuove_circolari:
            if circ['hash'] not in [c.get('hash', '') for c in circolari_esistenti]:
                # Rimuovi hash prima di salvare
                circ_senza_hash = {k: v for k, v in circ.items() if k != 'hash'}
                supabase.table('circolari').insert(circ_senza_hash).execute()
                nuove_aggiunte += 1
        
        # 5. Elimina circolari vecchie di oltre 30 giorni
        circolari_eliminate = 0
        for circ in circolari_esistenti:
            if is_circolare_scaduta(circ['data_pubblicazione']):
                supabase.table('circolari').delete().eq('id', circ['id']).execute()
                circolari_eliminate += 1
        
        return nuove_aggiunte
        
    except Exception as e:
        st.error(f"Errore aggiornamento automatico: {str(e)}")
        return 0

def genera_codice_condivisione(titolo, contenuto):
    """Genera codice per condividere una circolare"""
    import base64
    data = f"📌 {titolo}\n\n{contenuto}\n\n👉 Visualizza su Bacheca Circolari"
    encoded = base64.b64encode(data.encode()).decode()
    return f"data:text/plain;base64,{encoded}"

# ============================================
# LOGICA PRINCIPALE
# ============================================

# Inizializza Supabase
supabase = init_supabase()

# Inizializza session state per l'aggiornamento
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now(timezone.utc)

# Sidebar per controlli
with st.sidebar:
    st.title("⚙️ Controlli")
    
    if st.button("🔄 Aggiorna manualmente", use_container_width=True):
        with st.spinner("Aggiornamento in corso..."):
            nuove = aggiorna_database_automaticamente()
            if nuove > 0:
                st.success(f"Trovate {nuove} nuove circolari!")
            else:
                st.info("Nessuna nuova circolare trovata")
            st.session_state.last_update = datetime.now(timezone.utc)
            st.rerun()
    
    st.markdown("---")
    st.markdown("**📊 Statistiche**")
    
    # Calcola tempo trascorso dall'ultimo aggiornamento
    tempo_trascorso = (datetime.now(timezone.utc) - st.session_state.last_update).seconds / 60
    
    # Auto-aggiornamento ogni 30 minuti
    if tempo_trascorso > 30:  # 30 minuti
        with st.spinner("Auto-aggiornamento..."):
            nuove = aggiorna_database_automaticamente()
            st.session_state.last_update = datetime.now(timezone.utc)
            if nuove > 0:
                st.info(f"Auto-aggiornate {nuove} circolari")
            st.rerun()

# Mostra info aggiornamento
tempo_rimanente = max(0, 30 - int(tempo_trascorso))
st.markdown(f"""
<div class="update-info">
    🔄 Prossimo aggiornamento automatico tra: <strong>{tempo_rimanente} minuti</strong>
    <br><small>Ultimo aggiornamento: {st.session_state.last_update.astimezone(timezone(timedelta(hours=1))).strftime('%H:%M')}</small>
</div>
""", unsafe_allow_html=True)

# Carica e mostra circolari
if supabase:
    try:
        response = supabase.table('circolari').select("*").order('data_pubblicazione', desc=True).execute()
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            # Converti tutte le date in UTC (assicura che siano aware)
            df['data_pubblicazione'] = pd.to_datetime(df['data_pubblicazione'], utc=True)
            
            # Filtra circolari non scadute
            df = df[~df['data_pubblicazione'].apply(is_circolare_scaduta)]
            
            if df.empty:
                st.markdown("""
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <div class="empty-state-text">Nessuna circolare attiva</div>
                    <p>Le circolari vengono mantenute per 30 giorni dalla pubblicazione.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Mostra ultimo aggiornamento
                latest = df['data_pubblicazione'].max()
                latest_local = latest.astimezone(timezone(timedelta(hours=1)))  # GMT+1
                st.caption(f"📅 Ultimo aggiornamento: {latest_local.strftime('%d/%m/%Y %H:%M')}")
                
                # Mostra ogni circolare
                for idx, row in df.iterrows():
                    # Determina se è nuova (< 7 giorni)
                    data_pub = row['data_pubblicazione']
                    is_new = (datetime.now(timezone.utc) - data_pub).days < 7
                    
                    # Converti data in locale per visualizzazione (GMT+1 per Italia)
                    data_pub_local = data_pub.astimezone(timezone(timedelta(hours=1)))
                    
                    st.markdown(f"""
                    <div class="circolare-card">
                        <div class="circolare-title">
                            {row['titolo']}
                            <span class="badge {'badge-new' if is_new else 'badge-old'}">
                                {'🆕 Nuova' if is_new else '📜 Archivio'}
                            </span>
                        </div>
                        
                        <div class="circolare-date">
                            📅 Pubblicato il: {data_pub_local.strftime('%d/%m/%Y alle %H:%M')}
                        </div>
                        
                        <div class="circolare-content">
                            {row['contenuto'] if pd.notna(row['contenuto']) else ''}
                        </div>
                        
                        <div class="share-button" title="Condividi questa circolare"
                             onclick="navigator.clipboard.writeText(`📌 {row['titolo']}\\n\\n{row['contenuto'] if pd.notna(row['contenuto']) else ''}\\n\\n👉 Visualizza su Bacheca Circolari`)">
                            📤
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Documenti allegati
                    if 'pdf_url' in row and pd.notna(row['pdf_url']):
                        urls = str(row['pdf_url']).split(';;;')
                        valid_urls = [url.strip() for url in urls if url.strip()]
                        
                        if valid_urls:
                            st.markdown('<div class="doc-buttons-container">', unsafe_allow_html=True)
                            
                            for i, url in enumerate(valid_urls):
                                base = os.environ.get("SUPABASE_URL", "").rstrip('/')
                                if not url.startswith('http'):
                                    url = f"{base}/storage/v1/object/public/documenti/{urllib.parse.quote(url)}"
                                
                                st.markdown(
                                    f'<a href="{url}" target="_blank" class="doc-button">'
                                    f'📄 Doc.{i+1}</a>',
                                    unsafe_allow_html=True
                                )
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown("---")
        
        else:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <div class="empty-state-text">Nessuna circolare presente</div>
                <p>Il sistema aggiornerà automaticamente ogni 30 minuti.</p>
            </div>
            """, unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"❌ Errore nel caricamento dei dati: {str(e)}")
else:
    st.warning("⚠️ Impossibile connettersi al database. Controlla le configurazioni.")

# ============================================
# SCRIPT JAVASCRIPT PER CONDIVISIONE
# ============================================

st.markdown("""
<script>
// Funzione per copiare il testo negli appunti
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        // Mostra notifica
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 25px;
            border-radius: 10px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
            z-index: 1000;
            animation: slideIn 0.3s ease;
        `;
        notification.innerHTML = '✅ Copiato negli appunti!';
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 2000);
    });
}

// Aggiungi event listener ai pulsanti di condivisione
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.share-button').forEach(button => {
        button.addEventListener('click', function(e) {
            const card = this.closest('.circolare-card');
            const title = card.querySelector('.circolare-title').textContent.replace('🆕 Nuova', '').replace('📜 Archivio', '').trim();
            const content = card.querySelector('.circolare-content').textContent;
            
            const shareText = `📌 ${title}\\n\\n${content}\\n\\n👉 Visualizza su Bacheca Circolari`;
            copyToClipboard(shareText);
        });
    });
});

// Animazioni CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);
</script>
""", unsafe_allow_html=True)

# ============================================
# PIEDE PAGINA
# ============================================

st.markdown("""
<div style="text-align: center; margin-top: 3rem; padding: 1.5rem; color: #a0aec0; font-size: 0.9rem;">
    <hr style="border: none; height: 1px; background: linear-gradient(90deg, transparent, #667eea, transparent); margin: 1rem 0;">
    🏫 Bacheca Circolari IC Anna Frank - Agrigento • 
    <span id="live-clock">Caricamento...</span> • 
    Aggiornamento automatico ogni 30 minuti
</div>

<script>
// Orologio live
function updateClock() {
    const now = new Date();
    const clock = document.getElementById('live-clock');
    if (clock) {
        clock.textContent = now.toLocaleTimeString('it-IT', { 
            hour: '2-digit', 
            minute: '2-digit',
            second: '2-digit'
        });
    }
}
setInterval(updateClock, 1000);
updateClock();
</script>
""", unsafe_allow_html=True)
