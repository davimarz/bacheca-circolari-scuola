import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta, timezone
import urllib.parse
import os
import re

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
        background-color: #f8f9fa;
        font-family: 'Arial', sans-serif;
    }
    
    .main-header {
        text-align: center;
        padding: 2rem 1rem;
        background-color: #2c3e50;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: white;
    }
    
    .school-info {
        font-size: 1.3rem;
        color: #ecf0f1;
        margin-bottom: 0.5rem;
    }
    
    .author-info {
        font-size: 0.9rem;
        color: #bdc3c7;
        font-style: italic;
    }
    
    .circolare-card {
        background-color: white;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 4px solid #3498db;
    }
    
    .circolare-header {
        margin-bottom: 0.5rem;
    }
    
    .circolare-number {
        font-size: 0.9rem;
        color: #3498db;
        font-weight: 600;
        margin-right: 10px;
        display: inline-block;
    }
    
    .circolare-date {
        font-size: 0.85rem;
        color: #7f8c8d;
        display: inline-block;
    }
    
    .circolare-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 0.8rem;
        line-height: 1.4;
    }
    
    .doc-buttons-container {
        display: flex;
        flex-direction: row;
        gap: 8px;
        flex-wrap: wrap;
    }
    
    .doc-button {
        background-color: #27ae60;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        text-decoration: none;
        font-size: 0.85rem;
        font-weight: 500;
        transition: background-color 0.2s;
        display: inline-block;
    }
    
    .doc-button:hover {
        background-color: #229954;
        color: white;
        text-decoration: none;
    }
    
    .update-info {
        background-color: #ecf0f1;
        border-radius: 6px;
        padding: 0.8rem;
        margin-bottom: 1.5rem;
        text-align: center;
        font-size: 0.9rem;
        color: #2c3e50;
    }
    
    .badge {
        font-size: 0.7rem;
        padding: 2px 6px;
        border-radius: 3px;
        margin-left: 8px;
    }
    
    .badge-new {
        background-color: #2ecc71;
        color: white;
    }
    
    .badge-old {
        background-color: #95a5a6;
        color: white;
    }
    
    .empty-state {
        text-align: center;
        padding: 3rem;
        color: #7f8c8d;
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

def extract_circolare_number(titolo):
    if isinstance(titolo, str):
        match = re.search(r'N\.?\s*(\d+)', titolo, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0

if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now(timezone.utc)

tempo_trascorso = (datetime.now(timezone.utc) - st.session_state.last_update).seconds / 60
tempo_rimanente = max(0, 30 - int(tempo_trascorso))

st.markdown(f"""
<div class="update-info">
    🔄 Prossimo aggiornamento automatico tra: <strong>{tempo_rimanente} minuti</strong>
</div>
""", unsafe_allow_html=True)

supabase = init_supabase()

if supabase:
    try:
        inizio_anno_scolastico = datetime(2025, 9, 1, tzinfo=timezone.utc)
        
        response = supabase.table('circolari')\
            .select("*")\
            .gte('data_pubblicazione', inizio_anno_scolastico.isoformat())\
            .execute()
        
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            df['data_pubblicazione'] = pd.to_datetime(df['data_pubblicazione'], utc=True)
            df['numero_circolare'] = df['titolo'].apply(extract_circolare_number)
            
            df = df.sort_values(['data_pubblicazione', 'numero_circolare'], ascending=[False, False])
            
            oggi = datetime.now(timezone.utc)
            
            for idx, row in df.iterrows():
                data_pub = row['data_pubblicazione']
                is_new = (oggi - data_pub).days < 7
                data_pub_local = data_pub.astimezone(timezone(timedelta(hours=1)))
                
                badge_html = f'<span class="badge badge-{"new" if is_new else "old"}">{"NUOVA" if is_new else "ARCHIVIO"}</span>'
                
                numero_html = ""
                if row['numero_circolare'] > 0:
                    numero_html = f'<span class="circolare-number">N.{row["numero_circolare"]}</span>'
                
                st.markdown(f"""
                <div class="circolare-card">
                    <div class="circolare-header">
                        {numero_html}
                        <span class="circolare-date">
                            📅 Pubblicata il {data_pub_local.strftime('%d/%m/%Y')}
                        </span>
                    </div>
                    <div class="circolare-title">
                        {row['titolo']} {badge_html}
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
                                f'📄 Documento {i+1}</a>',
                                unsafe_allow_html=True
                            )
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('</div>')
        
        else:
            st.markdown('<div class="empty-state">📭 Nessuna circolare presente</div>', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"❌ Errore nel caricamento dei dati: {str(e)}")
else:
    st.warning("⚠️ Impossibile connettersi al database.")

st.markdown("""
<div style="text-align: center; margin-top: 3rem; padding: 1rem; color: #7f8c8d; font-size: 0.8rem;">
    <hr style="border: none; height: 1px; background-color: #bdc3c7; margin: 1rem 0;">
    Bacheca Circolari IC Anna Frank - Agrigento
</div>
""", unsafe_allow_html=True)
