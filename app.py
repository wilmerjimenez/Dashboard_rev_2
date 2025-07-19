import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
from pathlib import Path

st.set_page_config(page_title="Dashboard Proyectos Cambio Climático", layout="wide")

# ---------- Style ----------
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg,#0d1b2a 0%,#1b263b 100%);
    }
    .main .block-container { padding-top:1rem; padding-bottom:1rem; }
    h2, h3, h4, h5, h6 { color:white; }
    p, div, span { color:#d9d9d9; }
    .card { background-color:#1e2a3a; border-radius:16px; padding:1rem; box-shadow:0 4px 10px rgba(0,0,0,.4); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Data ----------
@st.cache_data
def load_data(upload):
    """Carga la hoja 'Resumen 2025' del Excel y la devuelve como DataFrame"""
    return pd.read_excel(upload, sheet_name="Resumen 2025")

st.sidebar.title("📊 Parámetros")
upload = st.sidebar.file_uploader("Carga tu Excel", type=["xlsx", "xls"])
if upload is None:
    default_file = Path(__file__).with_name("00_Planificacion_CambioClimatico_dashboard_2025jul19_2.xlsx")
    if default_file.exists():
        st.sidebar.info("Usando archivo de ejemplo incluido.")
        upload = default_file.open("rb")
    else:
        st.sidebar.warning("Sube un archivo para comenzar…")
        st.stop()

df = load_data(upload)

# ---------- Limpieza rápida de campos numéricos ----------
for col in [
    "Monto requerido (USD)",
    "Monto ejecutado (USD)",
    "Superficie intervenida (ha)",
    "CO2 eq evitado (t)",
    "Porcentaje de avance global",
]:
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(r"[^0-9\.]", "", regex=True),
            errors="coerce",
        )

# ---------- Coordenadas de provincias ----------
province_coords = {
    "Azuay": (-2.8974, -79.0045), "Bolívar": (-1.7482, -79.1817), "Cañar": (-2.5680, -78.9569),
    "Carchi": (0.5026, -77.9332), "Chimborazo": (-1.6789, -78.6569), "Cotopaxi": (-0.9101, -78.6965),
    "El Oro": (-3.2586, -79.9576), "Esmeraldas": (0.9510, -79.6517), "Galápagos": (-0.9538, -90.9656),
    "Guayas": (-2.3100, -79.8977), "Imbabura": (0.3496, -78.1230), "Loja": (-3.9931, -79.2042),
    "Los Ríos": (-1.0295, -79.4630), "Manabí": (-1.0543, -80.4520), "Morona Santiago": (-2.2381, -78.3715),
    "Napo": (-0.9956, -77.8120), "Orellana": (-0.5066, -76.9858), "Pastaza": (-1.4604, -78.0018),
    "Pichincha": (-0.2295, -78.5243), "Santa Elena": (-2.1780, -80.9593),
    "Santo Domingo de los Tsáchilas": (-0.2528, -79.2029), "Sucumbíos": (0.0884, -76.8833),
    "Tungurahua": (-1.0370, -78.5595), "Zamora Chinchipe": (-4.0667, -78.9529),
}

# ---------- Layout ----------
st.title("Dashboard de Proyectos de Cambio Climático")

# ===================== ROW 1 =====================
row1_col1, row1_col2, row1_col3 = st.columns([1.1, 1.3, 1.2])

# ----- Donut: distribución por fase -----
with row1_col1:
    st.subheader("Distribución por fase")
    fase_counts = df["Fase"].fillna("Sin fase").value_counts().reset_index()
    if not fase_counts.empty:
        fig_donut = px.pie(
            fase_counts,
            values="Fase",
            names="index",
            hole=0.55,
            color_discrete_sequence=["#32ff7e", "#18dcff", "#ef5777", "#ffbe0b"],
        )
        fig_donut.update_layout(margin=dict(t=0,b=0,l=0,r=0), showlegend=False,
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.info("No hay datos de fases.")

# ----- Mapa de proyectos -----
with row1_col2:
    st.subheader("Ubicación de proyectos")
    points = []
    for _, r in df.iterrows():
        prov_raw = str(r.get("Provincia_mapa") or r.get("Provincia/Estado") or "")
        for p in [p.strip().title() for p in prov_raw.split(',') if p.strip()]:
            if p in province_coords:
                lat, lon = province_coords[p]
                points.append({"lat": lat, "lon": lon, "Proyecto": r["Plan/Proyecto/Iniciativa"]})
    if points:
        st.pydeck_chart(
            pdk.Deck(
                map_style="mapbox://styles/mapbox/dark-v10",
                initial_view_state=pdk.ViewState(latitude=-1.5, longitude=-78.2, zoom=5.2),
                tooltip={"text": "{Proyecto}"},
                layers=[pdk.Layer("ScatterplotLayer", data=points,
                                   get_position="[lon, lat]", get_color="[255,165,0,160]",
                                   get_radius=50000, pickable=True)],
            )
        )
    else:
        st.info("No se pudieron geolocalizar proyectos.")

# ----- Tres áreas apiladas -----
with row1_col3:
    st.subheader("Finanzas y avance")
    df["Fecha fin"] = pd.to_datetime(df["Fecha fin"], errors="coerce")
    df["Año"] = df["Fecha fin"].dt.year
    area_df = df.groupby("Año")[[
        "Monto ejecutado (USD)", "Monto requerido (USD)", "CO2 eq evitado (t)"
    ]].sum().reset_index().fillna(0)
    metrics = ["Monto ejecutado (USD)", "Monto requerido (USD)", "CO2 eq evitado (t)"]
    colors = ["#18dcff", "#ef5777", "#4bcffa"]
    for m, c in zip(metrics, colors):
        if area_df[m].sum() == 0:
            continue
        fig = px.area(area_df, x="Año", y=m, color_discrete_sequence=[c])
        fig.update_layout(height=140, margin=dict(l=0,r=0,t=0,b=0),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

# ===================== ROW 2 =====================
st.markdown("---")

st.subheader("Ejecución presupuestaria por proyecto")
bar_df = (
    df.groupby("Plan/Proyecto/Iniciativa")[["Monto requerido (USD)", "Monto ejecutado (USD)"]]
    .sum()
    .reset_index()
    .sort_values("Monto requerido (USD)")
)

fig_bar = go.Figure()
fig_bar.add_bar(y=bar_df["Plan/Proyecto/Iniciativa"], x=bar_df["Monto requerido (USD)"],
                name="Requerido", orientation="h", marker=dict(color="#ffbe0b"))
fig_bar.add_bar(y=bar_df["Plan/Proyecto/Iniciativa"], x=bar_df["Monto ejecutado (USD)"],
                name="
