"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     GeoIA Territorial v3.0                                    ║
║         Inteligencia Artificial para Territorios Inteligentes                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Características v3.0:                                                        ║
║  • Interconexión automática entre módulos                                    ║
║  • Ejecución de código GeoPandas en vivo desde el chat                      ║
║  • Generación de mapas interactivos en tiempo real                          ║
║  • Base de conocimiento centralizada                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
from datetime import datetime

# Core
from core.data_store import get_store, init_store

# Components
from components.knowledge_base import render_knowledge_base_panel, render_knowledge_base_sidebar
from components.geo_viewer import render_geo_viewer
from components.analysis import render_analysis_panel
from components.chat import render_chat_interface, init_chat_session
from components.sidebar import render_sidebar

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="GeoIA Territorial v3.0",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/geoia-territorial',
        'Report a bug': 'https://github.com/geoia-territorial/issues',
        'About': '''
        ### 🌍 GeoIA Territorial v3.0
        
        Asistente de IA para análisis geoespacial y ordenamiento territorial.
        
        **Características:**
        - 💬 Chat inteligente con ejecución de código
        - 🗺️ Visor geoespacial interactivo
        - 📊 Herramientas de análisis territorial
        - 📁 Base de conocimiento integrada
        '''
    }
)

# ══════════════════════════════════════════════════════════════════════════════
# ESTILOS CSS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    /* Fuentes y colores base */
    :root {
        --primary: #1a5f4a;
        --primary-light: #2d8a6e;
        --secondary: #0ea5e9;
        --background: #f8fafc;
        --card-bg: #ffffff;
        --text: #1e293b;
        --text-light: #64748b;
    }
    
    /* Header principal */
    .main-header {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(26, 95, 74, 0.3);
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1rem;
    }
    
    /* Tabs personalizados */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: var(--background);
        padding: 0.5rem;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: var(--card-bg);
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        border: 1px solid #e2e8f0;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%) !important;
        color: white !important;
        border: none;
    }
    
    /* Cards */
    .geo-card {
        background: var(--card-bg);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
    
    /* Badges de estado */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    .status-connected {
        background: #dcfce7;
        color: #166534;
    }
    
    .status-disconnected {
        background: #fef3c7;
        color: #92400e;
    }
    
    /* Expanders mejorados */
    .streamlit-expanderHeader {
        background: var(--background);
        border-radius: 8px;
    }
    
    /* Botones primarios */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
        border: none;
        font-weight: 600;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 1.5rem;
        color: var(--text-light);
        font-size: 0.85rem;
    }
    
    /* Ocultar elementos de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Responsive */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 1.5rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# INICIALIZACIÓN
# ══════════════════════════════════════════════════════════════════════════════

# Inicializar store de datos
init_store()

# Inicializar sesión de chat
init_chat_session()

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    config = render_sidebar()

# ══════════════════════════════════════════════════════════════════════════════
# HEADER PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

store = get_store()

# Header con estado de conexión
st.markdown("""
<div class="main-header">
    <h1>🌍 GeoIA Territorial</h1>
    <p>Inteligencia Artificial para Territorios Inteligentes</p>
</div>
""", unsafe_allow_html=True)

# Barra de estado
if store.is_connected:
    summary = store.get_summary()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📁 Capas", summary['total_capas'])
    with col2:
        st.metric("📄 Documentos", summary['total_documentos'])
    with col3:
        st.metric("🗺️ Mapas QGIS", summary['total_mapas'])
    with col4:
        st.metric("📥 Cargadas", summary['capas_cargadas'])

# ══════════════════════════════════════════════════════════════════════════════
# TABS PRINCIPALES
# ══════════════════════════════════════════════════════════════════════════════

