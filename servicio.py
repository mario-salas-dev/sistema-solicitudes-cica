"""Lógica de negocio: creación, cambios de estado, espera y alertas."""
from datetime import date, datetime, timedelta

import config
from base_datos import conexion


class ErrorSolicitud(Exception):
    """Error base del sistema."""


class SolicitudNoEncontrada(ErrorSolicitud):
    pass


class TransicionInvalida(ErrorSolicitud):
    pass


# --------------------------------------------------------------------------
# Utilidades internas
# --------------------------------------------------------------------------
def _ahora():
    return datetime.now().isoformat(timespec="seconds")


def _obtener(con, codigo):
    fila = con.execute(
        "SELECT * FROM solicitudes WHERE codigo = ?", (codigo.strip().upper(),)
    ).fetchone()
    if fila is None:
        raise SolicitudNoEncontrada(f"No existe la solicitud {codigo}")
    return dict(fila)


def _registrar(con, solicitud_id, usuario, campo, anterior, nuevo, comentario=""):
    con.execute(
        """INSERT INTO historial
           (solicitud_id, fecha, usuario, campo, valor_anterior, valor_nuevo, comentario)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (solicitud_id, _ahora(), usuario, campo, anterior, nuevo, comentario),
    )


def _actualizar(con, solicitud_id, cambios):
    # Las columnas vienen siempre de este módulo, nunca del usuario
    columnas = ", ".join(f"{c} = ?" for c in cambios)
    con.execute(
        f"UPDATE solicitudes SET {columnas} WHERE id = ?",
        (*cambios.values(), solicitud_id),
    )


def normalizar_tipo(texto):
    """Devuelve el tipo de solicitud conocido o el tipo por defecto."""
    t = (texto or "").strip().lower()
    for nombre in config.TIPOS_SOLICITUD:
        if nombre.lower() == t:
            return nombre
    return config.TIPO_POR_DEFECTO


def _siguiente_codigo(con, anio):
    prefijo = f"CICA-{anio}-"
    n = con.execute(
        "SELECT COUNT(*) FROM solicitudes WHERE codigo LIKE ?", (prefijo + "%",)
    ).fetchone()[0]
    return f"{prefijo}{n + 1:04d}"


# --------------------------------------------------------------------------
# Creación y consulta
# --------------------------------------------------------------------------
def crear_solicitud(
    solicitante,
    tipo_solicitud,
    descripcion="",
    correo="",
    tipo_solicitante="",
    origen=None,
    fecha_creacion=None,
    usuario="sistema",
):
    """Registra una solicitud en estado 'Recibida'.

    Devuelve la solicitud creada, o None si `origen` ya había sido importado.
    """
    if not (solicitante or "").strip():
        raise ErrorSolicitud("El nombre del solicitante es obligatorio")

    tipo = normalizar_tipo(tipo_solicitud)
    fecha = fecha_creacion or date.today()
    limite = fecha + timedelta(days=config.TIPOS_SOLICITUD[tipo]["dias"])

    with conexion() as con:
        if origen and con.execute(
            "SELECT 1 FROM solicitudes WHERE origen = ?", (origen,)
        ).fetchone():
            return None

        codigo = _siguiente_codigo(con, fecha.year)
        cur = con.execute(
            """INSERT INTO solicitudes
               (codigo, origen, fecha_creacion, solicitante, correo, tipo_solicitante,
                tipo_solicitud, descripcion, estado, fecha_estado, fecha_limite)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Recibida', ?, ?)""",
            (
                codigo,
                origen,
                fecha.isoformat(),
                solicitante.strip(),
                (correo or "").strip(),
                (tipo_solicitante or "").strip(),
                tipo,
                (descripcion or "").strip(),
                fecha.isoformat(),
                limite.isoformat(),
            ),
        )
        _registrar(con, cur.lastrowid, usuario, "estado", None, "Recibida",
                   "Solicitud registrada")
        return _obtener(con, codigo)


def obtener(codigo):
    with conexion() as con:
        return _obtener(con, codigo)


def listar(estado=None, responsable=None, solo_abiertas=False):
    sql = "SELECT * FROM solicitudes WHERE 1 = 1"
    params = []
    if estado:
        sql += " AND estado = ?"
        params.append(estado)
    if responsable:
        sql += " AND responsable LIKE ?"
        params.append(f"%{responsable}%")
    if solo_abiertas:
        sql += " AND estado != 'Finalizada'"
    sql += " ORDER BY fecha_limite IS NULL, fecha_limite, id"
    with conexion() as con:
        return [dict(f) for f in con.execute(sql, params).fetchall()]


def historial(codigo):
    with conexion() as con:
        s = _obtener(con, codigo)
        filas = con.execute(
            "SELECT * FROM historial WHERE solicitud_id = ? ORDER BY id", (s["id"],)
        ).fetchall()
        return [dict(f) for f in filas]


