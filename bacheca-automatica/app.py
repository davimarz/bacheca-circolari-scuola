import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta, timezone
import urllib.parse
import os
import hashlib

st.set_page_config(
    page_title="Bacheca Circolari",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4edf5 100%);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
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
    
    .circolare-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 1rem;
    }
    
    .circolare-date {
        font-size: 0.9rem;
        color: #a0aec0;
        background: #f7fafc;
        padding: 4px 12px;
        border-radius: 20px;
        min-width: 140px;
        text-align: center;
        flex-shrink: 0;
        margin-right: 1rem;
    }
    
    .circolare-title-container {
        flex-grow: 1;
    }
    
    .circolare-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #2d3748;
        margin: 0;
        line-height: 1.3;
    }
    
    .share-button-container {
        flex-shrink: 0;
        margin-left: 1rem;
    }
    
    .share-button {
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
    
    .doc-buttons-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 1rem;
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
    
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-left: 10px;
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

st.markdown("""
<div class="main-header">
    <div class="main-title">🏫 Bacheca Circolari</div>
    <div class="school-info">IC Anna Frank - Agrigento</div>
    <div class="author-info">realizzato da: Davide prof. Marziano</div>
</div>
""", unsafe_allow_html=True)

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

def is_circolare_scaduta(data_pubblicazione, giorni_scadenza=30):
    if isinstance(data_pubblicazione, str):
        data_pubblicazione = pd.to_datetime(data_pubblicazione)
    
    data_limite = datetime.now(timezone.utc) - timedelta(days=giorni_scadenza)
    
    if data_pubblicazione.tzinfo is None:
        data_pubblicazione = data_pubblicazione.replace(tzinfo=timezone.utc)
    
    return data_pubblicazione < data_limite

if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now(timezone.utc)

with st.sidebar:
    st.title("⚙️ Controlli")
    
    if st.button("🔄 Aggiorna manualmente", use_container_width=True):
        with st.spinner("Aggiornamento in corso..."):
            st.session_state.last_update = datetime.now(timezone.utc)
            st.rerun()
    
    st.markdown("---")
    st.markdown("**📊 Statistiche**")
    
    tempo_trascorso = (datetime.now(timezone.utc) - st.session_state.last_update).seconds / 60
    
    if tempo_trascorso > 30:
        with st.spinner("Auto-aggiornamento..."):
            st.session_state.last_update = datetime.now(timezone.utc)
            st.rerun()

tempo_rimanente = max(0, 30 - int(tempo_trascorso))
st.markdown(f"""
<div class="update-info">
    🔄 Prossimo aggiornamento automatico tra: <strong>{tempo_rimanente} minuti</strong>
    <br><small>Ultimo aggiornamento: {st.session_state.last_update.astimezone(timezone(timedelta(hours=1))).strftime('%H:%M')}</small>
</div>
""", unsafe_allow_html=True)

supabase = init_supabase()

if supabase:
    try:
        response = supabase.table('circolari').select("*").order('data_pubblicazione', desc=True).execute()
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            df['data_pubblicazione'] = pd.to_datetime(df['data_pubblicazione'], utc=True)
            df = df[~df['data_pubblicazione'].apply(is_circolare_scaduta)]
            
            if df.empty:
                st.markdown("""
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <div class="empty-state-text">Nessuna circolare attiva</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                latest = df['data_pubblicazione'].max()
                latest_local = latest.astimezone(timezone(timedelta(hours=1)))
                st.caption(f"📅 Ultimo aggiornamento: {latest_local.strftime('%d/%m/%Y %H:%M')}")
                
                for idx, row in df.iterrows():
                    data_pub = row['data_pubblicazione']
                    is_new = (datetime.now(timezone.utc) - data_pub).days < 7
                    data_pub_local = data_pub.astimezone(timezone(timedelta(hours=1)))
                    
                    st.markdown(f"""
                    <div class="circolare-card">
                        <div class="circolare-header">
                            <div class="circolare-date">
                                📅 {data_pub_local.strftime('%d/%m/%Y')}
                            </div>
                            <div class="circolare-title-container">
                                <div class="circolare-title">
                                    {row['titolo']}
                                    <span class="badge {'badge-new' if is_new else 'badge-old'}">
                                        {'🆕 Nuova' if is_new else '📜 Archivio'}
                                    </span>
                                </div>
                            </div>
                            <div class="share-button-container">
                                <div class="share-button" title="Condividi questa circolare"
                                     onclick="navigator.clipboard.writeText(`📌 {row['titolo']}\\n\\n👉 Visualizza su Bacheca Circolari`)">
                                    📤
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
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
            </div>
            """, unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"❌ Errore nel caricamento dei dati: {str(e)}")
else:
    st.warning("⚠️ Impossibile connettersi al database.")

st.markdown("""
<script>
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
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

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.share-button').forEach(button => {
        button.addEventListener('click', function(e) {
            const card = this.closest('.circolare-card');
            const title = card.querySelector('.circolare-title').textContent.replace('🆕 Nuova', '').replace('📜 Archivio', '').trim();
            
            const shareText = `📌 ${title}\\n\\n👉 Visualizza su Bacheca Circolari`;
            copyToClipboard(shareText);
        });
    });
});

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

st.markdown("""
<div style="text-align: center; margin-top: 3rem; padding: 1.5rem; color: #a0aec0; font-size: 0.9rem;">
    <hr style="border: none; height: 1px; background: linear-gradient(90deg, transparent, #667eea, transparent); margin: 1rem 0;">
    🏫 Bacheca Circolari IC Anna Frank - Agrigento • 
    <span id="live-clock">Caricamento...</span> • 
    Aggiornamento automatico ogni 30 minuti
</div>

<script>
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
