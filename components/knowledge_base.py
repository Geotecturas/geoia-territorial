"""
GeoIA Territorial v3.0 - Componente Base de Conocimiento
=========================================================
Panel para conectar carpeta y sincronizar con todos los módulos.
"""

import streamlit as st
from pathlib import Path
from typing import Optional
import sys

# Agregar path del core
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_store import get_store


def render_knowledge_base_panel():
    """
    Renderiza el panel principal de Base de Conocimiento.
    Al conectar, sincroniza automáticamente con Chat, Visor y Análisis.
    """
    store = get_store()
    
    st.markdown("### 📁 Base de Conocimiento Territorial")
    st.markdown("*Conecta una carpeta para habilitar análisis integrado en todos los módulos*")
    
    # Estado de conexión
    if store.is_connected:
        summary = store.get_summary()
        
        # Mostrar estado conectado
        st.success(f"✅ **Conectado:** {store.root_path}")
        
        # Métricas en tiempo real
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🗺️ Capas", summary['total_capas'])
        with col2:
            st.metric("📄 Documentos", summary['total_documentos'])
        with col3:
            st.metric("🎨 Mapas QGIS", summary['total_mapas'])
        with col4:
            st.metric("📥 Cargadas", summary['capas_cargadas'])
        
        # Acciones
        col_refresh, col_disconnect = st.columns(2)
        with col_refresh:
            if st.button("🔄 Re-escanear", use_container_width=True):
                result = store.connect(str(store.root_path))
                if result['success']:
                    st.success("Base de conocimiento actualizada")
                    st.rerun()
        with col_disconnect:
            if st.button("❌ Desconectar", use_container_width=True):
                st.session_state.geo_store = None
                st.rerun()
        
        st.markdown("---")
        
        # Tabs para explorar contenido
        tab_layers, tab_docs, tab_maps = st.tabs([
            f"🗺️ Capas ({summary['total_capas']})",
            f"📄 Documentos ({summary['total_documentos']})",
            f"🎨 Mapas ({summary['total_mapas']})"
        ])
        
        with tab_layers:
            render_layers_explorer(store)
        
        with tab_docs:
            render_documents_explorer(store)
        
        with tab_maps:
            render_maps_explorer(store)
        
    else:
        # Formulario de conexión
        st.info("💡 Al conectar una carpeta, las capas estarán disponibles en:")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**💬 Chat Inteligente**")
            st.caption("Preguntas sobre datos y geoprocesamientos")
        with col2:
            st.markdown("**🗺️ Visor Geoespacial**")
            st.caption("Visualización interactiva de capas")
        with col3:
            st.markdown("**📊 Análisis Territorial**")
            st.caption("Herramientas de análisis espacial")
        
        st.markdown("---")
        
        # Input de ruta
        default_path = st.session_state.get('last_kb_path', '')
        folder_path = st.text_input(
            "📂 Ruta de la carpeta:",
            value=default_path,
            placeholder="C:\\MisProyectos\\GeoData o /home/usuario/geodata",
            help="Ingresa la ruta completa a tu carpeta de datos territoriales"
        )
        
        # Estructura esperada
        with st.expander("📁 Estructura de carpetas recomendada"):
            st.code("""
📁 MiCarpetaGeo/
├── 📁 capas/          # Shapefiles, GeoJSON, GPKG
│   ├── predios.shp
│   ├── vias.geojson
│   └── uso_suelo.gpkg
├── 📁 documentos/     # PDFs, Word, Excel, CSV
│   ├── POT_2024.pdf
│   └── datos_censo.csv
└── 📁 mapas/          # Proyectos QGIS
    └── proyecto.qgz
            """)
        
        # Botón de conexión
        if st.button("🔗 Conectar Carpeta", type="primary", use_container_width=True):
            if folder_path:
                with st.spinner("Escaneando carpeta..."):
                    result = store.connect(folder_path)
                
                if result['success']:
                    st.session_state.last_kb_path = folder_path
                    summary = result['summary']
                    st.success(
                        f"✅ Conectado exitosamente!\n\n"
                        f"- 🗺️ {summary['capas']} capas geoespaciales\n"
                        f"- 📄 {summary['documentos']} documentos\n"
                        f"- 🎨 {summary['mapas']} proyectos de mapa"
                    )
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"❌ Error: {result['error']}")
            else:
                st.warning("Por favor ingresa una ruta de carpeta")


