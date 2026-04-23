# PRODUCCION PARA MONITOREO DE ORDENES - FINAL
# HECHO POR ALFREDO CORTES MEZA
# PRODUCTION LINE INTELLIGENCE MONITOR (PLIM)
import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(layout="wide")
st.title("LINEA DE PRODUCCIÓN")
tipo_linea = st.selectbox(
    "Tipo de línea",
    ["MCX", "HCX", "ETS"]
)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "produccion_v2.db")

conn = sqlite3.connect(db_path, check_same_thread=False)

# -------------------------------------------------
# BASE DE DATOS
# -------------------------------------------------
conn.execute("""
CREATE TABLE IF NOT EXISTS ordenes (
    Orden TEXT PRIMARY KEY,
    Secciones INTEGER,
    Fecha DATE
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS produccion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Orden TEXT,
    Area TEXT,
    Seccion INTEGER,
    Porcentaje REAL,
    Turno TEXT,
    Trabajador TEXT,
    Ubicacion TEXT,
    Tiempo_efectivo REAL,
    Tiempo_muerto REAL,
    Pausas REAL,
    Razon TEXT,
    Fecha DATE
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS faltantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Orden TEXT,
    Area TEXT,
    Seccion INTEGER,
    Material TEXT,
    Cantidad INTEGER,
    Fecha DATE
)
""")

conn.commit()

# -------------------------------------------------
# SIDEBAR - AGREGAR ORDEN
# -------------------------------------------------
st.sidebar.subheader("Agregar Orden")

orden_sb = st.sidebar.text_input("Orden")
secciones_sb = st.sidebar.number_input("Secciones", min_value=1)
fecha_sb = st.sidebar.date_input("Fecha")

if st.sidebar.button("Agregar Orden"):
    try:
        conn.execute(
            "INSERT INTO ordenes VALUES (?, ?, ?)",
            (orden_sb, secciones_sb, fecha_sb)
        )
        conn.commit()
        st.sidebar.success("Orden agregada")
        st.rerun()
    except:
        st.sidebar.error("La orden ya existe")

# -------------------------------------------------
# CARGAR ORDENES
# -------------------------------------------------
df_ordenes = pd.read_sql_query("SELECT * FROM ordenes", conn)

if df_ordenes.empty:
    st.warning("No hay órdenes registradas")
    st.stop()

# -------------------------------------------------
# SIDEBAR - ELIMINAR ORDEN
# -------------------------------------------------
st.sidebar.subheader("Eliminar Orden")

orden_eliminar = st.sidebar.selectbox(
    "Selecciona Orden a eliminar",
    df_ordenes["Orden"],
    key="delete"
)

if st.sidebar.button("Eliminar Orden"):
    conn.execute("DELETE FROM produccion WHERE Orden=?", (orden_eliminar,))
    conn.execute("DELETE FROM faltantes WHERE Orden=?", (orden_eliminar,))
    conn.execute("DELETE FROM ordenes WHERE Orden=?", (orden_eliminar,))
    conn.commit()
    st.sidebar.success("Orden eliminada completamente")
    st.rerun()

# -------------------------------------------------
# SELECCION ORDEN ACTIVA
# -------------------------------------------------
orden_activa = st.sidebar.selectbox(
    "Selecciona Orden",
    df_ordenes["Orden"]
)

editar = st.sidebar.toggle("Editar avances")

secciones_total = int(
    df_ordenes[df_ordenes["Orden"] == orden_activa]["Secciones"].values[0]
)

# -------------------------------------------------
# TABS
# -------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["Ensamble", "Alambrado", "Faltantes", "Visualización"]
)