# --------------------------------------------------------------------------
# Cambios sobre una solicitud
# --------------------------------------------------------------------------
def cambiar_estado(codigo, nuevo_estado, usuario="sistema", comentario="", respuesta=None):
    """Mueve la solicitud al siguiente estado permitido.

    - En 'En revisión' asigna automáticamente el responsable según el tipo.
    - Para 'Finalizada' se exige una respuesta.
    """
    with conexion() as con:
        s = _obtener(con, codigo)

        if s["en_espera"]:
            raise TransicionInvalida(
                "La solicitud está esperando información del solicitante; "
                "reanúdala antes de cambiar de estado."
            )
        if nuevo_estado not in config.TRANSICIONES.get(s["estado"], []):
            permitidos = config.TRANSICIONES.get(s["estado"], [])
            raise TransicionInvalida(
                f"No se puede pasar de '{s['estado']}' a '{nuevo_estado}'. "
                f"Estados permitidos: {', '.join(permitidos) or 'ninguno'}."
            )

        hoy = date.today().isoformat()
        cambios = {"estado": nuevo_estado, "fecha_estado": hoy}

        if nuevo_estado == "En revisión" and not s["responsable"]:
            datos = config.TIPOS_SOLICITUD[s["tipo_solicitud"]]
            cambios["responsable"] = datos["responsable"]
            cambios["correo_responsable"] = datos["correo"]
            _registrar(con, s["id"], usuario, "responsable", None,
                       datos["responsable"], "Asignación automática por tipo")

        if nuevo_estado == "Finalizada":
            texto = (respuesta or s["respuesta"] or "").strip()
            if not texto:
                raise TransicionInvalida("Para finalizar debes indicar la respuesta.")
            cambios["respuesta"] = texto
            cambios["fecha_cierre"] = hoy

        _actualizar(con, s["id"], cambios)
        _registrar(con, s["id"], usuario, "estado", s["estado"], nuevo_estado, comentario)
        return _obtener(con, codigo)


def asignar_responsable(codigo, nombre, correo="", usuario="sistema"):
    with conexion() as con:
        s = _obtener(con, codigo)
        if s["estado"] == "Finalizada":
            raise TransicionInvalida("La solicitud ya está finalizada.")
        _actualizar(con, s["id"], {"responsable": nombre, "correo_responsable": correo})
        _registrar(con, s["id"], usuario, "responsable", s["responsable"], nombre)
        return _obtener(con, codigo)


def marcar_espera(codigo, motivo, usuario="sistema"):
    """Marca que la solicitud espera información del solicitante."""
    with conexion() as con:
        s = _obtener(con, codigo)
        if s["estado"] == "Finalizada":
            raise TransicionInvalida("La solicitud ya está finalizada.")
        if s["en_espera"]:
            raise TransicionInvalida("La solicitud ya está en espera.")
        _actualizar(con, s["id"], {
            "en_espera": 1,
            "motivo_espera": motivo,
            "fecha_espera": date.today().isoformat(),
        })
        _registrar(con, s["id"], usuario, "en_espera", "No", "Sí", motivo)
        return _obtener(con, codigo)


def reanudar(codigo, usuario="sistema", comentario=""):
    """Quita la espera y descuenta esos días de los plazos (no penalizan al equipo)."""
    with conexion() as con:
        s = _obtener(con, codigo)
        if not s["en_espera"]:
            raise TransicionInvalida("La solicitud no está en espera.")

        dias = (date.today() - date.fromisoformat(s["fecha_espera"])).days
        cambios = {
            "en_espera": 0,
            "motivo_espera": None,
            "fecha_espera": None,
            "fecha_estado": (date.fromisoformat(s["fecha_estado"])
                             + timedelta(days=dias)).isoformat(),
        }
        if s["fecha_limite"]:
            cambios["fecha_limite"] = (date.fromisoformat(s["fecha_limite"])
                                       + timedelta(days=dias)).isoformat()

        _actualizar(con, s["id"], cambios)
        _registrar(con, s["id"], usuario, "en_espera", "Sí", "No",
                   comentario or f"Estuvo en espera {dias} día(s)")
        return _obtener(con, codigo)


# --------------------------------------------------------------------------
# Alertas
# --------------------------------------------------------------------------
def generar_alertas(hoy=None):
    """Devuelve las solicitudes abiertas que requieren atención, con sus motivos."""
    hoy = hoy or date.today()
    alertas = []

    for s in listar(solo_abiertas=True):
        motivos = []

        if s["fecha_limite"]:
            vencida = (hoy - date.fromisoformat(s["fecha_limite"])).days
            if vencida > 0:
                motivos.append(f"Fecha límite vencida hace {vencida} día(s)")

        if s["en_espera"]:
            dias = (hoy - date.fromisoformat(s["fecha_espera"])).days
            if dias > config.DIAS_MAX_ESPERA:
                motivos.append(
                    f"Esperando información del solicitante hace {dias} día(s) "
                    f"({s['motivo_espera'] or 'sin motivo'})"
                )
        else:
            plazo = config.PLAZOS_ESTADO.get(s["estado"])
            dias = (hoy - date.fromisoformat(s["fecha_estado"])).days
            if plazo is not None and dias > plazo:
                motivos.append(
                    f"Lleva {dias} día(s) en '{s['estado']}' (plazo: {plazo})"
                )

        if motivos:
            alertas.append({
                "codigo": s["codigo"],
                "solicitante": s["solicitante"],
                "tipo_solicitud": s["tipo_solicitud"],
                "estado": s["estado"],
                "responsable": s["responsable"] or "Sin asignar",
                "correo_responsable": s["correo_responsable"] or "",
                "motivos": motivos,
            })
    return alertas
