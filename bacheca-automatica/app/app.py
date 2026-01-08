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
    if url and key:
        return create_client(url, key)
    st.error("Configura SUPABASE_URL e SUPABASE_KEY")
    return None

supabase = init_supabase()

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
    except:
        st.info("Caricamento in corso...")