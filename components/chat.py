"""
GeoIA Territorial v3.0 - Chat Inteligente
==========================================
Chat con capacidad de:
- Reconocer capas de la Base de Conocimiento
- Ejecutar código GeoPandas en vivo
- Generar mapas interactivos
"""

import streamlit as st
import google.generativeai as genai
from streamlit_folium import st_folium
import folium
import geopandas as gpd
import re
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_store import get_store
from core.execution_engine import CodeExecutionEngine, generate_geoprocessing_code


# Prompts del sistema por modo
SYSTEM_PROMPTS = {
    "general": """Eres GeoIA, un asistente experto en análisis geoespacial y ordenamiento territorial.
    
Tu especialidad incluye:
- Análisis espacial con GeoPandas y herramientas GIS
- Ordenamiento territorial y normativa urbana
- Visualización cartográfica
- Ciencia de datos espaciales

IMPORTANTE - CAPACIDADES DE CÓDIGO:
Cuando el usuario solicite análisis, cálculos o mapas sobre las capas disponibles:
1. Puedes generar código Python/GeoPandas ejecutable
2. El código se ejecutará automáticamente
3. Los mapas generados se mostrarán en vivo

Para generar código ejecutable, usa el formato:
```python
# Tu código aquí
resultado = ...  # La variable 'resultado' se mostrará al usuario
mapa = folium.Map(...)  # Los mapas folium se renderizarán automáticamente
```

Las capas están disponibles en el diccionario `capas` o `layers`:
- capas['nombre_capa'] retorna un GeoDataFrame

Responde siempre en español y sé preciso en tus análisis técnicos.
""",

    "analista": """Eres un Analista Territorial Senior con experiencia en:
- Estudios de ordenamiento territorial
- Análisis de uso del suelo
- Evaluación de aptitud territorial
- Indicadores urbanos y rurales

Cuando analices datos, genera código GeoPandas para cálculos precisos.
Las capas están en: capas['nombre'] o layers['nombre']
""",

    "cartografo": """Eres un Cartógrafo Profesional especializado en:
- Diseño cartográfico
- Simbología y representación visual
- Sistemas de referencia espacial
- Producción de mapas temáticos

Genera mapas con Folium cuando el usuario lo solicite.
Las capas están disponibles en: capas['nombre']

Ejemplo de mapa:
```python
capa = capas['nombre_capa'].to_crs('EPSG:4326')
bounds = capa.total_bounds
center = [(bounds[1]+bounds[3])/2, (bounds[0]+bounds[2])/2]
mapa = folium.Map(location=center)
mapa.fit_bounds([[bounds[1],bounds[0]], [bounds[3],bounds[2]]])
folium.GeoJson(capa).add_to(mapa)
resultado = mapa
```
""",

    "pot": """Eres un Consultor de Planes de Ordenamiento Territorial (POT) experto en:
- Normativa urbana colombiana
- Componentes del POT (general, urbano, rural)
- Clasificación del suelo
- Tratamientos urbanísticos

Puedes analizar capas geoespaciales relacionadas con POT usando código GeoPandas.
""",

    "cientifico": """Eres un Científico de Datos Espaciales especializado en:
- Machine Learning geoespacial
- Análisis estadístico espacial
- Big Data geográfico
- Modelamiento predictivo territorial

Genera código Python avanzado para análisis complejos.
Usa las capas disponibles en: capas['nombre']
"""
}


