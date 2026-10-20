"""Sistema de control de solicitudes y trámites del CICA.

Uso:  python main.py <comando> [opciones]      (python main.py --help)
"""
import argparse
import getpass
import sys
from datetime import date, timedelta

import base_datos
import config
import notificaciones
import servicio


# --------------------------------------------------------------------------
# Presentación
# --------------------------------------------------------------------------
def imprimir_tabla(filas, columnas):
    """Imprime una tabla simple. `columnas` es una lista de (encabezado, clave)."""
    if not filas:
        print("No hay resultados.")
        return
    anchos = [
        max(len(enc), *(len(str(f.get(clave, ""))) for f in filas))
        for enc, clave in columnas
    ]
    linea = "  ".join(enc.ljust(w) for (enc, _), w in zip(columnas, anchos))
    print(linea)
    print("  ".join("-" * w for w in anchos))
    for f in filas:
        print("  ".join(str(f.get(clave, "")).ljust(w)
                        for (_, clave), w in zip(columnas, anchos)))


# --------------------------------------------------------------------------
# Comandos
# --------------------------------------------------------------------------
def cmd_init(_):
    base_datos.inicializar()
    print(f"Base de datos lista en: {config.DB_PATH}")


def cmd_nueva(a):
    s = servicio.crear_solicitud(
        a.solicitante, a.tipo, a.descripcion, a.correo, a.tipo_solicitante,
        usuario=a.usuario,
    )
    print(f"Solicitud creada: {s['codigo']} ({s['tipo_solicitud']}), "
          f"fecha límite {s['fecha_limite']}")
    if not a.no_correo:
        notificaciones.notificar_recepcion(s)


def cmd_listar(a):
    alertas = {x["codigo"] for x in servicio.generar_alertas()}
    filas = servicio.listar(a.estado, a.responsable, solo_abiertas=not a.todas)
    for f in filas:
        f["alerta"] = "!" if f["codigo"] in alertas else ""
        f["espera"] = "sí" if f["en_espera"] else ""
        f["responsable"] = f["responsable"] or "-"
    imprimir_tabla(filas, [
        ("Código", "codigo"), ("Solicitante", "solicitante"),
        ("Tipo", "tipo_solicitud"), ("Estado", "estado"),
        ("Responsable", "responsable"), ("Límite", "fecha_limite"),
        ("Espera", "espera"), ("Alerta", "alerta"),
    ])


def cmd_ver(a):
    s = servicio.obtener(a.codigo)
    print(f"\n{s['codigo']}  -  {s['tipo_solicitud']}")
    print("=" * 60)
    campos = [
        ("Solicitante", "solicitante"), ("Correo", "correo"),
        ("Tipo de solicitante", "tipo_solicitante"), ("Descripción", "descripcion"),
        ("Estado", "estado"), ("Responsable", "responsable"),
        ("Fecha de creación", "fecha_creacion"), ("Fecha límite", "fecha_limite"),
        ("Motivo de espera", "motivo_espera"), ("Respuesta", "respuesta"),
        ("Fecha de cierre", "fecha_cierre"),
    ]
    for etiqueta, clave in campos:
        if s.get(clave):
            print(f"{etiqueta:<20}: {s[clave]}")
    print("\nHistorial:")
    for h in servicio.historial(a.codigo):
        cambio = f"{h['valor_anterior'] or '-'} -> {h['valor_nuevo'] or '-'}"
        print(f"  {h['fecha']}  {h['usuario']:<12} {h['campo']:<12} {cambio}"
              + (f"  ({h['comentario']})" if h["comentario"] else ""))


def cmd_estado(a):
    s = servicio.cambiar_estado(a.codigo, a.nuevo_estado, a.usuario,
                                a.comentario, a.respuesta)
    print(f"{s['codigo']} ahora está en '{s['estado']}'"
          + (f" (responsable: {s['responsable']})" if s["responsable"] else ""))
    if not a.no_correo:
        notificaciones.notificar_cambio_estado(s)


def cmd_asignar(a):
    s = servicio.asignar_responsable(a.codigo, a.responsable, a.correo_responsable,
                                     a.usuario)
    print(f"{s['codigo']} asignada a {s['responsable']}")


def cmd_espera(a):
    s = servicio.marcar_espera(a.codigo, a.motivo, a.usuario)
    print(f"{s['codigo']} en espera de información: {s['motivo_espera']}")
    if not a.no_correo:
        notificaciones.notificar_espera(s)


def cmd_reanudar(a):
    s = servicio.reanudar(a.codigo, a.usuario, a.comentario)
    print(f"{s['codigo']} reanudada. Nueva fecha límite: {s['fecha_limite']}")


def cmd_alertas(a):
    alertas = servicio.generar_alertas()
    if not alertas:
        print("Sin alertas. Todo al día.")
        return
    print(f"{len(alertas)} solicitud(es) con alerta:\n")
    for x in alertas:
        print(f"{x['codigo']} | {x['tipo_solicitud']} | {x['estado']} | {x['responsable']}")
        for m in x["motivos"]:
            print(f"    - {m}")
    if a.enviar:
        print()
        notificaciones.enviar_alertas(alertas)