tab_chat, tab_kb, tab_viewer, tab_analysis, tab_docs = st.tabs([
    "💬 Chat Inteligente",
    "📁 Base de Conocimiento",
    "🗺️ Visor Geoespacial",
    "📊 Análisis Territorial",
    "📚 Documentación"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: CHAT INTELIGENTE
# ══════════════════════════════════════════════════════════════════════════════

with tab_chat:
    render_chat_interface(config)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: BASE DE CONOCIMIENTO
# ══════════════════════════════════════════════════════════════════════════════

with tab_kb:
    render_knowledge_base_panel()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: VISOR GEOESPACIAL
# ══════════════════════════════════════════════════════════════════════════════

with tab_viewer:
    render_geo_viewer()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: ANÁLISIS TERRITORIAL
# ══════════════════════════════════════════════════════════════════════════════

with tab_analysis:
    render_analysis_panel()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: DOCUMENTACIÓN
# ══════════════════════════════════════════════════════════════════════════════

with tab_docs:
    st.markdown("### 📚 Documentación de GeoIA Territorial v3.0")
    
    st.markdown("""
    #### 🆕 Novedades de la versión 3.0
    
    Esta versión introduce **interconexión automática entre módulos**:
    
    1. **Base de Conocimiento Centralizada**
       - Conecta una carpeta y todos los módulos acceden a tus datos
       - Las capas se escanean automáticamente
       - Soporte para Shapefiles, GeoJSON, GPKG, KML
    
    2. **Chat con Ejecución de Código**
       - El chat puede generar y ejecutar código GeoPandas
       - Mapas interactivos generados en tiempo real
       - Análisis espaciales directamente desde la conversación
    
    3. **Visor Geoespacial Conectado**
       - Carga automática de capas de la Base de Conocimiento
       - Visualización multi-capa
       - Controles de estilo por capa
    
    4. **Análisis Territorial Integrado**
       - Selecciona capas directamente de tu Base de Conocimiento
       - Buffers, intersecciones, uniones, clips
       - Mapas temáticos y estadísticas
    """)
    
    with st.expander("📁 Estructura de carpetas recomendada"):
        st.code("""
📁 MiProyectoTerritorial/
├── 📁 capas/              # Archivos geoespaciales
│   ├── predios.shp
│   ├── predios.shx
│   ├── predios.dbf
│   ├── predios.prj
│   ├── vias.geojson
│   ├── uso_suelo.gpkg
│   └── hidrografia.kml
│
├── 📁 documentos/         # Documentos de soporte
│   ├── POT_2024.pdf
│   ├── Normativa.docx
│   └── censo_poblacion.csv
│
└── 📁 mapas/              # Proyectos QGIS
    ├── proyecto_pot.qgz
    └── estilos.qml
        """)
    
    with st.expander("💬 Ejemplos de consultas al Chat"):
        st.markdown("""
        **Consultas informativas:**
        - "¿Qué capas tengo disponibles?"
        - "Describe la capa de predios"
        - "¿Cuántos elementos tiene la capa de vías?"
        
        **Análisis con código:**
        - "Calcula el área total de los predios"
        - "Genera un mapa de la capa uso_suelo"
        - "Haz un buffer de 100 metros a las vías"
        - "Intersecta predios con zonas de riesgo"
        
        **Mapas temáticos:**
        - "Crea un mapa coroplético de predios por área"
        - "Visualiza la distribución de uso del suelo"
        """)
    
    with st.expander("🔧 Configuración de API"):
        st.markdown("""
        ### Obtener API Key de Google Gemini
        
        1. Ve a [Google AI Studio](https://makersuite.google.com/app/apikey)
        2. Crea una nueva API Key
        3. Copia la clave y pégala en el sidebar
        
        **Modelos disponibles:**
        - `gemini-2.0-flash` - Rápido, ideal para uso general
        - `gemini-2.0-flash-lite` - Más económico
        - `gemini-2.5-flash` - Mayor rendimiento
        - `gemini-2.5-pro` - Más avanzado, mejor razonamiento
        """)
    
    # Info del sistema
    st.markdown("---")
    with st.expander("🔧 Información del Sistema"):
        kb_status = "Conectada" if store.is_connected else "No conectada"
        kb_path = str(store.root_path) if store.is_connected else "N/A"
        
        st.code(f"""
Sistema: GeoIA Territorial v3.0
Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Base de conocimiento: {kb_status}
Ruta: {kb_path}
Capas disponibles: {len(store.layers) if store.is_connected else 0}
Mensajes en sesión: {len(st.session_state.get('messages', []))}
        """)

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("""
<div class="footer">
    <p>🌍 <strong>GeoIA Territorial v3.0</strong> | Desarrollado con ❤️ para territorios inteligentes</p>
    <p style="font-size: 0.75rem; opacity: 0.7;">Powered by Streamlit + Google Gemini + GeoPandas + Folium</p>
</div>
""", unsafe_allow_html=True)
