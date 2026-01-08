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
        margin-bottom: 1rem;
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
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .circolare-number {
        font-size: 0.9rem;
        color: #3498db;
        font-weight: 600;
        background-color: #ecf0f1;
        padding: 2px 8px;
        border-radius: 4px;
    }
    
    .circolare-date {
        font-size: 0.85rem;
        color: #7f8c8d;
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
        align-items: center;
    }
    
    .doc-button {
        background-color: #2c3e50;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        text-decoration: none;
        font-size: 0.85rem;
        font-weight: 500;
        transition: background-color 0.2s;
        display: inline-flex;
        align-items: center;
        gap: 5px;
        white-space: nowrap;
    }
    
    .doc-button:hover {
        background-color: #34495e;
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
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .update-text {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .search-container {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .search-input {
        padding: 6px 12px;
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        font-size: 0.9rem;
        width: 250px;
    }
    
    .search-button {
        background-color: #3498db;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 0.9rem;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    
    .search-button:hover {
        background-color: #2980b9;
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
    
    .clear-search {
        background-color: #e74c3c;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 0.9rem;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    
    .clear-search:hover {
        background-color: #c0392b;
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
        titolo_pulito = str(titolo).strip()
        match = re.search(r'N\.?\s*(\d+)', titolo_pulito, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except:
                return 0
    return 0

if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now(timezone.utc)

if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

tempo_trascorso = (datetime.now(timezone.utc) - st.session_state.last_update).seconds / 60
tempo_rimanente = max(0, 30 - int(tempo_trascorso))

st.markdown(f"""
<div class="update-info">
    <div class="update-text">
        🔄 Prossimo aggiornamento automatico tra: <strong>{tempo_rimanente} minuti</strong>
    </div>
    <div class="search-container">
        <input type="text" id="searchInput" class="search-input" placeholder="Cerca per numero o testo..." value="{st.session_state.search_query}" onkeydown="if(event.keyCode==13) searchCircolari()">
        <button class="search-button" onclick="searchCircolari()">🔍 Cerca</button>
        <button class="clear-search" onclick="clearSearch()">❌ Cancella</button>
    </div>
</div>
""".format(tempo_rimanente=tempo_rimanente), unsafe_allow_html=True)

st.markdown("""
<script>
function searchCircolari() {
    var searchInput = document.getElementById('searchInput');
    var query = searchInput.value;
    
    if (query.trim() !== '') {
        window.location.href = window.location.pathname + '?search=' + encodeURIComponent(query);
    }
}

function clearSearch() {
    window.location.href = window.location.pathname;
}
</script>
""", unsafe_allow_html=True)

query_params = st.query_params
if 'search' in query_params:
    st.session_state.search_query = query_params['search']

supabase = init_supabase()

if supabase:
    try:
        oggi = datetime.now(timezone.utc)
        limite_data = oggi - timedelta(days=30)
        
        response = supabase.table('circolari')\
            .select("*")\
            .gte('data_pubblicazione', limite_data.isoformat())\
            .execute()
        
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            df['data_pubblicazione'] = pd.to_datetime(df['data_pubblicazione'], utc=True)
            df['numero_circolare'] = df['titolo'].apply(extract_circolare_number)
            
            if st.session_state.search_query:
                query = st.session_state.search_query.lower()
                
                def matches_search(row):
                    titolo = str(row['titolo']).lower()
                    numero = str(row['numero_circolare'])
                    
                    if query.isdigit():
                        return query in numero
                    else:
                        return query in titolo
                
                df_filtered = df[df.apply(matches_search, axis=1)]
                
                if df_filtered.empty:
                    st.info(f"🔍 Nessuna circolare trovata per: '{st.session_state.search_query}'")
                    df_display = df
                else:
                    st.info(f"🔍 Risultati per: '{st.session_state.search_query}' ({len(df_filtered)} circolari trovate)")
                    df_display = df_filtered
            else:
                df_display = df
            
            df_display = df_display.sort_values('numero_circolare', ascending=False)
            
            for idx, row in df_display.iterrows():
                data_pub = row['data_pubblicazione']
                is_new = (oggi - data_pub).days < 7
                data_pub_local = data_pub.replace(tzinfo=timezone.utc).astimezone()
                
                badge_html = f'<span class="badge badge-{"new" if is_new else "old"}">{"NUOVA" if is_new else "ARCHIVIO"}</span>'
                
                numero_html = ""
                if row['numero_circolare'] > 0:
                    numero_html = f'<span class="circolare-number">N.{row["numero_circolare"]}</span>'
                
                titolo_pulito = str(row['titolo']).strip()
                
                card_html = f'''
                <div class="circolare-card">
                    <div class="circolare-header">
                        {numero_html}
                        <span class="circolare-date">📅 Pubblicata il {data_pub_local.strftime('%d/%m/%Y')}</span>
                    </div>
                    <div class="circolare-title">
                        {titolo_pulito} {badge_html}
                    </div>
                '''
                
                if 'pdf_url' in row and pd.notna(row['pdf_url']):
                    urls = str(row['pdf_url']).split(';;;')
                    valid_urls = [url.strip() for url in urls if url.strip()]
                    
                    if valid_urls:
                        card_html += '<div class="doc-buttons-container">'
                        
                        for i, url in enumerate(valid_urls):
                            base = os.environ.get("SUPABASE_URL", "").rstrip('/')
                            if not url.startswith('http'):
                                url = f"{base}/storage/v1/object/public/documenti/{urllib.parse.quote(url)}"
                            
                            card_html += f'<a href="{url}" target="_blank" class="doc-button">📄 Documento {i+1}</a>'
                        
                        card_html += '</div>'
                
                card_html += '</div>'
                st.markdown(card_html, unsafe_allow_html=True)
        
        else:
            st.markdown('<div class="empty-state">📭 Nessuna circolare presente negli ultimi 30 giorni</div>', unsafe_allow_html=True)
            
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
