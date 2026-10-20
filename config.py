"""Configuración central del sistema de solicitudes del CICA.

Aquí se ajustan los estados, los plazos, los responsables por tipo de
solicitud y los nombres de las columnas del formulario de Google.
Los datos sensibles (claves, correos) se leen del archivo .env.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv es opcional
    pass

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("CICA_DB", BASE_DIR / "solicitudes.db"))

# --------------------------------------------------------------------------
# Flujo de estados
# --------------------------------------------------------------------------
ESTADOS = ["Recibida", "En revisión", "En proceso", "Finalizada"]

TRANSICIONES = {
    "Recibida": ["En revisión"],
    "En revisión": ["En proceso"],
    "En proceso": ["Finalizada"],
    "Finalizada": [],
}

# Días máximos que una solicitud puede permanecer en cada estado
PLAZOS_ESTADO = {"Recibida": 2, "En revisión": 3, "En proceso": 7}

# Días máximos esperando información del solicitante antes de generar alerta
DIAS_MAX_ESPERA = 5

# --------------------------------------------------------------------------
# Tipos de solicitud: responsable por defecto y días para la fecha límite
# (cambia los nombres y correos por los reales del CICA)
# --------------------------------------------------------------------------
TIPOS_SOLICITUD = {
    "Certificados": {
        "responsable": "MARIO FERNANDO SALAS",
        "correo": "mfsalas@udenar.edu.co",
        "dias": 5,
    },
    "Solicitud de información": {
        "responsable": "ALEJANDRA RUANO",
        "correo": "cicagrarias@udenar.edu.co",
        "dias": 5,
    },
    "Publicación de noticias": {
        "responsable": "MARIO FERNANDO SALAS",
        "correo": "mfsalas@udenar.edu.co",
        "dias": 7,
    },
    "Actualización de docentes": {
        "responsable": "ALEJANDRA RUANO",
        "correo": "cicagrarias@udenar.edu.co",
        "dias": 10,
    },
    "Solicitud de equipos": {
        "responsable": "MARIO FERNANDO SALAS",
        "correo": "mfsalas@udenar.edu.co",
        "dias": 8,
    },
    "Documentos para procesos académicos": {
        "responsable": "ALEJANDRA RUANO",
        "correo": "cicagrarias@udenar.edu.co",
        "dias": 7,
    },
    "Petición de grupo de investigación": {
        "responsable": "HUGO FERNEY",
        "correo": "cicagrarias@udenar.edu.co",
        "dias": 10,
    },
    "Otra": {
        "responsable": "HUGO FERNEY",
        "correo": "cicagrarias@udenar.edu.co",
        "dias": 7,
    },
}
TIPO_POR_DEFECTO = "Otra"

# Correo que recibe el resumen de todas las alertas (opcional)
CORREO_COORDINADOR = os.getenv("CORREO_COORDINADOR", "")

# --------------------------------------------------------------------------
# Google Sheets (fase 1: el formulario de Google guarda en una hoja)
# --------------------------------------------------------------------------
GOOGLE_CREDENCIALES = os.getenv("GOOGLE_CREDENCIALES", "credenciales.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
HOJA_RESPUESTAS = os.getenv("HOJA_RESPUESTAS", "Respuestas de formulario 1")
HOJA_SEGUIMIENTO = os.getenv("HOJA_SEGUIMIENTO", "Seguimiento")

# Nombre de cada columna tal como aparece en la hoja de respuestas del formulario
COLUMNAS_FORM = {
    "fecha": "Marca temporal",
    "solicitante": "Nombre del solicitante",
    "correo": "Correo electrónico",
    "tipo_solicitante": "Tipo de solicitante",
    "tipo_solicitud": "Tipo de solicitud",
    "descripcion": "Descripción de la solicitud",
}

# Formatos posibles de la "Marca temporal" (depende de la región de la hoja)
FORMATOS_FECHA = [
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]
