"""
GeoIA Territorial v3.0 - Visor Geoespacial
==========================================
Carga automáticamente las capas de la Base de Conocimiento.
Permite visualización interactiva con múltiples capas.
"""

import streamlit as st
import folium
from folium.plugins import MarkerCluster, Fullscreen, MiniMap, MousePosition
from streamlit_folium import st_folium
import geopandas as gpd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_store import get_store


# Paletas de colores para capas
LAYER_COLORS = [
    '#3388ff', '#ff7800', '#00ff00', '#ff0000', '#800080',
    '#008080', '#ffd700', '#ff69b4', '#00ced1', '#ff6347'
]

# Opciones de mapas base
BASEMAPS = {
    'OpenStreetMap': 'OpenStreetMap',
    'CartoDB Positron': 'CartoDB positron',
    'CartoDB Dark': 'CartoDB dark_matter',
    'Stamen Terrain': 'Stamen Terrain',
    'Stamen Toner': 'Stamen Toner',
    'ESRI Satellite': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    'ESRI Topo': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}'
}


def render_geo_viewer():
    """
    Renderiza el Visor Geoespacial.
    Detecta automáticamente capas de la Base de Conocimiento.
    """
    store = get_store()
    
    st.markdown("### 🗺️ Visor Geoespacial Interactivo")
    
    # Verificar si hay base de conocimiento conectada
    if not store.is_connected:
        st.warning("⚠️ **Base de Conocimiento no conectada**")
        st.info("Para visualizar capas automáticamente, conecta una carpeta en la pestaña 'Base de Conocimiento'")
        
        # Opción de cargar archivo individual
        st.markdown("---")
        st.markdown("#### 📂 Cargar archivo individual")
        uploaded = st.file_uploader(
            "Sube un archivo geoespacial",
            type=['geojson', 'json', 'zip', 'gpkg', 'kml'],
            key="geo_viewer_upload"
        )
        
        if uploaded:
            render_single_file_map(uploaded)
        return
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PANEL DE CONTROL DE CAPAS
    # ═══════════════════════════════════════════════════════════════════════════
    
    st.markdown("---")
    
    # Layout: Panel de capas + Mapa
    col_layers, col_map = st.columns([1, 3])
    
    with col_layers:
        st.markdown("#### 📋 Capas Disponibles")
        
        available_layers = store.get_all_layers_info()
        
        if not available_layers:
            st.info("No hay capas en la base de conocimiento")
            return
        
        # Selector de capas con checkboxes
        selected_layers = []
        layer_styles = {}
        
        for i, layer_info in enumerate(available_layers):
            layer_name = layer_info['name']
            color = LAYER_COLORS[i % len(LAYER_COLORS)]
            
            # Checkbox con color indicador
            col_check, col_color = st.columns([4, 1])
            
            with col_check:
                is_selected = st.checkbox(
                    f"📍 {layer_name}",
                    value=False,
                    key=f"layer_check_{layer_name}",
                    help=f"{layer_info['geometry_type']} - {layer_info['feature_count']} elementos"
                )
            
            with col_color:
                if is_selected:
                    st.color_picker(
                        "",
                        value=color,
                        key=f"color_{layer_name}",
                        label_visibility="collapsed"
                    )
            
            if is_selected:
                selected_layers.append(layer_name)
                layer_styles[layer_name] = {
                    'color': st.session_state.get(f"color_{layer_name}", color),
                    'weight': 2,
                    'fillOpacity': 0.5
                }
            
            # Info compacta
            if is_selected:
                st.caption(f"  ↳ {layer_info['feature_count']:,} elementos | {layer_info['crs'] or 'Sin CRS'}")
        
        st.markdown("---")
        
        # Configuración del mapa
        st.markdown("#### ⚙️ Configuración")
        
        basemap = st.selectbox(
            "Mapa base:",
            options=list(BASEMAPS.keys()),
            index=0
        )
        
        show_legend = st.checkbox("Mostrar leyenda", value=True)
        show_popup = st.checkbox("Popups interactivos", value=True)
        
        # Botón para cargar todas
        if st.button("📥 Cargar Todas", use_container_width=True):
            with st.spinner("Cargando todas las capas..."):
                store.load_all_layers()
            st.rerun()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ÁREA DEL MAPA
    # ═══════════════════════════════════════════════════════════════════════════
    
    with col_map:
        if not selected_layers:
            st.info("👆 Selecciona capas del panel izquierdo para visualizarlas")
            
            # Mostrar mapa vacío centrado en Colombia
            empty_map = folium.Map(
                location=[4.5709, -74.2973],
                zoom_start=5,
                tiles=BASEMAPS[basemap]
            )
            st_folium(empty_map, width=None, height=600, use_container_width=True)
        else:
            # Cargar y renderizar capas seleccionadas
            render_multi_layer_map(
                store=store,
                layer_names=selected_layers,
                styles=layer_styles,
                basemap=BASEMAPS[basemap],
                show_legend=show_legend,
                show_popup=show_popup
            )


