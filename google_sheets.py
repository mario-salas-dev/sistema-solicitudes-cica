"""Integración con Google Sheets.

- importar_respuestas(): trae las filas nuevas del formulario a la base de datos.
- exportar_seguimiento(): escribe el estado actual de todas las solicitudes en
  la pestaña 'Seguimiento' para que el equipo lo consulte sin abrir Python.

Requiere una cuenta de servicio de Google Cloud (ver README) y compartir la hoja
con el correo de esa cuenta de servicio.
"""
import unicodedata
from datetime import date, datetime

import config
import servicio


def _normalizar(texto):
    """Quita tildes, espacios extra y pasa a minúsculas, para comparar encabezados
    sin que un acento o un espacio de más rompa la coincidencia."""
    texto = unicodedata.normalize("NFKD", str(texto).strip().lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _fila_normalizada(fila):
    """Convierte las claves de una fila (tal como las da gspread) a su forma
    normalizada, para poder buscarlas sin depender de tildes exactas."""
    return {_normalizar(clave): valor for clave, valor in fila.items()}


def _valor(fila_norm, nombre_columna):
    return str(fila_norm.get(_normalizar(nombre_columna), "")).strip()

ENCABEZADOS_SEGUIMIENTO = [
    "Código", "Fecha", "Solicitante", "Correo", "Tipo de solicitante",
    "Tipo de solicitud", "Descripción", "Estado", "Responsable",
    "Fecha límite", "En espera", "Motivo de espera", "Respuesta", "Fecha cierre",
]


def _abrir_libro():
    import gspread  # se importa aquí para no exigirlo si no se usa Sheets

    if not config.GOOGLE_SHEET_ID:
        raise RuntimeError("Falta GOOGLE_SHEET_ID en el archivo .env")
    cliente = gspread.service_account(filename=config.GOOGLE_CREDENCIALES)
    return cliente.open_by_key(config.GOOGLE_SHEET_ID)


def _parsear_fecha(texto):
    """Convierte la 'Marca temporal' del formulario a date (hoy si no se reconoce)."""
    texto = str(texto).strip()
    for formato in config.FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return date.today()


def importar_respuestas(usuario="sistema"):
    """Importa las respuestas nuevas. Devuelve la lista de solicitudes creadas."""
    hoja = _abrir_libro().worksheet(config.HOJA_RESPUESTAS)
    col = config.COLUMNAS_FORM
    creadas = []

    for fila in hoja.get_all_records():
        fila_norm = _fila_normalizada(fila)
        marca = _valor(fila_norm, col["fecha"])
        correo = _valor(fila_norm, col["correo"])
        if not marca:
            continue  # fila vacía

        solicitud = servicio.crear_solicitud(
            solicitante=_valor(fila_norm, col["solicitante"]) or correo,
            tipo_solicitud=_valor(fila_norm, col["tipo_solicitud"]),
            descripcion=_valor(fila_norm, col["descripcion"]),
            correo=correo,
            tipo_solicitante=_valor(fila_norm, col["tipo_solicitante"]),
            origen=f"{marca}|{correo}",  # evita importar dos veces la misma fila
            fecha_creacion=_parsear_fecha(marca),
            usuario=usuario,
        )
        if solicitud:
            creadas.append(solicitud)
    return creadas


def exportar_seguimiento():
    """Reescribe la pestaña 'Seguimiento' con el estado actual. Devuelve nº de filas."""
    import gspread

    libro = _abrir_libro()
    try:
        hoja = libro.worksheet(config.HOJA_SEGUIMIENTO)
    except gspread.WorksheetNotFound:
        hoja = libro.add_worksheet(config.HOJA_SEGUIMIENTO, rows=500,
                                   cols=len(ENCABEZADOS_SEGUIMIENTO))

    solicitudes = servicio.listar()
    datos = [ENCABEZADOS_SEGUIMIENTO]
    for s in solicitudes:
        datos.append([
            s["codigo"], s["fecha_creacion"], s["solicitante"], s["correo"] or "",
            s["tipo_solicitante"] or "", s["tipo_solicitud"], s["descripcion"] or "",
            s["estado"], s["responsable"] or "", s["fecha_limite"] or "",
            "Sí" if s["en_espera"] else "No", s["motivo_espera"] or "",
            s["respuesta"] or "", s["fecha_cierre"] or "",
        ])

    hoja.clear()
    hoja.update(range_name="A1", values=datos)
    hoja.freeze(rows=1)
    return len(solicitudes)
