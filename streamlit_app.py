"""Pantalla visual del sistema de solicitudes del CICA, hecha con Streamlit.

Para arrancarla:  streamlit run streamlit_app.py

Usa exactamente la misma base de datos y reglas que main.py (el mismo
archivo servicio.py), asi que lo que hagas aqui tambien queda en el
historial y es 100% compatible con los comandos de la terminal.
"""
import streamlit as st
from datetime import date

import base_datos
import config
import notificaciones
import servicio

st.set_page_config(page_title="Solicitudes CICA", page_icon="📋", layout="wide")
base_datos.inicializar()


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def badge_estado(estado):
    colores = {
        "Recibida": "🔵", "En revisión": "🟡",
        "En proceso": "🟠", "Finalizada": "🟢",
    }
    return f"{colores.get(estado, '⚪')} {estado}"


def recargar():
    st.cache_data.clear()
    st.rerun()


@st.cache_data(ttl=15)
def cargar_solicitudes(solo_abiertas):
    return servicio.listar(solo_abiertas=solo_abiertas)


@st.cache_data(ttl=15)
def cargar_alertas():
    return servicio.generar_alertas()


# --------------------------------------------------------------------------
# Barra lateral: navegación y resumen
# --------------------------------------------------------------------------
st.sidebar.title("📋 CICA")
pagina = st.sidebar.radio(
    "Menú",
    ["Listado", "Nueva solicitud", "Ver / gestionar", "Alertas"],
    label_visibility="collapsed",
)

usuario = st.sidebar.text_input("Tu nombre", value=st.session_state.get("usuario", ""),
                                help="Aparecerá en el historial de cada cambio que hagas")
st.session_state["usuario"] = usuario or "Sistema web"

todas = cargar_solicitudes(solo_abiertas=False)
abiertas = [s for s in todas if s["estado"] != "Finalizada"]
alertas_previas = cargar_alertas()
st.sidebar.metric("Solicitudes abiertas", len(abiertas))
st.sidebar.metric("Con alerta", len(alertas_previas))

if st.sidebar.button("🔄 Actualizar datos"):
    recargar()


# --------------------------------------------------------------------------
# Página: Listado
# --------------------------------------------------------------------------
if pagina == "Listado":
    st.title("Solicitudes")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        filtro_estado = st.selectbox("Estado", ["Todos"] + config.ESTADOS)
    with col2:
        filtro_responsable = st.text_input("Buscar responsable")
    with col3:
        incluir_finalizadas = st.checkbox("Incluir finalizadas", value=False)

    filas = cargar_solicitudes(solo_abiertas=not incluir_finalizadas)
    if filtro_estado != "Todos":
        filas = [f for f in filas if f["estado"] == filtro_estado]
    if filtro_responsable:
        filas = [f for f in filas
                if filtro_responsable.lower() in (f["responsable"] or "").lower()]

    if not filas:
        st.info("No hay solicitudes que coincidan con el filtro.")
    else:
        codigos_alerta = {a["codigo"] for a in alertas_previas}
        tabla = [{
            "⚠": "🔴" if f["codigo"] in codigos_alerta else "",
            "Código": f["codigo"],
            "Solicitante": f["solicitante"],
            "Tipo": f["tipo_solicitud"],
            "Estado": badge_estado(f["estado"]),
            "Responsable": f["responsable"] or "Sin asignar",
            "Límite": f["fecha_limite"] or "-",
            "Espera": "Sí" if f["en_espera"] else "",
        } for f in filas]
        st.dataframe(tabla, use_container_width=True, hide_index=True)
        st.caption(f"{len(filas)} solicitud(es). Ve a 'Ver / gestionar' para actuar sobre una.")


# --------------------------------------------------------------------------
# Página: Nueva solicitud
# --------------------------------------------------------------------------
elif pagina == "Nueva solicitud":
    st.title("Registrar solicitud")

    with st.form("nueva_solicitud"):
        c1, c2 = st.columns(2)
        with c1:
            solicitante = st.text_input("Nombre del solicitante *")
            correo = st.text_input("Correo electrónico")
            tipo_solicitante = st.text_input("Tipo de solicitante (Estudiante, Docente...)")
        with c2:
            tipo = st.selectbox("Tipo de solicitud *", list(config.TIPOS_SOLICITUD))
            enviar_correo = st.checkbox("Notificar por correo al solicitante", value=True)
        descripcion = st.text_area("Descripción")

        if st.form_submit_button("Registrar", type="primary"):
            if not solicitante.strip():
                st.error("El nombre del solicitante es obligatorio.")
            else:
                try:
                    s = servicio.crear_solicitud(
                        solicitante, tipo, descripcion, correo, tipo_solicitante,
                        usuario=st.session_state["usuario"],
                    )
                    st.success(f"Solicitud {s['codigo']} creada. Fecha límite: {s['fecha_limite']}")
                    if enviar_correo:
                        notificaciones.notificar_recepcion(s)
                    recargar()
                except servicio.ErrorSolicitud as error:
                    st.error(str(error))


