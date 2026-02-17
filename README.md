# 💊 Agente de Consulta de Prospectos (AEMPS)

Este proyecto es un **asistente farmacéutico inteligente** que utiliza la API oficial de la AEMPS (CIMA) para obtener prospectos actualizados y procesarlos mediante Inteligencia Artificial.



## 🚀 Características
- **Búsqueda en Tiempo Real:** Conexión directa con la API de CIMA para obtener datos actualizados de medicamentos.
- **Memoria de Contexto:** El agente recuerda alergias o condiciones mencionadas previamente por el usuario.
- **Resúmenes Inteligentes:** Utiliza el modelo **Llama 3.3** (vía Groq) para extraer dosis y advertencias de forma clara.
- **Interfaz Streamlit:** Panel visual e interactivo para una mejor experiencia de usuario.

## 🛠️ Stack Tecnológico
- **Lenguaje:** Python 3.x
- **Frontend:** Streamlit
- **IA/LLM:** Groq (Llama-3.3-70b-versatile)
- **Extracción de Datos:** BeautifulSoup4 & Requests
- **Gestión de Entorno:** Dotenv

## ⚙️ Instalación y Uso

1. **Clonar el repo:**
   ```bash
   git clone [https://github.com/tu-usuario/tu-repo.git](https://github.com/tu-usuario/tu-repo.git)
   cd tu-repo