def render_multi_layer_map(store, layer_names: list, styles: dict, 
                           basemap: str, show_legend: bool, show_popup: bool):
    """
    Renderiza mapa con múltiples capas de la base de conocimiento.
    """
    # Cargar las capas seleccionadas
    gdfs = {}
    all_bounds = []
    
    progress = st.progress(0)
    for i, name in enumerate(layer_names):
        gdf = store.load_layer(name)
        if gdf is not None:
            # Asegurar WGS84
            if gdf.crs and gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')
            gdfs[name] = gdf
            all_bounds.append(gdf.total_bounds)
        progress.progress((i + 1) / len(layer_names))
    
    progress.empty()
    
    if not gdfs:
        st.error("No se pudieron cargar las capas seleccionadas")
        return
    
    # Calcular bounds combinados
    import numpy as np
    combined_bounds = [
        min(b[0] for b in all_bounds),  # minx
        min(b[1] for b in all_bounds),  # miny
        max(b[2] for b in all_bounds),  # maxx
        max(b[3] for b in all_bounds),  # maxy
    ]
    center = [(combined_bounds[1] + combined_bounds[3]) / 2,
              (combined_bounds[0] + combined_bounds[2]) / 2]
    
    # Crear mapa
    if basemap.startswith('http'):
        m = folium.Map(location=center, zoom_start=10, tiles=None)
        folium.TileLayer(
            tiles=basemap,
            attr='ESRI',
            name='ESRI'
        ).add_to(m)
    else:
        m = folium.Map(location=center, zoom_start=10, tiles=basemap)
    
    # Ajustar a bounds
    m.fit_bounds([
        [combined_bounds[1], combined_bounds[0]],
        [combined_bounds[3], combined_bounds[2]]
    ])
    
    # Agregar capas
    for name, gdf in gdfs.items():
        style = styles.get(name, {'color': '#3388ff', 'weight': 2, 'fillOpacity': 0.5})
        
        # Feature group para cada capa
        fg = folium.FeatureGroup(name=name)
        
        # Determinar tipo de geometría
        geom_type = gdf.geometry.geom_type.iloc[0] if len(gdf) > 0 else None
        
        if geom_type in ['Point', 'MultiPoint']:
            # Puntos con marcadores
            for idx, row in gdf.iterrows():
                popup_content = create_popup_content(row, gdf.columns) if show_popup else None
                
                folium.CircleMarker(
                    location=[row.geometry.y, row.geometry.x],
                    radius=6,
                    color=style['color'],
                    fill=True,
                    fillColor=style['color'],
                    fillOpacity=0.7,
                    popup=popup_content
                ).add_to(fg)
        else:
            # Polígonos y líneas
            folium.GeoJson(
                gdf,
                name=name,
                style_function=lambda x, s=style: {
                    'fillColor': s['color'],
                    'color': s['color'],
                    'weight': s['weight'],
                    'fillOpacity': s['fillOpacity']
                },
                popup=folium.GeoJsonPopup(
                    fields=list(gdf.columns.drop('geometry'))[:5],
                    aliases=list(gdf.columns.drop('geometry'))[:5],
                    localize=True
                ) if show_popup else None
            ).add_to(fg)
        
        fg.add_to(m)
    
    # Agregar controles
    folium.LayerControl().add_to(m)
    Fullscreen().add_to(m)
    MiniMap(toggle_display=True).add_to(m)
    MousePosition().add_to(m)
    
    # Leyenda personalizada
    if show_legend and len(gdfs) > 1:
        legend_html = create_legend_html(gdfs.keys(), styles)
        m.get_root().html.add_child(folium.Element(legend_html))
    
    # Renderizar mapa
    map_data = st_folium(m, width=None, height=600, use_container_width=True)
    
    # Información de capas cargadas
    st.markdown("---")
    cols = st.columns(len(gdfs))
    for i, (name, gdf) in enumerate(gdfs.items()):
        with cols[i]:
            st.metric(
                name,
                f"{len(gdf):,}",
                help=f"Tipo: {gdf.geometry.geom_type.iloc[0]}"
            )