def render_chat_interface(config: dict):
    """
    Renderiza la interfaz de chat con capacidades de ejecución de código.
    """
    store = get_store()
    
    # Indicador de modo
    mode = config.get("mode", "general")
    mode_names = {
        "general": "🌍 General",
        "analista": "📊 Analista Territorial", 
        "pot": "🏛️ Consultor POT",
        "cartografo": "🗺️ Cartógrafo",
        "cientifico": "🔬 Científico de Datos"
    }
    
    # Header del chat
    col_mode, col_status = st.columns([2, 3])
    
    with col_mode:
        st.markdown(f"**Modo:** {mode_names.get(mode, '🌍 General')}")
    
    with col_status:
        if store.is_connected:
            layers_count = len(store.layers)
            loaded_count = sum(1 for l in store.layers.values() if l.loaded)
            st.markdown(f"📁 **{layers_count} capas** disponibles ({loaded_count} cargadas)")
        else:
            st.markdown("⚠️ *Sin base de conocimiento conectada*")
    
    st.markdown("---")
    
    # Contenedor de mensajes
    chat_container = st.container()
    
    with chat_container:
        # Mensaje de bienvenida
        if not st.session_state.get("messages"):
            render_welcome_message(store)
        
        # Historial de mensajes
        for msg in st.session_state.get("messages", []):
            render_message(msg)
    
    # Input del usuario
    user_input = st.chat_input(
        "Escribe tu consulta territorial o pide un análisis...",
        key="chat_input"
    )
    
    if user_input:
        process_user_message(user_input, config, store)


def render_welcome_message(store):
    """Renderiza mensaje de bienvenida con sugerencias"""
    
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 1rem;
    ">
        <h3 style="color: #166534; margin-bottom: 0.5rem;">👋 ¡Bienvenido a GeoIA Territorial v3!</h3>
        <p style="color: #15803d; margin: 0;">
            Ahora puedo ejecutar código GeoPandas y generar mapas en vivo
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sugerencias contextuales
    if store.is_connected and store.layers:
        layer_names = list(store.layers.keys())[:3]
        
        st.markdown("#### 💡 Prueba estas consultas:")
        
        suggestions = [
            f"Muéstrame un mapa de la capa {layer_names[0]}",
            f"Calcula el área total de {layer_names[0]}",
            "¿Qué capas tengo disponibles?",
            f"Haz un análisis estadístico de {layer_names[0]}"
        ]
        
        cols = st.columns(2)
        for i, suggestion in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
                    st.session_state.pending_message = suggestion
                    st.rerun()
    else:
        st.info("💡 Conecta una carpeta en 'Base de Conocimiento' para habilitar análisis avanzados")


def render_message(msg: dict):
    """Renderiza un mensaje del chat"""
    
    role = msg.get("role", "user")
    content = msg.get("content", "")
    
    with st.chat_message(role):
        st.markdown(content)
        
        # Renderizar código ejecutado
        if msg.get("code"):
            with st.expander("📝 Código ejecutado"):
                st.code(msg["code"], language="python")
        
        # Renderizar mapa generado
        if msg.get("map_html"):
            st.components.v1.html(msg["map_html"], height=400)
        
        # Renderizar resultado de datos
        if msg.get("result_df") is not None:
            with st.expander("📊 Datos resultantes"):
                st.dataframe(msg["result_df"], use_container_width=True)


def process_user_message(user_input: str, config: dict, store):
    """Procesa mensaje del usuario y genera respuesta"""
    
    # Agregar mensaje del usuario
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat()
    })
    
    # Mostrar mensaje del usuario
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Generar respuesta
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            response = generate_response(user_input, config, store)
        
        # Mostrar respuesta
        st.markdown(response["content"])
        
        # Si hay código, ejecutarlo
        if response.get("code"):
            execute_and_display_code(response["code"], store)
        
        # Guardar mensaje
        st.session_state.messages.append(response)


