"""Gestor de tareas: prioridades, fechas, descripciones y guardado local."""

import json
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

# Configuración. Los colores están en .streamlit/config.toml.
st.set_page_config(page_title="Gestor de Tareas", page_icon="📅", layout="centered")
CARPETA = Path(__file__).resolve().parent
ARCHIVO_TAREAS = CARPETA / "tareas.json"
ARCHIVO_USUARIO = CARPETA / "usuario.json"
IMAGEN_COMPLETADO = CARPETA / "felicitacion.png"
ORDEN_PRIORIDAD = {"Alta": 0, "Media": 1, "Baja": 2}


def leer_json(ruta, defecto):
    """Leer un archivo JSON sin sustituir silenciosamente datos defectuosos."""
    if not ruta.exists():
        return defecto
    try:
        with ruta.open("r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except (OSError, json.JSONDecodeError) as error:
        st.error(f"No se puede leer {ruta.name}: {error}")
        st.info("Haz una copia de seguridad del archivo y revisa su contenido.")
        st.stop()


def guardar_json(ruta, contenido):
    """Guardar mediante un archivo temporal para reducir pérdidas de datos."""
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    try:
        with temporal.open("w", encoding="utf-8") as archivo:
            json.dump(contenido, archivo, ensure_ascii=False, indent=2)
        temporal.replace(ruta)
    except (OSError, TypeError) as error:
        st.error(f"No se pudo guardar {ruta.name}: {error}")
        st.stop()


def cargar_tareas():
    tareas = leer_json(ARCHIVO_TAREAS, [])
    if not isinstance(tareas, list):
        st.error("tareas.json debe contener una lista de tareas.")
        st.stop()

    ids = set()
    for tarea in tareas:
        if not isinstance(tarea, dict):
            st.error("Hay una tarea con un formato incorrecto.")
            st.stop()
        if (
            type(tarea.get("id")) is not int
            or not isinstance(tarea.get("nombre"), str)
            or tarea.get("prioridad") not in ORDEN_PRIORIDAD
            or type(tarea.get("completada")) is not bool
            or tarea["id"] in ids
        ):
            st.error("Hay tareas con datos inválidos o identificadores duplicados.")
            st.stop()
        ids.add(tarea["id"])
        fecha = tarea.get("fecha")
        if fecha:
            try:
                date.fromisoformat(fecha)
            except (ValueError, TypeError):
                st.error("Hay una fecha inválida en tareas.json.")
                st.stop()
        if not isinstance(tarea.get("descripcion", ""), str):
            st.error("Hay una descripción inválida en tareas.json.")
            st.stop()
    return tareas


def cargar_id():
    datos = leer_json(ARCHIVO_USUARIO, {})
    if not isinstance(datos, dict):
        st.error("usuario.json debe contener un objeto JSON.")
        st.stop()
    # Se conserva la clave 'nombre' de las versiones anteriores.
    resultado = datos.get("nombre", "")
    if not isinstance(resultado, str):
        st.error("El ID guardado debe ser texto.")
        st.stop()
    return resultado


if "tareas" not in st.session_state:
    st.session_state.tareas = cargar_tareas()
if "siguiente_id" not in st.session_state:
    st.session_state.siguiente_id = max(
        (t["id"] for t in st.session_state.tareas), default=-1
    ) + 1
if "id_usuario" not in st.session_state:
    st.session_state.id_usuario = cargar_id()


def guardar_tareas():
    guardar_json(ARCHIVO_TAREAS, st.session_state.tareas)


def cambiar_id():
    st.session_state.id_usuario = st.session_state.id_usuario.strip()
    guardar_json(ARCHIVO_USUARIO, {"nombre": st.session_state.id_usuario})


def buscar_tarea(identificador):
    return next(
        (t for t in st.session_state.tareas if t["id"] == identificador),
        None,
    )


def cambiar_estado(identificador):
    tarea = buscar_tarea(identificador)
    if tarea is not None:
        tarea["completada"] = st.session_state[f"completada_{identificador}"]
        guardar_tareas()


def eliminar_tarea(identificador):
    st.session_state.tareas = [
        t for t in st.session_state.tareas if t["id"] != identificador
    ]
    guardar_tareas()
    st.rerun()


def esta_retrasada(tarea):
    fecha = tarea.get("fecha")
    return bool(
        fecha
        and not tarea["completada"]
        and date.fromisoformat(fecha) < date.today()
    )


def ordenar_tareas(tareas, criterio):
    if criterio == "Fecha más próxima":
        return sorted(tareas, key=lambda t: (not t.get("fecha"), t.get("fecha") or ""))
    if criterio == "Fecha más lejana":
        con_fecha = sorted(
            (t for t in tareas if t.get("fecha")),
            key=lambda t: t["fecha"], reverse=True,
        )
        return con_fecha + [t for t in tareas if not t.get("fecha")]
    if criterio == "Prioridad":
        return sorted(tareas, key=lambda t: ORDEN_PRIORIDAD[t["prioridad"]])
    return sorted(tareas, key=lambda t: t["nombre"].casefold())


def mostrar_tarea(tarea):
    identificador = tarea["id"]
    with st.container(border=True):
        nombre_col, prioridad_col, eliminar_col = st.columns(
            [5, 2, 1], vertical_alignment="center"
        )
        with nombre_col:
            st.checkbox(
                tarea["nombre"],
                value=tarea["completada"],
                key=f"completada_{identificador}",
                on_change=cambiar_estado,
                args=(identificador,),
            )
        with prioridad_col:
            icono = {"Alta": "🔴", "Media": "🟡", "Baja": "🟢"}[tarea["prioridad"]]
            st.write(f"{icono} {tarea['prioridad']}")
        with eliminar_col:
            if st.button("🗑️", key=f"borrar_{identificador}", help="Eliminar tarea"):
                eliminar_tarea(identificador)

        # La descripción solo aparece cuando tiene contenido.
        descripcion = tarea.get("descripcion", "")
        if descripcion.strip():
            st.write(descripcion)

        fecha = tarea.get("fecha")
        if fecha:
            st.caption(f"📅 {date.fromisoformat(fecha).strftime('%d/%m/%Y')}")
        else:
            st.caption("📅 Sin fecha")
        if esta_retrasada(tarea):
            st.caption("❗ Esta tarea está retrasada")

        with st.expander("✏️ Editar", expanded=False):
            with st.form(f"editar_{identificador}"):
                nombre_nuevo = st.text_input("Nombre", value=tarea["nombre"])
                descripcion_nueva = st.text_area(
                    "Descripción (opcional)", value=descripcion, height=85
                )
                col_p, col_f = st.columns(2)
                with col_p:
                    opciones = ["Alta", "Media", "Baja"]
                    prioridad_nueva = st.selectbox(
                        "Prioridad", opciones, index=opciones.index(tarea["prioridad"])
                    )
                with col_f:
                    fecha_nueva = st.date_input(
                        "Fecha límite",
                        value=date.fromisoformat(fecha) if fecha else None,
                        format="DD/MM/YYYY",
                    )
                if st.form_submit_button("💾 Guardar cambios", type="primary"):
                    if not nombre_nuevo.strip():
                        st.warning("El nombre de la tarea no puede estar vacío.")
                    else:
                        tarea.update({
                            "nombre": nombre_nuevo.strip(),
                            "descripcion": descripcion_nueva.strip(),
                            "prioridad": prioridad_nueva,
                            "fecha": fecha_nueva.isoformat() if fecha_nueva else None,
                        })
                        guardar_tareas()
                        st.rerun()


# CABECERA
usuario = st.session_state.id_usuario.strip()
st.title(f"📅 Gestor de tareas - {usuario}" if usuario else "📅 Gestor de tareas")
st.write("Organiza tus actividades de forma sencilla.")
with st.expander("👤 ID", expanded=not bool(usuario)):
    st.text_input(
        "ID", key="id_usuario", max_chars=60,
        placeholder="Introduce tu ID", on_change=cambiar_id,
    )
st.caption(f"Hoy es {date.today().strftime('%d/%m/%Y')}")

# ESTADÍSTICAS
lista = st.session_state.tareas
total = len(lista)
completadas = sum(t["completada"] for t in lista)
pendientes = total - completadas
retrasadas = [t for t in lista if esta_retrasada(t)]

col_total, col_pend, col_retr = st.columns(3)
col_total.metric("📋 TOTAL", total)
col_pend.metric("⏳ PENDIENTES", pendientes)
col_retr.metric("❗ RETRASADAS", len(retrasadas))
if total:
    st.write(f"✅ Has completado {completadas} de {total} tareas.")
    st.progress(completadas / total)

# NUEVA TAREA
st.subheader("➕ Nueva tarea", anchor=False)
with st.form("crear_tarea", clear_on_submit=True):
    nombre = st.text_input("Nombre de la tarea", placeholder="Ej. Preparar CV")
    descripcion = st.text_area(
        "📝 Descripción (opcional)",
        placeholder="Añade notas o detalles de esta tarea...", height=85,
    )
    c1, c2 = st.columns(2)
    with c1:
        prioridad = st.selectbox("Prioridad", ["Alta", "Media", "Baja"])
    with c2:
        fecha_limite = st.date_input(
            "Fecha límite", value=date.today() + timedelta(days=1),
            format="DD/MM/YYYY",
        )
    if st.form_submit_button("AGREGAR", type="primary"):
        if not nombre.strip():
            st.warning("Por favor, escribe el nombre de la tarea.")
        else:
            lista.append({
                "id": st.session_state.siguiente_id,
                "nombre": nombre.strip(),
                "descripcion": descripcion.strip(),
                "prioridad": prioridad,
                "fecha": fecha_limite.isoformat(),
                "completada": False,
            })
            st.session_state.siguiente_id += 1
            guardar_tareas()
            st.rerun()

# TAREAS Y FILTROS
st.subheader("📋 Mis tareas", anchor=False)
filtro_col, orden_col = st.columns(2)
with filtro_col:
    filtro = st.selectbox("Filtrar tareas", ["Todas", "Pendientes", "Completadas"])
with orden_col:
    criterio = st.selectbox(
        "Ordenar por", ["Fecha más próxima", "Fecha más lejana", "Prioridad", "Nombre (A-Z)"]
    )

if filtro == "Pendientes":
    seleccionadas = [t for t in lista if not t["completada"]]
elif filtro == "Completadas":
    seleccionadas = [t for t in lista if t["completada"]]
else:
    seleccionadas = lista.copy()

# Retrasadas se muestran aparte para no duplicarlas.
normales = ordenar_tareas(
    [t for t in seleccionadas if not esta_retrasada(t)], criterio
)

if pendientes == 0:
    if IMAGEN_COMPLETADO.exists():
        st.image(str(IMAGEN_COMPLETADO), width=300)
    else:
        st.success("🎉 ¡Enhorabuena! Has terminado todas tus tareas.")
    if IMAGEN_COMPLETADO.exists():
        st.success("¡Todo al día! No tienes tareas pendientes.")

if normales:
    for tarea in normales:
        mostrar_tarea(tarea)
elif pendientes > 0:
    st.info("No hay tareas en esta vista. Revisa el filtro o las retrasadas.")

# SECCIÓN DE RETRASADAS
st.divider()
mostrar_retrasadas = st.toggle(
    f"❗ Mostrar tareas retrasadas ({len(retrasadas)})", value=True
)
if mostrar_retrasadas:
    if retrasadas:
        st.subheader("❗ Tareas retrasadas", anchor=False)
        for tarea in ordenar_tareas(retrasadas, criterio):
            mostrar_tarea(tarea)
    else:
        st.success("No tienes tareas retrasadas.")

st.caption("Gestor de tareas · Proyecto personal con Python y Streamlit")