def create_popup_content(row, columns) -> str:
    """Crea contenido HTML para popup"""
    content = "<div style='font-size:12px;'>"
    for col in columns:
        if col != 'geometry':
            val = row[col]
            if val is not None:
                content += f"<b>{col}:</b> {val}<br>"
    content += "</div>"
    return folium.Popup(content, max_width=300)


def create_legend_html(layer_names, styles) -> str:
    """Genera HTML para leyenda del mapa"""
    items = ""
    for name in layer_names:
        color = styles.get(name, {}).get('color', '#3388ff')
        items += f"""
        <div style="display:flex;align-items:center;margin-bottom:5px;">
            <div style="width:20px;height:20px;background:{color};margin-right:8px;border-radius:3px;"></div>
            <span style="font-size:12px;">{name}</span>
        </div>
        """
    
    return f"""
    <div style="
        position: fixed;
        bottom: 30px;
        right: 10px;
        background: white;
        padding: 10px 15px;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        z-index: 1000;
        max-width: 200px;
    ">
        <div style="font-weight:bold;margin-bottom:8px;font-size:13px;">📍 Capas</div>
        {items}
    </div>
    """


def render_single_file_map(uploaded_file):
    """Renderiza mapa de un archivo individual cargado"""
    import tempfile
    import os
    
    try:
        # Guardar archivo temporal
        suffix = Path(uploaded_file.name).suffix
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        # Si es ZIP (shapefile), extraer
        if suffix.lower() == '.zip':
            import zipfile
            extract_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Buscar .shp
            shp_files = list(Path(extract_dir).rglob('*.shp'))
            if shp_files:
                gdf = gpd.read_file(shp_files[0])
            else:
                st.error("No se encontró archivo .shp en el ZIP")
                return
        else:
            gdf = gpd.read_file(tmp_path)
        
        # Limpiar
        os.unlink(tmp_path)
        
        # Convertir a WGS84
        if gdf.crs and gdf.crs != 'EPSG:4326':
            gdf = gdf.to_crs('EPSG:4326')
        
        # Info del archivo
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Elementos", len(gdf))
        with col2:
            st.metric("Geometría", gdf.geometry.geom_type.iloc[0])
        with col3:
            st.metric("Columnas", len(gdf.columns) - 1)
        
        # Crear mapa
        bounds = gdf.total_bounds
        center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
        
        m = folium.Map(location=center, tiles='CartoDB positron')
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
        
        folium.GeoJson(
            gdf,
            style_function=lambda x: {
                'fillColor': '#3388ff',
                'color': '#000000',
                'weight': 1,
                'fillOpacity': 0.6
            }
        ).add_to(m)
        
        st_folium(m, width=None, height=500, use_container_width=True)
        
        # Tabla de atributos
        with st.expander("📊 Ver tabla de atributos"):
            st.dataframe(gdf.drop(columns='geometry'), use_container_width=True)
            
    except Exception as e:
        st.error(f"Error al cargar archivo: {str(e)}")