def generate_response(user_input: str, config: dict, store) -> dict:
    """Genera respuesta usando Gemini con contexto de las capas"""
    
    mode = config.get("mode", "general")
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["general"])
    
    # Construir contexto
    context_parts = [system_prompt]
    
    # Agregar información de capas disponibles
    if store.is_connected:
        context_parts.append("\n\n=== CAPAS DISPONIBLES ===")
        context_parts.append(store.get_context_for_chat())
    
    # Historial de conversación
    history = ""
    for msg in st.session_state.get("messages", [])[-6:]:  # Últimos 6 mensajes
        role = "Usuario" if msg["role"] == "user" else "Asistente"
        history += f"\n{role}: {msg['content'][:500]}"
    
    if history:
        context_parts.append(f"\n\n=== HISTORIAL RECIENTE ==={history}")
    
    # Construir prompt completo
    full_prompt = "\n".join(context_parts) + f"\n\nUsuario: {user_input}\n\nAsistente:"
    
    try:
        # Configurar Gemini
        api_key = config.get("api_key") or st.secrets.get("GOOGLE_API_KEY")
        
        if not api_key:
            return {
                "role": "assistant",
                "content": "⚠️ Por favor configura tu API Key de Google en el sidebar",
                "timestamp": datetime.now().isoformat()
            }
        
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel(
            config.get("model", "gemini-2.0-flash"),
            generation_config={
                "temperature": config.get("temperature", 0.7),
                "max_output_tokens": 4096
            }
        )
        
        response = model.generate_content(full_prompt)
        response_text = response.text
        
        # Detectar si hay código Python en la respuesta
        code_match = re.search(r'```python\s*(.*?)\s*```', response_text, re.DOTALL)
        
        result = {
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        }
        
        if code_match:
            result["code"] = code_match.group(1)
        
        return result
        
    except Exception as e:
        return {
            "role": "assistant",
            "content": f"❌ Error al generar respuesta: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


def execute_and_display_code(code: str, store):
    """Ejecuta código GeoPandas y muestra resultados"""
    
    with st.expander("📝 Código ejecutado", expanded=True):
        st.code(code, language="python")
    
    # Cargar todas las capas necesarias
    layers = {}
    for name in store.layers:
        gdf = store.load_layer(name)
        if gdf is not None:
            layers[name] = gdf
    
    # Crear motor de ejecución
    engine = CodeExecutionEngine(layers)
    
    # Ejecutar código
    with st.spinner("Ejecutando código..."):
        result = engine.execute(code)
    
    if result["success"]:
        # Mostrar output de print()
        if result["output"]:
            st.markdown("**Salida:**")
            st.text(result["output"])
        
        # Mostrar mapas generados
        if result["maps"]:
            st.markdown("**🗺️ Mapa generado:**")
            for i, m in enumerate(result["maps"]):
                # Renderizar mapa Folium
                map_html = m._repr_html_()
                st.components.v1.html(map_html, height=450)
        
        # Mostrar resultado si es DataFrame/GeoDataFrame
        if result["result"] is not None:
            if isinstance(result["result"], (gpd.GeoDataFrame, )):
                st.markdown("**📊 Resultado (GeoDataFrame):**")
                display_df = result["result"].drop(columns='geometry', errors='ignore')
                st.dataframe(display_df.head(20), use_container_width=True)
                st.caption(f"Mostrando 20 de {len(result['result'])} filas")
            
            elif isinstance(result["result"], folium.Map):
                st.markdown("**🗺️ Mapa:**")
                st.components.v1.html(result["result"]._repr_html_(), height=450)
            
            elif hasattr(result["result"], '__iter__') and not isinstance(result["result"], str):
                st.markdown("**Resultado:**")
                st.write(result["result"])
        
        st.success("✅ Código ejecutado exitosamente")
        
    else:
        st.error(f"❌ Error: {result['error']}")
        if result.get("traceback"):
            with st.expander("Ver detalles del error"):
                st.code(result["traceback"])


def init_chat_session():
    """Inicializa la sesión del chat"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "pending_message" not in st.session_state:
        st.session_state.pending_message = None


def clear_chat():
    """Limpia el historial del chat"""
    st.session_state.messages = []


def export_chat():
    """Exporta el historial del chat"""
    import json
    
    messages = st.session_state.get("messages", [])
    
    export_data = {
        "timestamp": datetime.now().isoformat(),
        "messages": messages
    }
    
    return json.dumps(export_data, indent=2, ensure_ascii=False)
