"""Envío de correos por SMTP.

Si SMTP no está configurado en el .env, el envío solo se simula en consola,
así puedes probar todo el sistema sin enviar correos reales.
"""
import os
import smtplib
from collections import defaultdict
from email.message import EmailMessage

import config


def _smtp_configurado():
    return all(os.getenv(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))


def enviar_correo(destino, asunto, cuerpo):
    """Envía un correo. Devuelve True solo si se envió de verdad."""
    if not destino:
        return False

    if not _smtp_configurado():
        print(f"[SIMULADO] Para: {destino} | Asunto: {asunto}")
        return False

    msg = EmailMessage()
    msg["From"] = os.getenv("SMTP_REMITENTE", os.getenv("SMTP_USER"))
    msg["To"] = destino
    msg["Subject"] = asunto
    msg.set_content(cuerpo)

    try:
        with smtplib.SMTP(
            os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", "587")), timeout=30
        ) as smtp:
            smtp.starttls()
            smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            smtp.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError) as error:
        print(f"[ERROR] No se pudo enviar el correo a {destino}: {error}")
        return False


# --------------------------------------------------------------------------
# Mensajes al solicitante
# --------------------------------------------------------------------------
def notificar_recepcion(s):
    cuerpo = (
        f"Hola {s['solicitante']},\n\n"
        f"Recibimos tu solicitud de tipo '{s['tipo_solicitud']}'.\n"
        f"Código de seguimiento: {s['codigo']}\n"
        f"Fecha estimada de respuesta: {s['fecha_limite']}\n\n"
        "Te avisaremos cuando cambie de estado.\n\nCICA"
    )
    return enviar_correo(s["correo"], f"[{s['codigo']}] Solicitud recibida", cuerpo)


def notificar_cambio_estado(s):
    cuerpo = (
        f"Hola {s['solicitante']},\n\n"
        f"Tu solicitud {s['codigo']} ({s['tipo_solicitud']}) ahora está: {s['estado']}.\n"
    )
    if s["estado"] == "Finalizada" and s["respuesta"]:
        cuerpo += f"\nRespuesta:\n{s['respuesta']}\n"
    cuerpo += "\nCICA"
    return enviar_correo(s["correo"], f"[{s['codigo']}] Estado: {s['estado']}", cuerpo)


def notificar_espera(s):
    cuerpo = (
        f"Hola {s['solicitante']},\n\n"
        f"Para continuar con tu solicitud {s['codigo']} necesitamos tu ayuda:\n"
        f"{s['motivo_espera']}\n\n"
        "Responde a este correo con la información solicitada.\n\nCICA"
    )
    return enviar_correo(s["correo"], f"[{s['codigo']}] Necesitamos más información", cuerpo)


# --------------------------------------------------------------------------
# Alertas internas
# --------------------------------------------------------------------------
def _texto_alertas(alertas):
    lineas = ["Solicitudes que requieren atención:\n"]
    for a in alertas:
        lineas.append(f"- {a['codigo']} | {a['tipo_solicitud']} | {a['estado']} "
                      f"| Responsable: {a['responsable']}")
        for motivo in a["motivos"]:
            lineas.append(f"    * {motivo}")
    return "\n".join(lineas)


def enviar_alertas(alertas):
    """Envía a cada responsable sus alertas y al coordinador el resumen completo."""
    if not alertas:
        return

    por_responsable = defaultdict(list)
    for a in alertas:
        if a["correo_responsable"]:
            por_responsable[a["correo_responsable"]].append(a)

    for destino, items in por_responsable.items():
        enviar_correo(destino, f"CICA: {len(items)} solicitud(es) con alerta",
                      _texto_alertas(items))

    if config.CORREO_COORDINADOR:
        enviar_correo(config.CORREO_COORDINADOR,
                      f"CICA: resumen de alertas ({len(alertas)})",
                      _texto_alertas(alertas))