# --------------------------------------------------------------------------
# Página: Ver / gestionar una solicitud
# --------------------------------------------------------------------------
elif pagina == "Ver / gestionar":
    st.title("Ver y gestionar una solicitud")

    codigos = [f["codigo"] for f in todas]
    if not codigos:
        st.info("Todavía no hay solicitudes registradas.")
        st.stop()

    codigo = st.selectbox("Elige una solicitud", codigos)
    s = servicio.obtener(codigo)

    st.subheader(f"{s['codigo']} — {s['tipo_solicitud']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Estado", s["estado"])
    c2.metric("Responsable", s["responsable"] or "Sin asignar")
    c3.metric("Fecha límite", s["fecha_limite"] or "-")

    with st.expander("Datos de la solicitud", expanded=True):
        st.write(f"**Solicitante:** {s['solicitante']}")
        st.write(f"**Correo:** {s['correo'] or '-'}")
        st.write(f"**Tipo de solicitante:** {s['tipo_solicitante'] or '-'}")
        st.write(f"**Descripción:** {s['descripcion'] or '-'}")
        if s["en_espera"]:
            st.warning(f"En espera desde {s['fecha_espera']}: {s['motivo_espera']}")
        if s["respuesta"]:
            st.write(f"**Respuesta:** {s['respuesta']}")

    st.divider()
    tab_estado, tab_asignar, tab_espera = st.tabs(
        ["Cambiar estado", "Asignar responsable", "Espera / Reanudar"]
    )

    with tab_estado:
        siguientes = config.TRANSICIONES.get(s["estado"], [])
        if s["en_espera"]:
            st.info("Está en espera: reanúdala primero en la pestaña correspondiente.")
        elif not siguientes:
            st.info("Esta solicitud ya está finalizada.")
        else:
            nuevo_estado = st.selectbox("Nuevo estado", siguientes)
            respuesta = ""
            if nuevo_estado == "Finalizada":
                respuesta = st.text_area("Respuesta al solicitante *")
            enviar = st.checkbox("Notificar por correo al solicitante", value=True,
                                 key="notif_estado")
            if st.button("Aplicar cambio de estado", type="primary"):
                try:
                    actualizado = servicio.cambiar_estado(
                        codigo, nuevo_estado, st.session_state["usuario"],
                        respuesta=respuesta or None,
                    )
                    st.success(f"Ahora está en '{actualizado['estado']}'.")
                    if enviar:
                        notificaciones.notificar_cambio_estado(actualizado)
                    recargar()
                except servicio.ErrorSolicitud as error:
                    st.error(str(error))

    with tab_asignar:
        nombre = st.text_input("Nombre del responsable", value=s["responsable"] or "")
        correo_resp = st.text_input("Correo del responsable",
                                    value=s["correo_responsable"] or "")
        if st.button("Guardar responsable"):
            try:
                servicio.asignar_responsable(codigo, nombre, correo_resp,
                                             st.session_state["usuario"])
                st.success("Responsable actualizado.")
                recargar()
            except servicio.ErrorSolicitud as error:
                st.error(str(error))

    with tab_espera:
        if s["en_espera"]:
            st.warning(f"Motivo actual: {s['motivo_espera']}")
            if st.button("Reanudar (ya llegó la información)", type="primary"):
                actualizado = servicio.reanudar(codigo, st.session_state["usuario"])
                st.success(f"Reanudada. Nueva fecha límite: {actualizado['fecha_limite']}")
                recargar()
        else:
            motivo = st.text_input("¿Qué falta por parte del solicitante?")
            enviar_espera = st.checkbox("Notificar por correo al solicitante", value=True,
                                        key="notif_espera")
            if st.button("Marcar en espera"):
                if not motivo.strip():
                    st.error("Escribe el motivo.")
                else:
                    try:
                        actualizado = servicio.marcar_espera(codigo, motivo,
                                                             st.session_state["usuario"])
                        st.success("Solicitud marcada en espera.")
                        if enviar_espera:
                            notificaciones.notificar_espera(actualizado)
                        recargar()
                    except servicio.ErrorSolicitud as error:
                        st.error(str(error))

    st.divider()
    st.subheader("Historial")
    for h in servicio.historial(codigo):
        cambio = f"{h['valor_anterior'] or '-'} → {h['valor_nuevo'] or '-'}"
        st.text(f"{h['fecha']}  ·  {h['usuario']}  ·  {h['campo']}: {cambio}"
                + (f"  ({h['comentario']})" if h["comentario"] else ""))


# --------------------------------------------------------------------------
# Página: Alertas
# --------------------------------------------------------------------------
elif pagina == "Alertas":
    st.title("Alertas")

    alertas = cargar_alertas()
    if not alertas:
        st.success("Sin alertas. Todo al día. ✅")
    else:
        st.warning(f"{len(alertas)} solicitud(es) requieren atención.")
        for a in alertas:
            with st.container(border=True):
                st.markdown(f"**{a['codigo']}** · {a['tipo_solicitud']} · "
                           f"{a['estado']} · Responsable: {a['responsable']}")
                for m in a["motivos"]:
                    st.write(f"- {m}")

        if st.button("📧 Enviar todas las alertas por correo", type="primary"):
            notificaciones.enviar_alertas(alertas)
            st.success("Alertas enviadas.")
