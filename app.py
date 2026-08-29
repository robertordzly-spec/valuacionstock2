# -*- coding: utf-8 -*-
"""
App de Streamlit — Indicadores de Desempeño y Riesgo de Activos Financieros
Curso: Análisis Financiero para IA

Construida siguiendo:
- "instrucciones codigo phyton.docx" (inputs, indicadores a calcular, formato)
- "E7 RD4 Metricas valuacion de activos.pdf" (definición conceptual de cada indicador)
- "E7 RD3 Modelo de valuacion de activos.xlsx" (fórmulas exactas usadas como referencia,
  extraídas celda por celda: rentabilidad/volatilidad diaria y anualizada, iSharpe,
  Pearson, Beta, iTraynor, CAPM, Alpha, z, VaR $ y VaR %).

Fuente de datos: precios de cierre ajustado de Yahoo Finance (yfinance).
"""

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from scipy import stats
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Configuración de página y estilo (look bursátil / fintech: azul, negro, blanco, Arial)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Indicadores de Valuación de Activos",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
html, body, [class*="css"]  {
    font-family: 'Arial', sans-serif !important;
}

/* Fondo general: negro con degradado azul marino */
.stApp {
    background: linear-gradient(180deg, #05070d 0%, #0a1128 45%, #0d1b3e 100%);
    color: #f5f7ff;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #060a17;
    border-right: 1px solid #1c2b52;
}
section[data-testid="stSidebar"] * {
    color: #f5f7ff !important;
}

/* Texto general blanco */
h1, h2, h3, h4, h5, h6, p, span, label, div {
    color: #f5f7ff;
}

/* Encabezado principal */
.app-title {
    font-size: 2.1rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.5px;
}
.app-subtitle {
    color: #7fa8ff;
    font-size: 1.0rem;
    margin-top: -8px;
}

/* Tarjetas / métricas */
div[data-testid="stMetric"] {
    background: linear-gradient(145deg, #0d1b3e, #111f4d);
    border: 1px solid #22407a;
    border-radius: 12px;
    padding: 10px 14px;
}
div[data-testid="stMetricLabel"] { color: #9db8ff !important; }
div[data-testid="stMetricValue"] { color: #ffffff !important; }

/* Tablas */
.stDataFrame { border-radius: 10px; overflow: hidden; }

/* Botones */
.stButton>button, .stDownloadButton>button {
    background-color: #1657ff;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    font-weight: 700;
}
.stButton>button:hover, .stDownloadButton>button:hover {
    background-color: #0d3fc4;
    color: #ffffff;
}

/* Separadores azules */
hr { border-color: #22407a; }

/* Tabs */
button[data-baseweb="tab"] { color: #cdd9ff; }
button[data-baseweb="tab"][aria-selected="true"] { color: #ffffff; border-bottom-color: #1657ff; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

PLOTLY_TEMPLATE = "plotly_dark"
BLUE = "#3d7dff"
LIGHT_BLUE = "#9db8ff"
WHITE = "#f5f7ff"

# ---------------------------------------------------------------------------
# Encabezado
# ---------------------------------------------------------------------------
st.markdown('<div class="app-title">📈 Indicadores de Valuación de Activos Financieros</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">Rentabilidad, riesgo, desempeño ajustado por riesgo y VaR — '
    'datos de Yahoo Finance</div>',
    unsafe_allow_html=True,
)
st.write("")

# ---------------------------------------------------------------------------
# Mapas de opciones (Inputs pedidos en instrucciones codigo phyton.docx)
# ---------------------------------------------------------------------------
PERIODICIDAD_MAP = {
    "Diaria": ("1d", 252),
    "Semanal": ("1wk", 52),
    "Mensual": ("1mo", 12),
}

PLAZO_CALCULO_MAP = {
    "5 días": "5d",
    "3 meses": "3mo",
    "6 meses": "6mo",
    "YTD": "ytd",
    "12 Meses": "1y",
    "5 años": "5y",
}

# Plazo VaR expresado en número de periodos de la periodicidad seleccionada
PLAZO_VAR_MAP = {
    "1 día": 1,
    "1 mes": 21,  # ~ días hábiles en un mes cuando la periodicidad es diaria
}

INDICES_SUGERIDOS = {
    "S&P 500 (EE. UU.)": "^GSPC",
    "Dow Jones (EE. UU.)": "^DJI",
    "Nasdaq 100 (EE. UU.)": "^NDX",
    "IPC (México)": "^MXX",
    "Ibovespa (Brasil)": "^BVSP",
    "DAX (Alemania)": "^GDAXI",
    "FTSE 100 (Reino Unido)": "^FTSE",
    "Otro (escribir manualmente)": "",
}

# ---------------------------------------------------------------------------
# Sidebar — Inputs
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Parámetros de la valuación")

    n_activos = st.number_input(
        "Número de activos a valuar", min_value=1, max_value=10, value=3, step=1
    )

    st.markdown("**Tickers de activos** (formato Yahoo Finance, ej. AAPL, BTC-USD)")
    tickers = []
    default_tickers = ["AAPL", "BTC-USD", "GC=F", "MSFT", "TSLA", "AMZN", "GOOGL", "META", "NVDA", "KO"]
    for i in range(int(n_activos)):
        t = st.text_input(f"Activo {i + 1}", value=default_tickers[i], key=f"ticker_{i}")
        if t.strip():
            tickers.append(t.strip().upper())

    st.markdown("---")
    idx_label = st.selectbox("Índice bursátil de referencia", list(INDICES_SUGERIDOS.keys()), index=0)
    idx_ticker = INDICES_SUGERIDOS[idx_label]
    if idx_label == "Otro (escribir manualmente)":
        idx_ticker = st.text_input("Ticker del índice", value="^GSPC")

    st.markdown("---")
    periodicidad = st.selectbox("Periodicidad de precios", list(PERIODICIDAD_MAP.keys()), index=0)
    plazo_calculo_label = st.selectbox("Plazo para calcular (historial)", list(PLAZO_CALCULO_MAP.keys()), index=4)

    st.markdown("---")
    rf_pct = st.number_input(
        "Tasa libre de riesgo anual (%) — país de origen de los activos",
        min_value=0.0, max_value=50.0, value=4.57, step=0.01,
        help="Ej. rendimiento del bono soberano a 10 años del país de origen de los activos (UST 10Y, CETES, etc.)",
    )
    rf = rf_pct / 100.0

    st.markdown("---")
    st.markdown("**Value at Risk (VaR)**")
    capital = st.number_input("Monto de capital a invertir ($)", min_value=0.0, value=100.0, step=100.0)
    intervalo_confianza_pct = st.selectbox("Intervalo de confianza", [90, 95, 99], index=1)
    intervalo_confianza = intervalo_confianza_pct / 100.0
    plazo_var_label = st.selectbox("Plazo para VaR", list(PLAZO_VAR_MAP.keys()), index=0)

    st.markdown("---")
    correr = st.button("🚀 Calcular indicadores")

# ---------------------------------------------------------------------------
# Funciones de cálculo (fórmulas replicadas de E7 RD3 Modelo de valuacion de activos.xlsx)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=3600)
def descargar_precios(ticker: str, interval: str, period: str) -> pd.Series:
    data = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
    if data.empty:
        return pd.Series(dtype=float)
    serie = data["Close"]
    if isinstance(serie, pd.DataFrame):
        serie = serie.iloc[:, 0]
    return serie.dropna()


def rendimientos_simples(precios: pd.Series) -> pd.Series:
    # F = A(t)/A(t-1) - 1   (misma fórmula que la hoja "Métricas" del Excel)
    return precios.pct_change().dropna()


def calcular_indicadores(ret_activo: pd.Series, ret_mercado: pd.Series, n_periodos_anio: int,
                          rf: float, ret_anual_mercado: float) -> dict:
    """Replica exactamente las fórmulas de la hoja Métricas (columnas M/O/P/Q...)."""
    # Alinear fechas
    df = pd.concat([ret_activo, ret_mercado], axis=1, join="inner").dropna()
    df.columns = ["activo", "mercado"]

    rent_diaria = df["activo"].mean()                       # =AVERAGE(F4:F1252)
    vol_diaria = df["activo"].std(ddof=1)                    # =STDEV.S(F4:F1252)

    rent_anual = (1 + rent_diaria) ** n_periodos_anio - 1     # =(1+M3)^252-1
    vol_anual = vol_diaria * np.sqrt(n_periodos_anio)         # =M4*SQRT(252)

    pearson = df["activo"].corr(df["mercado"])                # =CORREL(...)
    beta = stats.linregress(df["mercado"], df["activo"]).slope  # =SLOPE(activo, mercado)

    sharpe = (rent_anual - rf) / vol_anual if vol_anual else np.nan          # =(M5-Rf)/M6
    treynor = (rent_anual - rf) / beta if beta else np.nan                   # =(M5-Rf)/M9
    capm = rf + beta * (ret_anual_mercado - rf)                              # =Rf+Beta*(Rm-Rf)
    alpha = rent_anual - capm                                                # =M5-CAPM

    return {
        "Rentabilidad diaria": rent_diaria,
        "Volatilidad diaria": vol_diaria,
        "Rentabilidad anualizada": rent_anual,
        "Volatilidad anualizada": vol_anual,
        "iSharpe": sharpe,
        "Coef. Correlación Pearson": pearson,
        "BETA": beta,
        "iTraynor": treynor,
        "CAPM": capm,
        "Alpha": alpha,
        "_ret_alineados": df,
    }


def calcular_var(vol_diaria: float, capital: float, intervalo_confianza: float, plazo_periodos: int) -> dict:
    nivel_significancia = 1 - intervalo_confianza                 # =1-M15
    z = stats.norm.ppf(nivel_significancia)                       # =NORM.S.INV(nivel_significancia)
    var_monto = vol_diaria * z * capital * np.sqrt(plazo_periodos)  # =M4*M17*M14*SQRT(M18)
    var_pct = var_monto / capital if capital else np.nan           # =VaR/Capital
    return {
        "Nivel Significancia": nivel_significancia,
        'Valor "z"': z,
        "VaR $": var_monto,
        "VaR %": var_pct,
    }


def fmt_pct(x):
    return "n.d." if pd.isna(x) else f"{x * 100:,.2f}%"


def fmt_num(x, dec=3):
    return "n.d." if pd.isna(x) else f"{x:,.{dec}f}"


def fmt_money(x):
    return "n.d." if pd.isna(x) else f"${x:,.2f}"


# ---------------------------------------------------------------------------
# Cuerpo principal
# ---------------------------------------------------------------------------
if not correr:
    st.info(
        "Configura los parámetros en el panel izquierdo (activos, índice, tasa libre de riesgo, "
        "capital y confianza para el VaR) y presiona **Calcular indicadores**."
    )
    st.stop()

if not tickers:
    st.error("Ingresa al menos un ticker válido.")
    st.stop()

interval, n_periodos_anio = PERIODICIDAD_MAP[periodicidad]
period = PLAZO_CALCULO_MAP[plazo_calculo_label]
plazo_var_periodos = PLAZO_VAR_MAP[plazo_var_label]

with st.spinner("Descargando precios de Yahoo Finance y calculando indicadores..."):
    precios_mercado = descargar_precios(idx_ticker, interval, period)
    if precios_mercado.empty:
        st.error(f"No se pudieron descargar precios para el índice '{idx_ticker}'.")
        st.stop()
    ret_mercado = rendimientos_simples(precios_mercado)

    rent_diaria_m = ret_mercado.mean()
    ret_anual_mercado = (1 + rent_diaria_m) ** n_periodos_anio - 1
    vol_diaria_m = ret_mercado.std(ddof=1)
    vol_anual_mercado = vol_diaria_m * np.sqrt(n_periodos_anio)

    resultados = {}
    series_precios = {}
    errores = []

    for tk in tickers:
        precios = descargar_precios(tk, interval, period)
        if precios.empty or len(precios) < 3:
            errores.append(tk)
            continue
        series_precios[tk] = precios
        ret_activo = rendimientos_simples(precios)
        ind = calcular_indicadores(ret_activo, ret_mercado, n_periodos_anio, rf, ret_anual_mercado)
        var_res = calcular_var(ind["Volatilidad diaria"], capital, intervalo_confianza, plazo_var_periodos)
        ind.update(var_res)
        ind["Intervalo Confianza"] = intervalo_confianza
        resultados[tk] = ind

if errores:
    st.warning(f"No se pudieron descargar datos para: {', '.join(errores)}")

if not resultados:
    st.error("No hay resultados para mostrar.")
    st.stop()

# ---------------------------------------------------------------------------
# Resumen de mercado / supuestos
# ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Índice de referencia", idx_label if idx_label != "Otro (escribir manualmente)" else idx_ticker)
c2.metric("Rentabilidad anual del índice", fmt_pct(ret_anual_mercado))
c3.metric("Volatilidad anual del índice", fmt_pct(vol_anual_mercado))
c4.metric("Tasa libre de riesgo", fmt_pct(rf))

st.markdown("---")

# ---------------------------------------------------------------------------
# Tabla comparativa de indicadores (como la hoja "Métricas" del Excel)
# ---------------------------------------------------------------------------
st.markdown("### 📊 Tabla de indicadores por activo")

orden_filas = [
    "Rentabilidad anualizada", "Volatilidad anualizada", "iSharpe",
    "Coef. Correlación Pearson", "BETA", "iTraynor", "CAPM", "Alpha",
    "Intervalo Confianza", "Nivel Significancia", 'Valor "z"', "VaR $", "VaR %",
]

tabla = pd.DataFrame({tk: {k: resultados[tk][k] for k in orden_filas} for tk in resultados})

tabla_fmt = tabla.copy()
filas_pct = ["Rentabilidad anualizada", "Volatilidad anualizada", "CAPM", "Alpha",
             "Intervalo Confianza", "Nivel Significancia", "VaR %"]
filas_num = ["iSharpe", "Coef. Correlación Pearson", "BETA", "iTraynor", 'Valor "z"']
for r in tabla_fmt.index:
    for c in tabla_fmt.columns:
        val = tabla.loc[r, c]
        if r in filas_pct:
            tabla_fmt.loc[r, c] = fmt_pct(val)
        elif r == "VaR $":
            tabla_fmt.loc[r, c] = fmt_money(val)
        else:
            tabla_fmt.loc[r, c] = fmt_num(val)

st.dataframe(tabla_fmt, use_container_width=True)

csv = tabla.to_csv().encode("utf-8")
st.download_button("⬇️ Descargar tabla (CSV)", data=csv, file_name="indicadores_activos.csv", mime="text/csv")

st.markdown("---")

# ---------------------------------------------------------------------------
# Detalle por activo + gráfica de correlación / regresión vs índice
# ---------------------------------------------------------------------------
st.markdown("### 🔎 Detalle por activo")

tabs = st.tabs(list(resultados.keys()))
for tab, tk in zip(tabs, resultados.keys()):
    with tab:
        ind = resultados[tk]
        colA, colB, colC, colD = st.columns(4)
        colA.metric("Rentabilidad anualizada", fmt_pct(ind["Rentabilidad anualizada"]))
        colB.metric("Volatilidad anualizada", fmt_pct(ind["Volatilidad anualizada"]))
        colC.metric("iSharpe", fmt_num(ind["iSharpe"]))
        colD.metric("BETA", fmt_num(ind["BETA"]))

        colE, colF, colG, colH = st.columns(4)
        colE.metric("iTraynor", fmt_num(ind["iTraynor"]))
        colF.metric("CAPM", fmt_pct(ind["CAPM"]))
        colG.metric("Alpha", fmt_pct(ind["Alpha"]))
        colH.metric("Pearson", fmt_num(ind["Coef. Correlación Pearson"]))

        colI, colJ, colK, colL = st.columns(4)
        colI.metric("Intervalo Confianza", fmt_pct(ind["Intervalo Confianza"]))
        colJ.metric("Nivel Significancia", fmt_pct(ind["Nivel Significancia"]))
        colK.metric('Valor "z"', fmt_num(ind['Valor "z"']))
        colL.metric("VaR $ / %", f'{fmt_money(ind["VaR $"])}  ({fmt_pct(ind["VaR %"])})')

        # ----- Gráfica de correlación y regresión vs índice, con fórmula -----
        df_reg = ind["_ret_alineados"]
        x = df_reg["mercado"].values
        y = df_reg["activo"].values
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        x_line = np.linspace(x.min(), x.max(), 100)
        y_line = slope * x_line + intercept

        signo = "+" if intercept >= 0 else "-"
        formula_txt = f"y = {slope:.4f}x {signo} {abs(intercept):.4f}   |   R² = {r_value ** 2:.4f}"

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="markers", name=f"{tk} vs {idx_label}",
            marker=dict(color=LIGHT_BLUE, size=6, opacity=0.75),
        ))
        fig.add_trace(go.Scatter(
            x=x_line, y=y_line, mode="lines", name="Regresión lineal",
            line=dict(color=WHITE, width=2, dash="solid"),
        ))
        fig.add_annotation(
            x=0.02, y=0.98, xref="paper", yref="paper",
            text=formula_txt, showarrow=False, align="left",
            font=dict(color=WHITE, size=13, family="Arial"),
            bgcolor="rgba(22,87,255,0.35)", bordercolor=BLUE, borderwidth=1,
        )
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Arial", color=WHITE),
            title=f"Correlación y regresión: {tk} vs {idx_label}",
            xaxis_title=f"Rendimiento diario — {idx_label}",
            yaxis_title=f"Rendimiento diario — {tk}",
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            height=450,
        )
        st.plotly_chart(fig, use_container_width=True)

        # ----- Serie de precios -----
        fig_precio = go.Figure()
        fig_precio.add_trace(go.Scatter(
            x=series_precios[tk].index, y=series_precios[tk].values,
            mode="lines", name=tk, line=dict(color=BLUE, width=2),
        ))
        fig_precio.update_layout(
            template=PLOTLY_TEMPLATE,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Arial", color=WHITE),
            title=f"Precio de cierre ajustado — {tk}",
            height=320,
            margin=dict(t=50, b=30),
        )
        st.plotly_chart(fig_precio, use_container_width=True)

st.markdown("---")
st.caption(
    "Fórmulas replicadas de E7 RD3 Modelo de valuación de activos.xlsx · "
    "Definiciones conceptuales: E7 RD4 Métricas valuación de activos.pdf · "
    "Fuente de precios: Yahoo Finance (yfinance) · Rentabilidad anualizada = (1+r̄diaria)^N-1 · "
    "Volatilidad anualizada = σdiaria·√N · Sharpe=(Ranual-Rf)/σanual · Beta=pendiente(regresión vs índice) · "
    "Treynor=(Ranual-Rf)/Beta · CAPM=Rf+Beta·(Rm-Rf) · Alpha=Ranual-CAPM · "
    "VaR=σdiaria·z·Capital·√plazo, con z=NORM.INV(1-Confianza)."
)
