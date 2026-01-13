"""
GeoIA Territorial v3.0 - Análisis Territorial
==============================================
Selecciona capas de la Base de Conocimiento para análisis espacial.
"""

import streamlit as st
import geopandas as gpd
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_store import get_store
from core.execution_engine import GeoProcessingTools


def render_analysis_panel():
    """
    Renderiza el panel de Análisis Territorial.
    Permite seleccionar capas de la Base de Conocimiento para análisis.
    """
    store = get_store()
    
    st.markdown("### 📊 Panel de Análisis Territorial")
    
    # Verificar conexión
    if not store.is_connected:
        st.warning("⚠️ **Base de Conocimiento no conectada**")
        st.info("Conecta una carpeta en la pestaña 'Base de Conocimiento' para acceder a las herramientas de análisis")
        return
    
    # Obtener capas disponibles
    available_layers = store.get_layer_names()
    
    if not available_layers:
        st.info("No hay capas disponibles para análisis")
        return
    
    st.success(f"✅ **{len(available_layers)} capas disponibles** desde la Base de Conocimiento")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SELECTOR DE ANÁLISIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    st.markdown("---")
    
    analysis_types = {
        "📏 Cálculo de Áreas": "area",
        "🔵 Buffer (Zona de influencia)": "buffer",
        "✂️ Intersección de capas": "intersection",
        "🔗 Unión de capas": "union",
        "➖ Diferencia de capas": "difference",
        "📍 Centroides": "centroid",
        "📐 Envolvente convexa": "convex_hull",
        "🔀 Join espacial": "spatial_join",
        "✂️ Recorte (Clip)": "clip",
        "📊 Estadísticas descriptivas": "stats",
        "🗺️ Mapa temático": "thematic_map"
    }
    
    selected_analysis = st.selectbox(
        "🔧 Selecciona tipo de análisis:",
        options=list(analysis_types.keys()),
        index=0
    )
    
    analysis_type = analysis_types[selected_analysis]
    
    st.markdown("---")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURACIÓN SEGÚN TIPO DE ANÁLISIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    if analysis_type in ["area", "centroid", "convex_hull", "stats"]:
        # Análisis de una sola capa
        render_single_layer_analysis(store, available_layers, analysis_type)
        
    elif analysis_type == "buffer":
        render_buffer_analysis(store, available_layers)
        
    elif analysis_type in ["intersection", "union", "difference", "spatial_join", "clip"]:
        # Análisis de dos capas
        render_two_layer_analysis(store, available_layers, analysis_type)
        
    elif analysis_type == "thematic_map":
        render_thematic_map(store, available_layers)


def render_single_layer_analysis(store, layers: list, analysis_type: str):
    """Análisis que requiere una sola capa"""
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_layer = st.selectbox(
            "📍 Selecciona capa:",
            options=layers,
            key="single_layer_select"
        )
        
        # Mostrar info de la capa
        layer_info = store.get_layer_info(selected_layer)
        if layer_info:
            st.markdown(f"""
            **Información:**
            - Geometría: {layer_info['geometry_type']}
            - Elementos: {layer_info['feature_count']:,}
            - CRS: {layer_info['crs'] or 'No definido'}
            """)
        
        run_analysis = st.button("▶️ Ejecutar Análisis", type="primary", use_container_width=True)
    
    with col2:
        if run_analysis:
            with st.spinner(f"Ejecutando {analysis_type}..."):
                gdf = store.load_layer(selected_layer)
                
                if gdf is None:
                    st.error("Error al cargar la capa")
                    return
                
                if analysis_type == "area":
                    result = calculate_areas(gdf)
                elif analysis_type == "centroid":
                    result = calculate_centroids(gdf)
                elif analysis_type == "convex_hull":
                    result = calculate_convex_hull(gdf)
                elif analysis_type == "stats":
                    display_statistics(gdf, selected_layer)
                    return
                
                if result is not None:
                    display_result(result, f"Resultado: {analysis_type}")


def render_buffer_analysis(store, layers: list):
    """Análisis de buffer"""
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_layer = st.selectbox(
            "📍 Selecciona capa:",
            options=layers,
            key="buffer_layer"
        )
        
        distance = st.number_input(
            "📏 Distancia (metros):",
            min_value=1,
            max_value=100000,
            value=100,
            step=10
        )
        
        cap_style = st.selectbox(
            "Estilo de bordes:",
            options=["Redondo", "Plano", "Cuadrado"],
            index=0
        )
        cap_map = {"Redondo": 1, "Plano": 2, "Cuadrado": 3}
        
        run_buffer = st.button("▶️ Crear Buffer", type="primary", use_container_width=True)
    
    with col2:
        if run_buffer:
            with st.spinner(f"Creando buffer de {distance}m..."):
                gdf = store.load_layer(selected_layer)
                
                if gdf is None:
                    st.error("Error al cargar la capa")
                    return
                
                result = create_buffer(gdf, distance, cap_map[cap_style])
                
                if result is not None:
                    display_result_with_map(result, gdf, f"Buffer {distance}m")


