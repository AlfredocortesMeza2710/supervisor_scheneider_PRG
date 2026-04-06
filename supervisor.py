# PRODUCCION PARA MONITOREO DE ORDENES - FINAL
# HECHO POR ALFREDO CORTES MEZA
# PRODUCTION LINE INTELLIGENCE MONITOR (PLIM)

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(layout="wide")
st.title("LINEA DE PRODUCCIÓN")

conn = sqlite3.connect("produccion.db", check_same_thread=False)

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
    Tiempo_efectivo REAL,
    Tiempo_muerto REAL,
    Pausas REAL,
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

    df = pd.read_sql_query("SELECT * FROM produccion", conn)
    df_falt = pd.read_sql_query("SELECT * FROM faltantes", conn)
    params=(orden_activa, seccion_sel)
    

    bloqueado = not df.empty and not editar

    if bloqueado:
        st.warning("Sección bloqueada")

    porcentaje = st.slider("Avance (%)", 0, 100, step=10, disabled=bloqueado)
    turno = st.selectbox("Turno", ["Día", "Noche"], disabled=bloqueado)

    te = st.number_input("Tiempo efectivo", value=0.0, disabled=bloqueado)
    tm = st.number_input("Tiempo muerto", value=0.0, disabled=bloqueado)
    pausa = st.number_input("Pausas", value=0.0, disabled=bloqueado)

    if st.button("Guardar Ensamble", disabled=bloqueado):
        conn.execute("""
        INSERT INTO produccion VALUES (NULL,?,?,?,?,?,?,?,?,?)
        """, (
            orden_activa, "Ensamble", seccion_sel, porcentaje, turno,
            te, tm, pausa,
            datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        st.success("Guardado")
        st.rerun()

# =================================================
# ALAMBRADO
# =================================================
with tab2:

    st.subheader(f"Alambrado - {orden_activa}")

    seccion_sel = st.selectbox("Sección", range(1, secciones_total+1), key="alm_sec")

    df = pd.read_sql_query(
        "SELECT * FROM produccion WHERE Orden=? AND Area='Alambrado' AND Seccion=?",
        conn,
        params=(orden_activa, seccion_sel)
    )

    bloqueado = not df.empty and not editar

    if bloqueado:
        st.warning("Sección bloqueada")

    porcentaje = st.slider("Avance (%)", 0, 100, step=10, key="alm", disabled=bloqueado)
    turno = st.selectbox("Turno", ["Día", "Noche"], key="alm_t", disabled=bloqueado)

    te = st.number_input("Tiempo efectivo", key="alm_te", value=0.0, disabled=bloqueado)
    tm = st.number_input("Tiempo muerto", key="alm_tm", value=0.0, disabled=bloqueado)
    pausa = st.number_input("Pausas", key="alm_p", value=0.0, disabled=bloqueado)

    if st.button("Guardar Alambrado", disabled=bloqueado):
        conn.execute("""
        INSERT INTO produccion VALUES (NULL,?,?,?,?,?,?,?,?,?)
        """, (
            orden_activa, "Alambrado", seccion_sel, porcentaje, turno,
            te, tm, pausa,
            datetime.today().strftime("%Y-%m-%d %H:%M:%S")
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
            datetime.today().strftime("%Y-%m-%d")
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

        df = pd.read_sql_query("SELECT * FROM produccion", conn)
        df_falt = pd.read_sql_query("SELECT * FROM faltantes", conn)

        for orden in df["Orden"].unique():

            elementos.append(Paragraph(f"<b>Orden: {orden}</b>", styles["Title"]))
            elementos.append(Spacer(1, 10))

            df_ord = df[df["Orden"] == orden]
            for sec in sorted(df_ord["Seccion"].unique()):
                df_sec = df_ord[df_ord["Seccion"] == sec]
                df_sec = df_sec.sort_values("Fecha").drop_duplicates(subset=["Area"], keep="last")

                texto = f"<b>Sección {sec}</b><br/>"

    # Producción
                for _, row in df_sec.iterrows():
                    texto += f"{row['Area']}: {int(row['Porcentaje'])}%<br/>"

                elementos.append(Paragraph(texto, styles["Normal"]))
                elementos.append(Spacer(1, 12))
            faltantes_ord = df_falt[df_falt["Orden"] == orden]
            if not faltantes_ord.empty:
                texto_falt = "<font color='red'><b>Faltantes:</b> "

                lista = []
                for _, f in faltantes_ord.iterrows():
                    lista.append(f"{f['Material']} ({f['Cantidad']})")

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

                for _, row in df_sec.iterrows():

                    # 🔥 SEMÁFORO
                    if row["Porcentaje"] < 40:
                        color = "#e53935"  # rojo
                    elif row["Porcentaje"] < 80:
                        color = "#fbc02d"  # amarillo
                    else:
                        color = "#43a047"  # verde

                    barra = f"""
                    <div style="background:#e0e0e0; width:100%;">
                        <div style="
                            width:{row['Porcentaje']}%;
                            min-width:120px;
                            background:{color};
                            padding:5px;
                            color:white;
                            white-space:nowrap;
                            overflow:hidden;
                        ">
                            {row['Area']} - {int(row['Porcentaje'])}%
                        </div>
                    </div>
                    """

                    if row["Area"] == "Ensamble":
                        col1.markdown(barra, unsafe_allow_html=True)
                    else:
                        col2.markdown(barra, unsafe_allow_html=True)

    else:
        st.info("No hay datos")