# =================================================
# ENSAMBLE
# =================================================
with tab1:

    st.subheader(f"Ensamble - {orden_activa}")

    seccion_sel = st.selectbox("Sección", range(1, secciones_total+1))

    df = pd.read_sql_query(
    "SELECT * FROM produccion WHERE Orden=? AND Area='Ensamble' AND Seccion=?",
    conn,
    params=(orden_activa, seccion_sel)
)
    df_falt = pd.read_sql_query("SELECT * FROM faltantes", conn)
    params=(orden_activa, seccion_sel)
    

    bloqueado = not df.empty and not editar

    if bloqueado:
        st.warning("Sección bloqueada")

    porcentaje = st.slider("Avance (%)", 0, 100, step=10, disabled=bloqueado)
    turno = st.selectbox("Turno", ["Primer turno", "Tercer turno"], disabled=bloqueado)
    trabajador = st.text_input("Trabajador", disabled=bloqueado)

    ubicacion = st.selectbox(
        "Ubicación",
        ["Línea", "Pruebas", "Preembarque"],
        disabled=bloqueado
    )
    te = st.number_input("Tiempo efectivo", value=0.0, disabled=bloqueado)
    tm = st.number_input("Tiempo muerto", value=0.0, disabled=bloqueado)
    pausa = st.number_input("Pausas", value=0.0, disabled=bloqueado)
    razon = ""

    if tm > 0 or pausa > 0:
        razon_opcion = st.selectbox(
            "Razón de pausas / tiempo muerto",
            ["Junta de seguridad", "Junta informativa", "Evacuación", "Otro"],
            disabled=bloqueado
        )

        if razon_opcion == "Otro":
            razon = st.text_input("Especifica la razón", disabled=bloqueado)
        else:
            razon = razon_opcion
    if st.button("Guardar Ensamble", disabled=bloqueado):

        if df.empty:
        # INSERTAR
            conn.execute("""
            INSERT INTO produccion VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                orden_activa, "Ensamble", seccion_sel, porcentaje, turno,
                trabajador, ubicacion,
                te, tm, pausa,
                razon,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        else:
        # ACTUALIZAR
            conn.execute("""
            UPDATE produccion
            SET Porcentaje=?, Turno=?, Trabajador=?, Ubicacion=?,
                Tiempo_efectivo=?, Tiempo_muerto=?, Pausas=?, Razon=?, Fecha=?
            WHERE Orden=? AND Area='Ensamble' AND Seccion=?
            """, (
                porcentaje, turno, trabajador, ubicacion,
                te, tm, pausa, razon,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                orden_activa, seccion_sel
            ))

        conn.commit()
        st.success("Guardado")
        st.rerun()

# =================================================
# ALAMBRADO
# =================================================
with tab2:

    st.subheader(f"Alambrado - {orden_activa}")

    tipo_alambrado = st.selectbox(
        "Tipo de alambrado",
        ["Alambrado en sección", "Alambrado en panel"]
    )

    seccion_sel = st.selectbox("Sección", range(1, secciones_total+1), key="alm_sec")

    df = pd.read_sql_query(
        "SELECT * FROM produccion WHERE Orden=? AND Area=? AND Seccion=?",
        conn,
        params=(orden_activa, tipo_alambrado, seccion_sel)
    )

    bloqueado = not df.empty and not editar

    if bloqueado:
        st.warning("Sección bloqueada")

    porcentaje = st.slider("Avance (%)", 0, 100, step=10, key="alm", disabled=bloqueado)
    turno = st.selectbox("Turno", ["Primer turno", "Tercer turno"], key="alm_t", disabled=bloqueado)
    trabajador = st.text_input("Trabajador", key="alm_trab", disabled=bloqueado)

    ubicacion = st.selectbox(
        "Ubicación",
        ["Línea", "Pruebas", "Preembarque"],
        key="alm_ubi",
        disabled=bloqueado
    )
    te = st.number_input("Tiempo efectivo", key="alm_te", value=0.0, disabled=bloqueado)
    tm = st.number_input("Tiempo muerto", key="alm_tm", value=0.0, disabled=bloqueado)
    pausa = st.number_input("Pausas", key="alm_p", value=0.0, disabled=bloqueado)
    razon = ""

    if tm > 0 or pausa > 0:
        razon_opcion = st.selectbox(
            "Razón de pausas / tiempo muerto",
            ["Junta de seguridad", "Junta informativa", "Evacuación", "Otro"],
            key="alm_razon",
            disabled=bloqueado
        )

        if razon_opcion == "Otro":
            razon = st.text_input("Especifica la razón", key="alm_otro", disabled=bloqueado)
        else:
            razon = razon_opcion
    if st.button("Guardar Alambrado", disabled=bloqueado):

        if df.empty:
            conn.execute("""
            INSERT INTO produccion VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                orden_activa, tipo_alambrado, seccion_sel, porcentaje, turno,
                trabajador, ubicacion,
                te, tm, pausa,
                razon,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        else:
            conn.execute("""
            UPDATE produccion
            SET Porcentaje=?, Turno=?, Trabajador=?, Ubicacion=?,
                Tiempo_efectivo=?, Tiempo_muerto=?, Pausas=?, Razon=?, Fecha=?
            WHERE Orden=? AND Area=? AND Seccion=?
            """, (
                porcentaje, turno, trabajador, ubicacion,
                te, tm, pausa, razon,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                orden_activa, tipo_alambrado, seccion_sel
            ))

        conn.commit()
        st.success("Guardado")
        st.rerun()

# =================================================
# FALTANTES
# =================================================
with tab3:

    st.subheader(f"Faltantes - {orden_activa}")

    material = st.text_input("Material")
    cantidad = st.number_input("Cantidad", min_value=1)

    if st.button("Registrar Faltante"):
        conn.execute("""
        INSERT INTO faltantes VALUES (NULL,?,?,?,?,?,?)
        """, (
            orden_activa, "", 0, material, cantidad,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        st.success("Registrado")
        st.rerun()

    df_falt = pd.read_sql_query(
        "SELECT * FROM faltantes WHERE Orden=?",
        conn,
        params=(orden_activa,)
    )

    df_falt["Fecha"] = pd.to_datetime(df_falt["Fecha"]).dt.strftime("%d/%m/%Y")

    st.dataframe(df_falt[["Orden", "Material", "Cantidad", "Fecha"]])

# =================================================
# VISUALIZACION + PDF
# =================================================
with tab4:

    st.subheader("TABLERO DE PRODUCCIÓN")

    if st.button("Generar Reporte PDF"):

        doc = SimpleDocTemplate("reporte_produccion.pdf")
        styles = getSampleStyleSheet()
        elementos = []

        logo = Image("Schneider.png", width=80, height=30)
        logo.hAlign = "RIGHT"
        elementos.append(logo)
        elementos.append(Spacer(1, 10))

        df = pd.read_sql_query("SELECT * FROM produccion", conn)
        df_falt = pd.read_sql_query("SELECT * FROM faltantes", conn)
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        df_falt["Fecha"] = pd.to_datetime(df_falt["Fecha"], errors="coerce")
        for orden in df["Orden"].unique():

            elementos.append(Paragraph(f"<b>Orden: {orden}</b>", styles["Title"]))
            elementos.append(Paragraph(f"Tipo de línea: {tipo_linea}", styles["Normal"]))
            elementos.append(Spacer(1, 10))

            df_ord = df[df["Orden"] == orden]
            for sec in sorted(df_ord["Seccion"].unique()):
                df_sec = df_ord[df_ord["Seccion"] == sec]
                df_sec = df_sec.sort_values("Fecha").drop_duplicates(subset=["Area"], keep="last")

                texto = f"<b>Sección {sec}</b><br/>"

                for _, row in df_sec.iterrows():
                    texto += f"{row['Area']}: {int(row['Porcentaje']) if pd.notna(row['Porcentaje']) else 0}% - {row['Turno']}<br/>"
                    texto += f"Trabajador: {row['Trabajador']} | Ubicación: {row['Ubicacion']}<br/>"

                    if row["Tiempo_muerto"] > 0 or row["Pausas"] > 0:
                        texto += f"Tiempo muerto: {row['Tiempo_muerto']} | Pausas: {row['Pausas']}<br/>"

                    if row["Razon"] and str(row["Razon"]).strip() != "":
                        texto += f"Razón: {row['Razon']}<br/>"

                    texto += "<br/>"

                elementos.append(Paragraph(texto, styles["Normal"]))
                elementos.append(Spacer(1, 12))

# AQUÍ VA (fuera del for sec)
            faltantes_ord = df_falt[df_falt["Orden"] == orden]

            if not faltantes_ord.empty:
                texto_falt = "<font color='red'><b>Faltantes:</b> "

                lista = [f"{f['Material']} ({f['Cantidad']})" for _, f in faltantes_ord.iterrows()]

                texto_falt += ", ".join(lista)
                texto_falt += "</font>"

                elementos.append(Paragraph(texto_falt, styles["Normal"]))
                elementos.append(Spacer(1, 15))    

        doc.build(elementos)
             
        with open("reporte_produccion.pdf", "rb") as file:
            st.download_button("Descargar PDF", file, "reporte_produccion.pdf")

    df = pd.read_sql_query("SELECT * FROM produccion", conn)
    df_falt = pd.read_sql_query("SELECT * FROM faltantes", conn)

if not df.empty:

        for orden in df["Orden"].unique():

            st.markdown(f"## 🧾 Orden: {orden}")

            df_ord = df[df["Orden"] == orden]

            if not df_falt[df_falt["Orden"] == orden].empty:
                st.error("⚠️ Tiene faltantes")

            for sec in sorted(df_ord["Seccion"].unique()):

                st.write(f"Sección {sec}")

                col1, col2 = st.columns(2)

                df_sec = df_ord[df_ord["Seccion"] == sec]
                df_sec = df_sec.sort_values("Fecha").drop_duplicates(subset=["Area"], keep="last")
                # Separar por tipo de alambrado
                df_ensamble = df_sec[df_sec["Area"] == "Ensamble"]

# AQUÍ ESTÁ EL FIX
                df_seccion = df_sec[df_sec["Area"].isin(["Alambrado", "Alambrado en sección"])]
                df_panel = df_sec[df_sec["Area"] == "Alambrado en panel"]


# =========================
# ENSAMBLE (col1)
# =========================
                for _, row in df_ensamble.iterrows():

                    if row["Porcentaje"] < 40:
                        color = "#e53935"
                    elif row["Porcentaje"] < 80:
                        color = "#fbc02d"
                    else:
                        color = "#43a047"

                    barra = f"""
                    <div style="background:#e0e0e0; width:100%;">
                        <div style="
                            width:{row['Porcentaje']}%;
                            min-width:120px;
                            background:{color};
                            padding:5px;
                            color:white;
                        ">
                            {row['Area']} - {int(row['Porcentaje'])}%<br>
                                {row['Trabajador']} | 📍 {row['Ubicacion']}
                        </div>
                    </div>
                    """

                    col1.markdown(barra, unsafe_allow_html=True)

# =========================
# ALAMBRADO SECCIÓN (col2)
# =========================
                for _, row in df_seccion.iterrows():

                    color = "#1e88e5"

                    barra = f"""
                    <div style="background:#e0e0e0; width:100%;">
                        <div style="
                            width:{row['Porcentaje']}%;
                            min-width:120px;
                            background:{color};
                            padding:5px;
                            color:white;
                        ">
                            {row['Area']} - {int(row['Porcentaje'])}%<br>
                                {row['Trabajador']} | 📍 {row['Ubicacion']}
                        </div>
                    </div>
                    """

                    col2.markdown(barra, unsafe_allow_html=True)
# =========================
# ALAMBRADO PANEL (col2)
# =========================
                for _, row in df_panel.iterrows():

                    color = "#8e24aa"

                    barra = f"""
                    <div style="background:#e0e0e0; width:100%;">
                        <div style="
                            width:{row['Porcentaje']}%;
                            min-width:120px;
                            background:{color};
                            padding:5px;
                            color:white;
                        ">
                            {row['Area']} - {int(row['Porcentaje'])}%<br>
                                {row['Trabajador']} | 📍 {row['Ubicacion']}
                        </div>
                    </div>
                    """

                    col2.markdown(barra, unsafe_allow_html=True)
                