def render_two_layer_analysis(store, layers: list, analysis_type: str):
    """Análisis que requiere dos capas"""
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        layer1 = st.selectbox(
            "📍 Primera capa:",
            options=layers,
            key="layer1_select"
        )
        
        layer2 = st.selectbox(
            "📍 Segunda capa:",
            options=[l for l in layers if l != layer1],
            key="layer2_select"
        )
        
        if analysis_type == "spatial_join":
            predicate = st.selectbox(
                "Tipo de relación:",
                options=["intersects", "contains", "within", "touches"],
                index=0
            )
        
        run_analysis = st.button("▶️ Ejecutar", type="primary", use_container_width=True)
    
    with col2:
        if run_analysis:
            with st.spinner("Procesando capas..."):
                gdf1 = store.load_layer(layer1)
                gdf2 = store.load_layer(layer2)
                
                if gdf1 is None or gdf2 is None:
                    st.error("Error al cargar las capas")
                    return
                
                # Asegurar mismo CRS
                if gdf1.crs != gdf2.crs:
                    gdf2 = gdf2.to_crs(gdf1.crs)
                
                if analysis_type == "intersection":
                    result = gpd.overlay(gdf1, gdf2, how='intersection')
                elif analysis_type == "union":
                    result = gpd.overlay(gdf1, gdf2, how='union')
                elif analysis_type == "difference":
                    result = gpd.overlay(gdf1, gdf2, how='difference')
                elif analysis_type == "spatial_join":
                    result = gpd.sjoin(gdf1, gdf2, how='inner', predicate=predicate)
                elif analysis_type == "clip":
                    result = gpd.clip(gdf1, gdf2)
                
                st.success(f"✅ Resultado: {len(result)} elementos")
                display_result(result, f"{analysis_type.title()}: {layer1} + {layer2}")


def render_thematic_map(store, layers: list):
    """Genera mapas temáticos"""
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_layer = st.selectbox(
            "📍 Selecciona capa:",
            options=layers,
            key="thematic_layer"
        )
        
        # Cargar para obtener columnas
        gdf = store.load_layer(selected_layer)
        
        if gdf is None:
            st.error("Error al cargar capa")
            return
        
        # Columnas numéricas para colorear
        numeric_cols = gdf.select_dtypes(include=[np.number]).columns.tolist()
        
        if numeric_cols:
            color_column = st.selectbox(
                "🎨 Columna para colorear:",
                options=numeric_cols
            )
            
            color_scheme = st.selectbox(
                "Paleta de colores:",
                options=['YlOrRd', 'YlGn', 'BuPu', 'RdYlBu', 'Spectral', 'viridis', 'plasma']
            )
            
            create_map = st.button("🗺️ Generar Mapa", type="primary", use_container_width=True)
        else:
            st.warning("La capa no tiene columnas numéricas para mapas temáticos")
            create_map = False
    
    with col2:
        if numeric_cols and create_map:
            create_thematic_map_display(gdf, color_column, color_scheme, selected_layer)


# ═══════════════════════════════════════════════════════════════════════════
# FUNCIONES DE ANÁLISIS
# ═══════════════════════════════════════════════════════════════════════════

