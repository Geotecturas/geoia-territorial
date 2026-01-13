"""
GeoIA Territorial v3.0 - Motor de Ejecución de Código
=====================================================
Permite al Chat Inteligente ejecutar código GeoPandas y generar mapas en vivo.
"""

import sys
import io
import traceback
from typing import Dict, Any, Optional, Tuple
import geopandas as gpd
import pandas as pd
import numpy as np
import folium
from folium.plugins import MarkerCluster, HeatMap
import matplotlib.pyplot as plt
import contextlib
import re


class CodeExecutionEngine:
    """
    Motor de ejecución segura de código GeoPandas.
    Permite al chat generar y ejecutar código para análisis geoespacial.
    """
    
    # Módulos permitidos para ejecución
    ALLOWED_MODULES = {
        'geopandas': gpd,
        'gpd': gpd,
        'pandas': pd,
        'pd': pd,
        'numpy': np,
        'np': np,
        'folium': folium,
        'MarkerCluster': MarkerCluster,
        'HeatMap': HeatMap
    }
    
    # Operaciones peligrosas prohibidas
    FORBIDDEN_PATTERNS = [
        r'import\s+os',
        r'import\s+subprocess',
        r'import\s+sys',
        r'__import__',
        r'eval\s*\(',
        r'exec\s*\(',
        r'open\s*\(',
        r'file\s*\(',
        r'input\s*\(',
        r'os\.',
        r'subprocess\.',
        r'shutil\.',
        r'pathlib\.Path.*unlink',
        r'\.remove\s*\(',
        r'\.delete\s*\(',
        r'\.rmdir\s*\(',
    ]
    
    def __init__(self, layers: Dict[str, gpd.GeoDataFrame] = None):
        """
        Inicializa el motor con las capas disponibles.
        
        Args:
            layers: Diccionario de capas cargadas {nombre: GeoDataFrame}
        """
        self.layers = layers or {}
        self.results = {}
        self.generated_maps = []
        self.generated_figures = []
        
    def set_layers(self, layers: Dict[str, gpd.GeoDataFrame]):
        """Actualiza las capas disponibles"""
        self.layers = layers
        
    def validate_code(self, code: str) -> Tuple[bool, str]:
        """
        Valida que el código sea seguro para ejecutar.
        
        Returns:
            (is_valid, error_message)
        """
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Operación no permitida detectada: {pattern}"
        
        return True, ""
    
    def execute(self, code: str) -> Dict[str, Any]:
        """
        Ejecuta código Python con GeoPandas de forma segura.
        
        Args:
            code: Código Python a ejecutar
            
        Returns:
            Dict con resultado, salida, errores, mapas generados, etc.
        """
        # Validar código
        is_valid, error = self.validate_code(code)
        if not is_valid:
            return {
                "success": False,
                "error": error,
                "output": "",
                "result": None,
                "maps": [],
                "figures": []
            }
        
        # Preparar entorno de ejecución
        exec_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'list': list,
                'dict': dict,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'tuple': tuple,
                'set': set,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'sorted': sorted,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'isinstance': isinstance,
                'type': type,
                'hasattr': hasattr,
                'getattr': getattr,
            },
            **self.ALLOWED_MODULES,
            'layers': self.layers,  # Acceso a las capas
            'capas': self.layers,   # Alias en español
        }
        
        # Agregar cada capa como variable directa
        for name, gdf in self.layers.items():
            # Sanitizar nombre para usar como variable
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
            exec_globals[safe_name] = gdf
        
        # Capturar salida
        output_buffer = io.StringIO()
        self.generated_maps = []
        self.generated_figures = []
        
        # Interceptar creación de mapas
        original_folium_map = folium.Map
        
        def capture_map(*args, **kwargs):
            m = original_folium_map(*args, **kwargs)
            self.generated_maps.append(m)
            return m
        
        exec_globals['folium'].Map = capture_map
        
        try:
            with contextlib.redirect_stdout(output_buffer):
                # Ejecutar código
                exec(code, exec_globals)
            
            # Buscar resultados relevantes
            result = None
            for var_name in ['resultado', 'result', 'output', 'mapa', 'map', 'gdf', 'df']:
                if var_name in exec_globals and exec_globals[var_name] is not None:
                    result = exec_globals[var_name]
                    break
            
            # Si hay un mapa en las variables, capturarlo
            for var_name, var_value in exec_globals.items():
                if isinstance(var_value, folium.Map) and var_value not in self.generated_maps:
                    self.generated_maps.append(var_value)
            
            return {
                "success": True,
                "error": None,
                "output": output_buffer.getvalue(),
                "result": result,
                "maps": self.generated_maps,
                "figures": self.generated_figures,
                "variables": {k: type(v).__name__ for k, v in exec_globals.items() 
                            if not k.startswith('_') and k not in self.ALLOWED_MODULES}
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"{type(e).__name__}: {str(e)}",
                "traceback": traceback.format_exc(),
                "output": output_buffer.getvalue(),
                "result": None,
                "maps": [],
                "figures": []
            }
        finally:
            # Restaurar folium.Map original
            exec_globals['folium'].Map = original_folium_map


