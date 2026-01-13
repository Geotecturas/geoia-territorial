"""
GeoIA Territorial v3.0 - Sidebar
================================
Configuración y controles del sidebar.
"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_store import get_store


def render_sidebar() -> dict:
    """
    Renderiza el sidebar con configuración.
    Retorna diccionario de configuración.
    """
    
    st.markdown("## ⚙️ Configuración")
    
    # API Key
    api_key = st.text_input(
        "🔑 API Key de Google:",
        type="password",
        value=st.session_state.get("api_key", ""),
        help="Tu API Key de Google Gemini"
    )
    
    if api_key:
        st.session_state.api_key = api_key
    
    st.markdown("---")
    
    # Modelo - Actualizados enero 2026
    model = st.selectbox(
        "🤖 Modelo:",
        options=[
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.5-pro"
        ],
        index=0,
        help="gemini-2.0-flash: Rápido y económico | gemini-2.5-pro: Más avanzado"
    )
    
    # Modo del asistente
    mode = st.selectbox(
        "👤 Modo del asistente:",
        options=[
            ("general", "🌍 General"),
            ("analista", "📊 Analista Territorial"),
            ("pot", "🏛️ Consultor POT"),
            ("cartografo", "🗺️ Cartógrafo"),
            ("cientifico", "🔬 Científico de Datos")
        ],
        format_func=lambda x: x[1],
        index=0
    )
    
    # Temperatura
    temperature = st.slider(
        "🌡️ Temperatura:",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="0 = Preciso, 1 = Creativo"
    )
    
    st.markdown("---")
    
    # Estado de la base de conocimiento
    render_kb_status()
    
    st.markdown("---")
    
    # Acciones rápidas
    st.markdown("### 🔧 Acciones")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Limpiar chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    with col2:
        if st.button("📥 Exportar", use_container_width=True):
            export_conversation()
    
    return {
        "api_key": api_key,
        "model": model,
        "mode": mode[0],
        "temperature": temperature
    }


def render_kb_status():
    """Renderiza estado de la base de conocimiento en el sidebar"""
    
    store = get_store()
    
    st.markdown("### 📁 Base de Conocimiento")
    
    if store.is_connected:
        summary = store.get_summary()
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #1a5f4a 0%, #2d8a6e 100%);
            padding: 0.8rem;
            border-radius: 8px;
            color: white;
        ">
            <div style="font-size: 0.75rem; opacity: 0.9;">✅ Conectado</div>
            <div style="font-size: 1rem; font-weight: 600; margin-top: 0.25rem;">
                {summary['total_capas']} capas • {summary['total_documentos']} docs
            </div>
            <div style="font-size: 0.7rem; opacity: 0.8; margin-top: 0.25rem;">
                {summary['capas_cargadas']} capas en memoria
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔄 Actualizar", key="kb_refresh", use_container_width=True):
            store.connect(str(store.root_path))
            st.rerun()
            
    else:
        st.markdown("""
        <div style="
            background: #fef3c7;
            border: 1px solid #f59e0b;
            padding: 0.8rem;
            border-radius: 8px;
            text-align: center;
        ">
            <div style="font-size: 1.2rem;">📁</div>
            <div style="font-size: 0.8rem; color: #92400e;">
                No conectado
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.caption("Ve a 'Base de Conocimiento' para conectar una carpeta")


def export_conversation():
    """Exporta la conversación actual"""
    import json
    from datetime import datetime
    
    messages = st.session_state.get("messages", [])
    
    if not messages:
        st.warning("No hay mensajes para exportar")
        return
    
    export_data = {
        "exported_at": datetime.now().isoformat(),
        "message_count": len(messages),
        "messages": messages
    }
    
    json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
    
    st.download_button(
        "💾 Descargar JSON",
        data=json_str,
        file_name=f"geoia_chat_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json"
    )
