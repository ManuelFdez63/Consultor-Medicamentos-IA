import streamlit as st
import requests
import os
from bs4 import BeautifulSoup
from groq import Groq
from dotenv import load_dotenv

# --- 1. CONFIGURACIÓN INICIAL ---
load_dotenv()
st.set_page_config(page_title="Farmacéutico IA", page_icon="💊", layout="wide")

# Verificación API Key
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    st.error("❌ No se detectó la API Key de Groq. Configura tu archivo .env")
    st.stop()

client = Groq(api_key=api_key)

# --- 2. GESTIÓN DE ESTADO (MEMORIA) ---
# Streamlit se reinicia con cada interacción, así que guardamos todo en session_state

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []  # Aquí guardamos el historial del chat

if "resultados_busqueda" not in st.session_state:
    st.session_state.resultados_busqueda = []

if "prospecto_actual" not in st.session_state:
    st.session_state.prospecto_actual = ""

if "medicamento_seleccionado" not in st.session_state:
    st.session_state.medicamento_seleccionado = None

# --- 3. FUNCIONES DE BACKEND ---

@st.cache_data(show_spinner=False)
def buscar_en_cima(nombre):
    """Busca medicamentos en la API de la AEMPS."""
    try:
        url = "https://cima.aemps.es/cima/rest/medicamentos"
        params = {"nombre": nombre, "tamanioPagina": 50}
        r = requests.get(url, params=params, timeout=5)
        return r.json().get("resultados", [])
    except:
        return []

@st.cache_data(show_spinner=False)
def obtener_prospecto(nregistro):
    """Descarga y limpia el HTML del prospecto."""
    try:
        url = f"https://cima.aemps.es/cima/dochtml/p/{nregistro}/P_{nregistro}.html"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            for tag in soup(["script", "style", "header", "footer", "nav"]):
                tag.decompose()
            return soup.get_text(separator="\n", strip=True)[:15000] # Limitamos caracteres
    except:
        return None
    return None

def limpiar_chat():
    st.session_state.mensajes = []
    st.session_state.prospecto_actual = ""

# --- 4. INTERFAZ: BARRA LATERAL (Búsqueda) ---
with st.sidebar:
    st.header("🔍 Buscador CIMA")
    
    query = st.text_input("Nombre del medicamento", placeholder="Ej: Ibuprofeno")
    tipo_filtro = st.radio("Filtro:", ["Todos", "Genérico (EFG)", "Marca"], horizontal=True)
    
    if st.button("Buscar Medicamento", use_container_width=True):
        if query:
            with st.spinner("Conectando con AEMPS..."):
                res = buscar_en_cima(query)
                st.session_state.resultados_busqueda = res
                # Limpiamos selección anterior al buscar de nuevo
                st.session_state.medicamento_seleccionado = None 
                limpiar_chat()
        else:
            st.warning("Escribe un nombre.")

    # Lógica de filtrado y selección
    resultados = st.session_state.resultados_busqueda
    
    if resultados:
        # Aplicar filtro visual
        if tipo_filtro == "Genérico (EFG)":
            opciones = [m for m in resultados if "EFG" in m['nombre'].upper()]
        elif tipo_filtro == "Marca":
            opciones = [m for m in resultados if "EFG" not in m['nombre'].upper()]
        else:
            opciones = resultados
        
        st.success(f"Encontrados: {len(opciones)}")
        
        # Crear diccionario para el selectbox: "Nombre Med" -> Objeto Med
        mapa_nombres = {f"{m['nombre']} ({m['labtitular']})": m for m in opciones}
        
        seleccion = st.selectbox(
            "Selecciona la presentación exacta:", 
            options=list(mapa_nombres.keys()),
            index=None,
            placeholder="Elige uno..."
        )

        if seleccion:
            med_obj = mapa_nombres[seleccion]
            
            # Si cambiamos de medicamento, recargamos prospecto y borramos chat
            if st.session_state.medicamento_seleccionado != med_obj['nregistro']:
                st.session_state.medicamento_seleccionado = med_obj['nregistro']
                with st.spinner("Descargando prospecto oficial..."):
                    texto = obtener_prospecto(med_obj['nregistro'])
                    if texto:
                        st.session_state.prospecto_actual = texto
                        st.session_state.mensajes = [] # Reset chat
                        st.toast("Prospecto cargado correctamente", icon="✅")
                    else:
                        st.error("Este medicamento no tiene prospecto en texto.")
                        st.session_state.prospecto_actual = ""
    
    st.divider()
    if st.button("🗑️ Borrar Historial de Chat"):
        st.session_state.mensajes = []
        st.rerun()

# --- 5. INTERFAZ: ÁREA PRINCIPAL (Chat) ---

st.title("🏥 Asistente Farmacéutico IA")
st.caption("Consulta dudas sobre posología, efectos secundarios y contraindicaciones basadas en el prospecto oficial.")

# Verificamos si hay un prospecto cargado para habilitar el chat
if st.session_state.prospecto_actual:
    
    # 1. Mostrar historial de mensajes
    for mensaje in st.session_state.mensajes:
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

    # 2. Input del usuario
    if prompt := st.chat_input("Escribe tu duda (ej: ¿Puedo tomarlo si estoy embarazada?)"):
        
        # Mostrar mensaje del usuario
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.mensajes.append({"role": "user", "content": prompt})

        # 3. Generar respuesta con Groq
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                # Construcción del prompt con memoria + contexto
                mensajes_api = [
                    {
                        "role": "system", 
                        "content": (
                            "Eres un farmacéutico experto y amable. Responde a las preguntas basándote EXCLUSIVAMENTE "
                            "en el prospecto proporcionado a continuación. Si la información no está en el texto, indícalo. "
                            "Mantén el contexto de la conversación.\n\n"
                            f"--- PROSPECTO OFICIAL ---\n{st.session_state.prospecto_actual}"
                        )
                    }
                ]
                
                # Añadir historial reciente (últimos 10 mensajes para no saturar)
                mensajes_api.extend(st.session_state.mensajes[-10:])
                
                # Llamada Streaming para efecto "escribiendo"
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=mensajes_api,
                    temperature=0.2,
                    stream=True
                )
                
                # Procesar stream
                for chunk in completion:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                
                # Guardar respuesta en memoria
                st.session_state.mensajes.append({"role": "assistant", "content": full_response})

            except Exception as e:
                st.error(f"Error conectando con Groq: {e}")

else:
    # Pantalla de bienvenida si no hay medicamento
    st.info("👈 **Para empezar:** Busca un medicamento en la barra lateral y selecciónalo.")
    st.markdown("""
    **¿Cómo funciona?**
    1. Escribe el nombre (ej: *Paracetamol*) en el menú de la izquierda.
    2. Filtra si quieres Genérico o Marca.
    3. Selecciona la caja exacta.
    4. **¡Chatea!** La IA leerá el prospecto y responderá tus dudas recordando el contexto.
    """)