def cmd_importar(a):
    import google_sheets

    creadas = google_sheets.importar_respuestas(a.usuario)
    print(f"{len(creadas)} solicitud(es) nueva(s) importada(s).")
    for s in creadas:
        print(f"  {s['codigo']}  {s['solicitante']}  ({s['tipo_solicitud']})")
        if not a.no_correo:
            notificaciones.notificar_recepcion(s)


def cmd_exportar(_):
    import google_sheets

    n = google_sheets.exportar_seguimiento()
    print(f"{n} solicitud(es) escritas en la pestaña '{config.HOJA_SEGUIMIENTO}'.")


def cmd_demo(a):
    """Carga datos de ejemplo para probar el sistema."""
    base_datos.inicializar()
    hoy = date.today()
    ejemplos = [
        ("Ana Pérez", "Certificados", "Certificado de participación en semillero", 1),
        ("Luis Gómez", "Solicitud de equipos", "Préstamo de portátil para trabajo de campo", 9),
        ("Grupo GIDA", "Petición de grupo de investigación", "Espacio para seminario", 3),
        ("María Ruiz", "Publicación de noticias", "Noticia sobre premio de investigación", 6),
        ("Carlos Díaz", "Actualización de docentes", "Actualizar CvLAC", 0),
    ]
    creadas = []
    for i, (nombre, tipo, desc, hace_dias) in enumerate(ejemplos, start=1):
        creadas.append(servicio.crear_solicitud(
            nombre, tipo, desc, f"solicitante{i}@example.com",
            "Docente", fecha_creacion=hoy - timedelta(days=hace_dias), usuario="demo",
        ))
    servicio.cambiar_estado(creadas[1]["codigo"], "En revisión", "demo")
    servicio.cambiar_estado(creadas[2]["codigo"], "En revisión", "demo")
    servicio.cambiar_estado(creadas[2]["codigo"], "En proceso", "demo")
    servicio.marcar_espera(creadas[3]["codigo"], "Falta la foto de la noticia", "demo")
    print(f"{len(creadas)} solicitudes de ejemplo creadas. Prueba: "
          "python main.py listar   |   python main.py alertas")


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------
def construir_parser():
    padre = argparse.ArgumentParser(add_help=False)
    padre.add_argument("--usuario", default=getpass.getuser(),
                       help="quién realiza la acción (queda en el historial)")
    padre.add_argument("--no-correo", action="store_true",
                       help="no enviar correo al solicitante")

    p = argparse.ArgumentParser(description="Control de solicitudes y trámites del CICA")
    sub = p.add_subparsers(dest="comando", required=True)

    sub.add_parser("init", help="crea la base de datos").set_defaults(func=cmd_init)

    s = sub.add_parser("nueva", parents=[padre], help="registra una solicitud")
    s.add_argument("--solicitante", required=True)
    s.add_argument("--tipo", required=True,
                   help="; ".join(config.TIPOS_SOLICITUD))
    s.add_argument("--descripcion", default="")
    s.add_argument("--correo", default="")
    s.add_argument("--tipo-solicitante", default="",
                   help="estudiante, docente, investigador...")
    s.set_defaults(func=cmd_nueva)

    s = sub.add_parser("listar", help="lista solicitudes")
    s.add_argument("--estado", choices=config.ESTADOS)
    s.add_argument("--responsable")
    s.add_argument("--todas", action="store_true", help="incluye las finalizadas")
    s.set_defaults(func=cmd_listar)

    s = sub.add_parser("ver", help="detalle e historial de una solicitud")
    s.add_argument("codigo")
    s.set_defaults(func=cmd_ver)

    s = sub.add_parser("estado", parents=[padre], help="cambia el estado")
    s.add_argument("codigo")
    s.add_argument("nuevo_estado", choices=config.ESTADOS)
    s.add_argument("--comentario", default="")
    s.add_argument("--respuesta", help="obligatoria al pasar a Finalizada")
    s.set_defaults(func=cmd_estado)

    s = sub.add_parser("asignar", parents=[padre], help="asigna un responsable")
    s.add_argument("codigo")
    s.add_argument("responsable")
    s.add_argument("--correo-responsable", default="")
    s.set_defaults(func=cmd_asignar)

    s = sub.add_parser("espera", parents=[padre],
                       help="marca que se espera información del solicitante")
    s.add_argument("codigo")
    s.add_argument("motivo")
    s.set_defaults(func=cmd_espera)

    s = sub.add_parser("reanudar", parents=[padre], help="quita la espera")
    s.add_argument("codigo")
    s.add_argument("--comentario", default="")
    s.set_defaults(func=cmd_reanudar)

    s = sub.add_parser("alertas", help="muestra (y opcionalmente envía) las alertas")
    s.add_argument("--enviar", action="store_true", help="enviar por correo")
    s.set_defaults(func=cmd_alertas)

    s = sub.add_parser("importar", parents=[padre],
                       help="importa respuestas nuevas de Google Sheets")
    s.set_defaults(func=cmd_importar)

    sub.add_parser("exportar", help="escribe el seguimiento en Google Sheets"
                   ).set_defaults(func=cmd_exportar)

    s = sub.add_parser("demo", help="carga datos de ejemplo")
    s.set_defaults(func=cmd_demo)
    return p


def main():
    args = construir_parser().parse_args()
    base_datos.inicializar()
    try:
        args.func(args)
    except servicio.ErrorSolicitud as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    except Exception as error:  # errores de Google, red, etc.
        print(f"Error inesperado: {error}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
