"""
GeoIA Territorial v3.0 - Data Store Centralizado
=================================================
Este módulo es el NÚCLEO de la interconexión entre todos los componentes.
Cuando se carga la base de conocimiento, todos los módulos se sincronizan automáticamente.
"""

import streamlit as st
import geopandas as gpd
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib


@dataclass
class LayerInfo:
    """Información de una capa geoespacial"""
    name: str
    path: Path
    format: str
    geometry_type: Optional[str] = None
    crs: Optional[str] = None
    feature_count: int = 0
    columns: List[str] = field(default_factory=list)
    bounds: Optional[tuple] = None
    loaded: bool = False
    gdf: Optional[gpd.GeoDataFrame] = None
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": str(self.path),
            "format": self.format,
            "geometry_type": self.geometry_type,
            "crs": self.crs,
            "feature_count": self.feature_count,
            "columns": self.columns,
            "bounds": self.bounds,
            "loaded": self.loaded
        }


@dataclass
class DocumentInfo:
    """Información de un documento"""
    name: str
    path: Path
    format: str
    size_kb: float = 0
    content_preview: str = ""
    extracted_text: Optional[str] = None


class GeoDataStore:
    """
    Store centralizado para gestión de datos geoespaciales.
    Actúa como el bus de comunicación entre todos los módulos.
    """
    
    LAYER_EXTENSIONS = {'.shp', '.geojson', '.gpkg', '.kml', '.gml', '.json'}
    DOC_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt', '.md', '.csv', '.xlsx'}
    MAP_EXTENSIONS = {'.qgz', '.qgs', '.qml', '.sld'}
    
    def __init__(self):
        self.root_path: Optional[Path] = None
        self.layers: Dict[str, LayerInfo] = {}
        self.documents: Dict[str, DocumentInfo] = {}
        self.maps: Dict[str, Path] = {}
        self.is_connected: bool = False
        self.last_scan: Optional[datetime] = None
        self._observers: List[Callable] = []
        
    def connect(self, path: str) -> Dict[str, Any]:
        """
        Conecta una carpeta como base de conocimiento.
        Escanea y prepara toda la información para los módulos.
        """
        root = Path(path)
        
        if not root.exists():
            return {"success": False, "error": f"La carpeta no existe: {path}"}
        
        self.root_path = root
        self.layers = {}
        self.documents = {}
        self.maps = {}
        
        # Escanear estructura
        scan_result = self._scan_folder(root)
        
        self.is_connected = True
        self.last_scan = datetime.now()
        
        # Notificar a todos los observadores (módulos)
        self._notify_observers("connected", scan_result)
        
        return {
            "success": True,
            "summary": scan_result,
            "timestamp": self.last_scan.isoformat()
        }
    
    def _scan_folder(self, root: Path) -> Dict[str, int]:
        """Escanea recursivamente la carpeta"""
        
        # Buscar capas
        capas_folder = root / "capas"
        if capas_folder.exists():
            self._scan_layers(capas_folder)
        else:
            # Buscar en raíz también
            self._scan_layers(root)
        
        # Buscar documentos
        docs_folder = root / "documentos"
        if docs_folder.exists():
            self._scan_documents(docs_folder)
        else:
            self._scan_documents(root)
            
        # Buscar mapas QGIS
        maps_folder = root / "mapas"
        if maps_folder.exists():
            self._scan_maps(maps_folder)
        else:
            self._scan_maps(root)
            
        return {
            "capas": len(self.layers),
            "documentos": len(self.documents),
            "mapas": len(self.maps)
        }
    
    def _scan_layers(self, folder: Path):
        """Escanea capas geoespaciales"""
        processed_shapefiles = set()
        
        for file in folder.rglob("*"):
            if file.suffix.lower() in self.LAYER_EXTENSIONS:
                # Evitar duplicados de shapefile
                if file.suffix.lower() == '.shp':
                    base_name = file.stem
                    if base_name in processed_shapefiles:
                        continue
                    processed_shapefiles.add(base_name)
                
                layer_info = self._analyze_layer(file)
                if layer_info:
                    self.layers[layer_info.name] = layer_info
    
    def _analyze_layer(self, file: Path) -> Optional[LayerInfo]:
        """Analiza metadatos de una capa sin cargarla completamente"""
        try:
            # Lectura rápida solo de metadatos
            gdf = gpd.read_file(file, rows=1)
            
            # Obtener conteo real
            if file.suffix.lower() == '.shp':
                import fiona
                with fiona.open(file) as src:
                    count = len(src)
            else:
                # Para otros formatos, lectura completa
                gdf_full = gpd.read_file(file)
                count = len(gdf_full)
            
            bounds = None
            try:
                gdf_bounds = gpd.read_file(file)
                total_bounds = gdf_bounds.total_bounds
                bounds = tuple(total_bounds)
            except:
                pass
            
            return LayerInfo(
                name=file.stem,
                path=file,
                format=file.suffix.lower().replace('.', ''),
                geometry_type=gdf.geometry.geom_type.iloc[0] if len(gdf) > 0 else None,
                crs=str(gdf.crs) if gdf.crs else None,
                feature_count=count,
                columns=[c for c in gdf.columns if c != 'geometry'],
                bounds=bounds
            )
        except Exception as e:
            # Si falla el análisis, crear info básica
            return LayerInfo(
                name=file.stem,
                path=file,
                format=file.suffix.lower().replace('.', '')
            )
    
    def _scan_documents(self, folder: Path):
        """Escanea documentos"""
        for file in folder.rglob("*"):
            if file.suffix.lower() in self.DOC_EXTENSIONS and file.is_file():
                self.documents[file.stem] = DocumentInfo(
                    name=file.stem,
                    path=file,
                    format=file.suffix.lower().replace('.', ''),
                    size_kb=file.stat().st_size / 1024
                )
    
    def _scan_maps(self, folder: Path):
        """Escanea proyectos de mapas"""
        for file in folder.rglob("*"):
            if file.suffix.lower() in self.MAP_EXTENSIONS:
                self.maps[file.stem] = file
    
    def load_layer(self, layer_name: str) -> Optional[gpd.GeoDataFrame]:
        """Carga una capa específica en memoria"""
        if layer_name not in self.layers:
            return None
        
        layer = self.layers[layer_name]
        
        if layer.gdf is not None:
            return layer.gdf
        
        try:
            gdf = gpd.read_file(layer.path)
            layer.gdf = gdf
            layer.loaded = True
            
            # Notificar que se cargó una capa
            self._notify_observers("layer_loaded", {"name": layer_name, "gdf": gdf})
            
            return gdf
        except Exception as e:
            return None
    
    def load_all_layers(self) -> Dict[str, gpd.GeoDataFrame]:
        """Carga todas las capas en memoria"""
        loaded = {}
        for name in self.layers:
            gdf = self.load_layer(name)
            if gdf is not None:
                loaded[name] = gdf
        return loaded
    
    def get_layer_names(self) -> List[str]:
        """Retorna lista de nombres de capas disponibles"""
        return list(self.layers.keys())
    
    def get_layer_info(self, layer_name: str) -> Optional[Dict]:
        """Retorna información de una capa"""
        if layer_name in self.layers:
            return self.layers[layer_name].to_dict()
        return None
    
    def get_all_layers_info(self) -> List[Dict]:
        """Retorna información de todas las capas"""
        return [layer.to_dict() for layer in self.layers.values()]
    
    def get_context_for_chat(self) -> str:
        """
        Genera contexto estructurado para el Chat Inteligente.
        Incluye información sobre capas, documentos y mapas disponibles.
        """
        if not self.is_connected:
            return ""
        
        context_parts = []
        
        # Información de capas
        if self.layers:
            context_parts.append("=== CAPAS GEOESPACIALES DISPONIBLES ===")
            for name, layer in self.layers.items():
                layer_desc = f"""
📍 **{name}** ({layer.format.upper()})
   - Geometría: {layer.geometry_type or 'No determinado'}
   - CRS: {layer.crs or 'No definido'}
   - Elementos: {layer.feature_count}
   - Columnas: {', '.join(layer.columns[:10])}{'...' if len(layer.columns) > 10 else ''}
   - Ruta: {layer.path}
"""
                context_parts.append(layer_desc)
        
        # Información de documentos
        if self.documents:
            context_parts.append("\n=== DOCUMENTOS DISPONIBLES ===")
            for name, doc in self.documents.items():
                context_parts.append(f"📄 {name}.{doc.format} ({doc.size_kb:.1f} KB)")
        
        # Información de mapas
        if self.maps:
            context_parts.append("\n=== PROYECTOS QGIS ===")
            for name, path in self.maps.items():
                context_parts.append(f"🗺️ {name} ({path.suffix})")
        
        return "\n".join(context_parts)
    
    def get_summary(self) -> Dict[str, Any]:
        """Resumen general del store"""
        return {
            "connected": self.is_connected,
            "root_path": str(self.root_path) if self.root_path else None,
            "total_capas": len(self.layers),
            "total_documentos": len(self.documents),
            "total_mapas": len(self.maps),
            "capas_cargadas": sum(1 for l in self.layers.values() if l.loaded),
            "last_scan": self.last_scan.isoformat() if self.last_scan else None
        }
    
    # Sistema de observadores para notificaciones entre módulos
    def add_observer(self, callback: Callable):
        """Registra un observador para recibir notificaciones"""
        self._observers.append(callback)
    
    def _notify_observers(self, event: str, data: Any):
        """Notifica a todos los observadores de un evento"""
        for observer in self._observers:
            try:
                observer(event, data)
            except:
                pass


def get_store() -> GeoDataStore:
    """
    Obtiene la instancia global del store.
    Se almacena en st.session_state para persistencia.
    """
    if "geo_store" not in st.session_state:
        st.session_state.geo_store = GeoDataStore()
    return st.session_state.geo_store


def init_store():
    """Inicializa el store si no existe"""
    get_store()