def render_layers_explorer(store):
    """Explorador de capas geoespaciales"""
    if not store.layers:
        st.info("No se encontraron capas geoespaciales")
        return
    
    for name, layer in store.layers.items():
        with st.expander(f"📍 {name} ({layer.format.upper()})", expanded=False):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                - **Geometría:** {layer.geometry_type or 'No determinado'}
                - **CRS:** {layer.crs or 'No definido'}
                - **Elementos:** {layer.feature_count:,}
                - **Columnas:** {len(layer.columns)}
                """)
                
                if layer.columns:
                    st.caption(f"Atributos: {', '.join(layer.columns[:8])}{'...' if len(layer.columns) > 8 else ''}")
            
            with col2:
                if layer.loaded:
                    st.success("✅ En memoria")
                else:
                    if st.button(f"📥 Cargar", key=f"load_{name}"):
                        with st.spinner(f"Cargando {name}..."):
                            gdf = store.load_layer(name)
                            if gdf is not None:
                                st.success(f"Cargada: {len(gdf)} elementos")
                                st.rerun()
                            else:
                                st.error("Error al cargar")
            
            # Vista previa si está cargada
            if layer.loaded and layer.gdf is not None:
                st.dataframe(layer.gdf.drop(columns='geometry').head(5), use_container_width=True)


def render_documents_explorer(store):
    """Explorador de documentos"""
    if not store.documents:
        st.info("No se encontraron documentos")
        return
    
    for name, doc in store.documents.items():
        with st.expander(f"📄 {name}.{doc.format}", expanded=False):
            st.markdown(f"""
            - **Formato:** {doc.format.upper()}
            - **Tamaño:** {doc.size_kb:.1f} KB
            - **Ruta:** `{doc.path}`
            """)


def render_maps_explorer(store):
    """Explorador de proyectos de mapas"""
    if not store.maps:
        st.info("No se encontraron proyectos de mapas")
        return
    
    for name, path in store.maps.items():
        with st.expander(f"🎨 {name}", expanded=False):
            st.markdown(f"""
            - **Formato:** {path.suffix.upper()}
            - **Ruta:** `{path}`
            """)
            st.info("💡 Los proyectos QGIS se pueden abrir directamente en QGIS Desktop")


def render_knowledge_base_sidebar():
    """
    Versión compacta para el sidebar.
    Muestra estado y permite conexión rápida.
    """
    store = get_store()
    
    st.markdown("#### 📁 Base de Conocimiento")
    
    if store.is_connected:
        summary = store.get_summary()
        
        # Indicador de estado
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #1a5f4a 0%, #2d8a6e 100%);
            padding: 0.8rem;
            border-radius: 8px;
            color: white;
            margin-bottom: 0.5rem;
        ">
            <div style="font-size: 0.75rem; opacity: 0.9;">✅ Conectado</div>
            <div style="font-size: 0.85rem; font-weight: 600;">
                {summary['total_capas']} capas • {summary['total_documentos']} docs
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Botón de re-escaneo
        if st.button("🔄 Actualizar", key="sidebar_refresh", use_container_width=True):
            store.connect(str(store.root_path))
            st.rerun()
    else:
        st.markdown("""
        <div style="
            background: #f8fafc;
            border: 2px dashed #94a3b8;
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
        ">
            <div style="font-size: 1.5rem;">📁</div>
            <div style="font-size: 0.8rem; color: #64748b;">
                Sin conexión
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.caption("Ve a 'Base de Conocimiento' para conectar")


def get_kb_layers_for_selector() -> dict:
    """
    Retorna las capas disponibles para selectores en otros módulos.
    Usado por Visor Geoespacial y Análisis Territorial.
    """
    store = get_store()
    
    if not store.is_connected:
        return {}
    
    return {
        name: {
            'info': layer.to_dict(),
            'loaded': layer.loaded,
            'gdf': layer.gdf
        }
        for name, layer in store.layers.items()
    }


def load_kb_layer(layer_name: str):
    """
    Carga una capa específica de la base de conocimiento.
    Usado por otros módulos para obtener datos.
    """
    store = get_store()
    return store.load_layer(layer_name)


def get_kb_context_for_chat() -> str:
    """
    Retorna contexto formateado para el Chat Inteligente.
    """
    store = get_store()
    return store.get_context_for_chat()
