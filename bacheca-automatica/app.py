import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import urllib.parse
import os

# Configurazione
st.set_page_config(
    page_title="Bacheca Circolari",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .main-header {text-align: center; padding-bottom: 1rem;}
    .main-title {font-size: 2rem; font-weight: 700; color: #1a1a1a;}
    .school-info {font-size: 1.3rem; color: #2c5282; font-weight: 500;}
    .author-info {font-size: 0.9rem; color: #718096; font-style: italic;}
    .update-info {font-size: 0.7rem; color: #a0aec0;}
    .pdf-button {
        background-color: #4299e1; color: white; border: none; border-radius: 4px;
        padding: 6px 12px; text-decoration: none; display: inline-block; margin: 2px;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <div class="main-title">🏫 Bacheca Circolari</div>
    <div class="school-info">IC Anna Frank - Agrigento</div>
    <div class="author-info">realizzato da: Davide prof. Marziano</div>
</div>
""", unsafe_allow_html=True)

# Connessione Supabase
@st.cache_resource
def init_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    # Debug: mostra se le variabili esistono (rimuovi in produzione)
    debug_mode = os.environ.get("DEBUG", "false").lower() == "true"
    if debug_mode:
        st.write("DEBUG - SUPABASE_URL presente:", "SI" if url else "NO")
        if url:
            st.write("DEBUG - URL inizia con https://:", url.startswith("https://"))
    
    if not url or not key:
        st.error("❌ Configura SUPABASE_URL e SUPABASE_KEY nelle variabili d'ambiente")
        return None
    
    if not url.startswith("https://"):
        st.error("❌ SUPABASE_URL deve iniziare con https://")
        return None
    
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Errore connessione Supabase: {str(e)}")
        return None

supabase = init_supabase()

# Debug info (rimuovi in produzione)
debug_mode = os.environ.get("DEBUG", "false").lower() == "true"
if debug_mode and supabase is None:
    st.write("DEBUG - Variabili ambiente:")
    st.write("- SUPABASE_URL:", os.environ.get("SUPABASE_URL", "Non impostato"))
    supabase_key = os.environ.get("SUPABASE_KEY")
    if supabase_key:
        st.write("- SUPABASE_KEY:", "***" + supabase_key[-4:])
    else:
        st.write("- SUPABASE_KEY: Non impostato")

# Carica dati
if supabase:
    try:
        response = supabase.table('circolari').select("*").order('id', desc=True).execute()
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            latest = pd.to_datetime(df['data_pubblicazione']).max()
            st.markdown(f'<div class="update-info">Ultimo aggiornamento: {latest.strftime("%d/%m/%Y %H:%M")}</div>', unsafe_allow_html=True)
            
            for _, row in df.iterrows():
                st.markdown(f"**{row['titolo']}**")
                if 'contenuto' in row and pd.notna(row['contenuto']):
                    st.caption(row['contenuto'])
                
                if 'pdf_url' in row and pd.notna(row['pdf_url']):
                    urls = str(row['pdf_url']).split(';;;')
                    for i, url in enumerate(urls):
                        if url.strip():
                            base = os.environ.get("SUPABASE_URL", "").rstrip('/')
                            if not url.startswith('http'):
                                url = f"{base}/storage/v1/object/public/documenti/{urllib.parse.quote(url)}"
                            st.markdown(f'<a href="{url}" target="_blank" class="pdf-button">📄 Documento {i+1}</a>', unsafe_allow_html=True)
                
                st.markdown("---")
        else:
            st.info("📭 Nessuna circolare presente")
    except Exception as e:
        st.error(f"❌ Errore nel caricamento dei dati: {str(e)}")
else:
    st.warning("⚠️ Impossibile connettersi al database. Controlla le configurazioni.")