def calculate_areas(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Calcula áreas en metros cuadrados y hectáreas"""
    result = gdf.copy()
    
    # Reproyectar si es geográfico
    if result.crs and result.crs.is_geographic:
        result_proj = result.to_crs(result.estimate_utm_crs())
        result['area_m2'] = result_proj.geometry.area
    else:
        result['area_m2'] = result.geometry.area
    
    result['area_ha'] = result['area_m2'] / 10000
    result['area_km2'] = result['area_m2'] / 1000000
    
    return result


def calculate_centroids(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Calcula centroides de geometrías"""
    result = gdf.copy()
    result['geometry'] = result.geometry.centroid
    result['centroid_x'] = result.geometry.x
    result['centroid_y'] = result.geometry.y
    return result


def calculate_convex_hull(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Calcula envolvente convexa"""
    result = gdf.copy()
    result['geometry'] = result.geometry.convex_hull
    return result


def create_buffer(gdf: gpd.GeoDataFrame, distance: float, cap_style: int) -> gpd.GeoDataFrame:
    """Crea buffer alrededor de geometrías"""
    result = gdf.copy()
    
    # Reproyectar para trabajar en metros
    if result.crs and result.crs.is_geographic:
        original_crs = result.crs
        result = result.to_crs(result.estimate_utm_crs())
        result['geometry'] = result.geometry.buffer(distance, cap_style=cap_style)
        result = result.to_crs(original_crs)
    else:
        result['geometry'] = result.geometry.buffer(distance, cap_style=cap_style)
    
    return result


def display_statistics(gdf: gpd.GeoDataFrame, layer_name: str):
    """Muestra estadísticas descriptivas de la capa"""
    
    st.markdown(f"#### 📊 Estadísticas: {layer_name}")
    
    # Resumen general
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total elementos", len(gdf))
    with col2:
        st.metric("Columnas", len(gdf.columns) - 1)
    with col3:
        geom_type = gdf.geometry.geom_type.iloc[0] if len(gdf) > 0 else "N/A"
        st.metric("Geometría", geom_type)
    
    # Estadísticas numéricas
    numeric_df = gdf.select_dtypes(include=[np.number])
    
    if not numeric_df.empty:
        st.markdown("**Columnas numéricas:**")
        st.dataframe(numeric_df.describe(), use_container_width=True)
    
    # Columnas categóricas
    cat_cols = gdf.select_dtypes(include=['object']).columns.tolist()
    cat_cols = [c for c in cat_cols if c != 'geometry']
    
    if cat_cols:
        st.markdown("**Distribución de categorías:**")
        selected_cat = st.selectbox("Columna:", cat_cols)
        value_counts = gdf[selected_cat].value_counts().head(10)
        st.bar_chart(value_counts)
    
    # Bounds geográficos
    bounds = gdf.total_bounds
    st.markdown("**Extensión geográfica:**")
    st.code(f"""
Min X (Oeste):  {bounds[0]:.6f}
Min Y (Sur):    {bounds[1]:.6f}
Max X (Este):   {bounds[2]:.6f}
Max Y (Norte):  {bounds[3]:.6f}
    """)


def display_result(gdf: gpd.GeoDataFrame, title: str):
    """Muestra resultado de análisis con mapa y tabla"""
    
    st.markdown(f"#### {title}")
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Elementos", len(gdf))
    with col2:
        st.metric("Columnas", len(gdf.columns))
    with col3:
        if 'area_ha' in gdf.columns:
            st.metric("Área total (ha)", f"{gdf['area_ha'].sum():,.2f}")
    
    # Tabs para mapa y tabla
    tab_map, tab_table = st.tabs(["🗺️ Mapa", "📋 Tabla"])
    
    with tab_map:
        display_simple_map(gdf)
    
    with tab_table:
        st.dataframe(
            gdf.drop(columns='geometry', errors='ignore').head(100),
            use_container_width=True
        )
    
    # Opción de descarga
    if st.button("💾 Descargar como GeoJSON"):
        geojson = gdf.to_json()
        st.download_button(
            "📥 Descargar",
            data=geojson,
            file_name="resultado_analisis.geojson",
            mime="application/json"
        )


def display_result_with_map(result_gdf: gpd.GeoDataFrame, original_gdf: gpd.GeoDataFrame, title: str):
    """Muestra resultado con comparación antes/después"""
    
    st.markdown(f"#### {title}")
    
    # Asegurar WGS84
    if result_gdf.crs and result_gdf.crs != 'EPSG:4326':
        result_gdf = result_gdf.to_crs('EPSG:4326')
    if original_gdf.crs and original_gdf.crs != 'EPSG:4326':
        original_gdf = original_gdf.to_crs('EPSG:4326')
    
    bounds = result_gdf.total_bounds
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    
    m = folium.Map(location=center, tiles='CartoDB positron')
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    
    # Capa original (semi-transparente)
    folium.GeoJson(
        original_gdf,
        name="Original",
        style_function=lambda x: {
            'fillColor': '#888888',
            'color': '#444444',
            'weight': 1,
            'fillOpacity': 0.3
        }
    ).add_to(m)
    
    # Resultado
    folium.GeoJson(
        result_gdf,
        name="Resultado",
        style_function=lambda x: {
            'fillColor': '#ff7800',
            'color': '#ff5500',
            'weight': 2,
            'fillOpacity': 0.5
        }
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    
    st_folium(m, width=None, height=400, use_container_width=True)


def display_simple_map(gdf: gpd.GeoDataFrame):
    """Muestra mapa simple de un GeoDataFrame"""
    
    if gdf.crs and gdf.crs != 'EPSG:4326':
        gdf = gdf.to_crs('EPSG:4326')
    
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
    
    st_folium(m, width=None, height=400, use_container_width=True)


def create_thematic_map_display(gdf: gpd.GeoDataFrame, column: str, cmap: str, layer_name: str):
    """Genera y muestra mapa temático"""
    
    if gdf.crs and gdf.crs != 'EPSG:4326':
        gdf = gdf.to_crs('EPSG:4326')
    
    bounds = gdf.total_bounds
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    
    m = folium.Map(location=center, tiles='CartoDB positron')
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    
    # Mapa coroplético
    folium.Choropleth(
        geo_data=gdf.__geo_interface__,
        data=gdf,
        columns=[gdf.index.name or gdf.columns[0], column],
        key_on='feature.properties.' + (gdf.index.name or gdf.columns[0]),
        fill_color=cmap,
        fill_opacity=0.7,
        line_opacity=0.8,
        legend_name=column,
        nan_fill_color='gray'
    ).add_to(m)
    
    st.markdown(f"#### 🗺️ Mapa Temático: {column}")
    
    # Estadísticas de la columna
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Mínimo", f"{gdf[column].min():,.2f}")
    with col2:
        st.metric("Máximo", f"{gdf[column].max():,.2f}")
    with col3:
        st.metric("Media", f"{gdf[column].mean():,.2f}")
    with col4:
        st.metric("Std Dev", f"{gdf[column].std():,.2f}")
    
    st_folium(m, width=None, height=500, use_container_width=True)