class GeoProcessingTools:
    """
    Herramientas de geoprocesamiento predefinidas que el chat puede invocar.
    """
    
    @staticmethod
    def buffer(gdf: gpd.GeoDataFrame, distance: float, cap_style: int = 1) -> gpd.GeoDataFrame:
        """Crea buffer alrededor de geometrías"""
        result = gdf.copy()
        result['geometry'] = result.geometry.buffer(distance, cap_style=cap_style)
        return result
    
    @staticmethod
    def intersection(gdf1: gpd.GeoDataFrame, gdf2: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Intersección de dos capas"""
        return gpd.overlay(gdf1, gdf2, how='intersection')
    
    @staticmethod
    def union(gdf1: gpd.GeoDataFrame, gdf2: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Unión de dos capas"""
        return gpd.overlay(gdf1, gdf2, how='union')
    
    @staticmethod
    def difference(gdf1: gpd.GeoDataFrame, gdf2: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Diferencia entre dos capas"""
        return gpd.overlay(gdf1, gdf2, how='difference')
    
    @staticmethod
    def dissolve(gdf: gpd.GeoDataFrame, by: str = None, aggfunc: str = 'sum') -> gpd.GeoDataFrame:
        """Disuelve geometrías"""
        if by:
            return gdf.dissolve(by=by, aggfunc=aggfunc)
        return gdf.dissolve(aggfunc=aggfunc)
    
    @staticmethod
    def centroid(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Calcula centroides"""
        result = gdf.copy()
        result['geometry'] = result.geometry.centroid
        return result
    
    @staticmethod
    def convex_hull(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Calcula envolvente convexa"""
        result = gdf.copy()
        result['geometry'] = result.geometry.convex_hull
        return result
    
    @staticmethod
    def calculate_area(gdf: gpd.GeoDataFrame, column_name: str = 'area_m2') -> gpd.GeoDataFrame:
        """Calcula área en metros cuadrados"""
        result = gdf.copy()
        # Reproyectar a sistema métrico si es necesario
        if result.crs and result.crs.is_geographic:
            result_proj = result.to_crs(result.estimate_utm_crs())
            result[column_name] = result_proj.geometry.area
        else:
            result[column_name] = result.geometry.area
        return result
    
    @staticmethod
    def spatial_join(gdf1: gpd.GeoDataFrame, gdf2: gpd.GeoDataFrame, 
                     how: str = 'inner', predicate: str = 'intersects') -> gpd.GeoDataFrame:
        """Join espacial entre capas"""
        return gpd.sjoin(gdf1, gdf2, how=how, predicate=predicate)
    
    @staticmethod
    def clip(gdf: gpd.GeoDataFrame, mask: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Recorta una capa con otra"""
        return gpd.clip(gdf, mask)
    
    @staticmethod
    def create_map(gdf: gpd.GeoDataFrame, 
                   column: str = None,
                   cmap: str = 'viridis',
                   style: str = 'default',
                   tiles: str = 'OpenStreetMap') -> folium.Map:
        """
        Crea un mapa interactivo con Folium.
        
        Args:
            gdf: GeoDataFrame a visualizar
            column: Columna para colorear (opcional)
            cmap: Paleta de colores
            style: Estilo del mapa
            tiles: Proveedor de tiles
        """
        # Asegurar CRS WGS84
        if gdf.crs and gdf.crs != 'EPSG:4326':
            gdf = gdf.to_crs('EPSG:4326')
        
        # Calcular centro y bounds
        bounds = gdf.total_bounds
        center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
        
        # Crear mapa base
        m = folium.Map(location=center, tiles=tiles)
        
        # Ajustar zoom a bounds
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
        
        # Agregar capa
        if column and column in gdf.columns:
            # Mapa coroplético
            folium.Choropleth(
                geo_data=gdf.__geo_interface__,
                data=gdf,
                columns=[gdf.index.name or 'index', column],
                key_on='feature.id',
                fill_color=cmap,
                fill_opacity=0.7,
                line_opacity=0.8,
                legend_name=column
            ).add_to(m)
        else:
            # Mapa simple
            folium.GeoJson(
                gdf,
                style_function=lambda x: {
                    'fillColor': '#3388ff',
                    'color': '#000000',
                    'weight': 1,
                    'fillOpacity': 0.5
                }
            ).add_to(m)
        
        return m


def generate_geoprocessing_code(operation: str, params: Dict[str, Any]) -> str:
    """
    Genera código Python para operaciones de geoprocesamiento.
    Útil para que el chat genere código ejecutable.
    """
    templates = {
        'buffer': '''
# Buffer de {distance} metros a la capa {layer}
resultado = capas['{layer}'].copy()
if resultado.crs.is_geographic:
    resultado = resultado.to_crs(resultado.estimate_utm_crs())
resultado['geometry'] = resultado.geometry.buffer({distance})
resultado = resultado.to_crs('EPSG:4326')
print(f"Buffer creado: {{len(resultado)}} elementos")
''',
        'intersection': '''
# Intersección entre {layer1} y {layer2}
capa1 = capas['{layer1}']
capa2 = capas['{layer2}']
resultado = gpd.overlay(capa1, capa2, how='intersection')
print(f"Intersección: {{len(resultado)}} elementos resultantes")
''',
        'area': '''
# Calcular área de {layer}
resultado = capas['{layer}'].copy()
if resultado.crs.is_geographic:
    resultado_proj = resultado.to_crs(resultado.estimate_utm_crs())
    resultado['area_m2'] = resultado_proj.geometry.area
    resultado['area_ha'] = resultado['area_m2'] / 10000
else:
    resultado['area_m2'] = resultado.geometry.area
    resultado['area_ha'] = resultado['area_m2'] / 10000
print(f"Área total: {{resultado['area_ha'].sum():.2f}} hectáreas")
''',
        'map': '''
# Crear mapa de {layer}
capa = capas['{layer}']
if capa.crs != 'EPSG:4326':
    capa = capa.to_crs('EPSG:4326')

bounds = capa.total_bounds
center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]

mapa = folium.Map(location=center, tiles='{tiles}')
mapa.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

folium.GeoJson(
    capa,
    style_function=lambda x: {{
        'fillColor': '{color}',
        'color': '#000000',
        'weight': 1,
        'fillOpacity': 0.6
    }}
).add_to(mapa)

resultado = mapa
'''
    }
    
    if operation in templates:
        return templates[operation].format(**params)
    
    return f"# Operación '{operation}' no reconocida"
