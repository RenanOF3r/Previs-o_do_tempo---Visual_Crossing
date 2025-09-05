import os
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# Config
st.set_page_config(page_title="Previsão do Tempo", layout="wide", page_icon=":sun_behind_cloud:")
st.title("Previsão do Tempo")

# Helpers
def _get_api_key():
    try:
        key = st.secrets.get("visualcrossing_api_key")
    except Exception:
        key = None
    return key or os.getenv("VISUALCROSSING_API_KEY")

def _icon_for(cond: str) -> str:
    c = (cond or "").lower()
    if "snow" in c: return "❄️"
    if "rain" in c: return "🌧️"
    if "storm" in c or "thunder" in c: return "⛈️"
    if "overcast" in c: return "☁️"
    if "cloud" in c: return "⛅️"
    if "fog" in c or "mist" in c: return "🌫️"
    if "clear" in c: return "☀️"
    return "🌡️"

@st.cache_data(ttl=900)
def fetch_weather(city: str, unit: str = "metric"):
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("Defina st.secrets['visualcrossing_api_key'] ou VISUALCROSSING_API_KEY")
    unit_param = "metric" if unit == "metric" else "us"
    params = {
        "unitGroup": unit_param,
        "include": "hours,days,current",
        "key": api_key,
        "contentType": "json",
    }
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{city}"
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    current = data.get("currentConditions", {})
    resolved = data.get("resolvedAddress", city)
    now = {"resolvedAddress": resolved, **current}
    df_now = pd.Series(now)

    days = data.get("days", [])[:7]
    for d in days:
        if "precipprob" not in d:
            d["precipprob"] = d.get("precip", 0)
    df_daily = pd.DataFrame(days)
    if "datetime" in df_daily.columns:
        df_daily.rename(columns={"datetime": "date"}, inplace=True)

    hourly_rows = []
    for d in days[:2]:
        for h in d.get("hours", []):
            row = {**h}
            row["parentDate"] = d.get("date") or d.get("datetime")
            hourly_rows.append(row)
    df_hourly = pd.DataFrame(hourly_rows)
    if not df_hourly.empty and "datetime" in df_hourly.columns:
        try:
            df_hourly["timestamp"] = pd.to_datetime(
                df_hourly["parentDate"].astype(str) + " " + df_hourly["datetime"].astype(str)
            )
        except Exception:
            df_hourly["timestamp"] = pd.to_datetime(df_hourly["datetime"], errors="coerce")

    return df_now, df_hourly, df_daily

# Busca (form)
with st.form("busca"):
    cidade = st.text_input("Cidade (ex: Rio de Janeiro,BR)", value=st.session_state.get("cidade", ""))
    col_a, col_b = st.columns([3,1])
    with col_b:
        usar_f = st.toggle("Usar °F", value=st.session_state.get("use_f", False))
        buscar = st.form_submit_button("Buscar previsão")
if buscar:
    st.session_state["cidade"] = cidade.strip()
    st.session_state["use_f"] = usar_f

if "cidade" not in st.session_state or not st.session_state["cidade"]:
    st.info("Digite uma cidade para começar.")
    st.stop()

unit = "us" if st.session_state.get("use_f") else "metric"
unit_t = "°F" if unit == "us" else "°C"
vento_unit = "mph" if unit == "us" else "km/h"

try:
    with st.spinner("Buscando dados..."):
        df_now, df_hourly, df_daily = fetch_weather(st.session_state["cidade"], unit=unit)
except Exception as e:
    st.error(f"Não foi possível carregar a previsão: {e}")
    st.stop()

# Abas
tab_now, tab_today, tab_week, tab_table = st.tabs(["Agora", "Hoje (horas)", "7 dias", "Tabela"])

# Agora
with tab_now:
    icon = _icon_for(str(df_now.get("conditions", "")))
    resolved = str(df_now.get("resolvedAddress", st.session_state["cidade"]))
    dt_txt = str(df_now.get("datetime", ""))

    c1, c2, c3, c4 = st.columns(4)
    temp = df_now.get("temp")
    feels = df_now.get("feelslike")
    wind = df_now.get("windspeed")
    pprob = df_now.get("precipprob") or df_now.get("precip")

    c1.metric("Temperatura", f"{float(temp):.1f} {unit_t}" if temp is not None else "-")
    c2.metric("Sensação", f"{float(feels):.1f} {unit_t}" if feels is not None else "-")
    c3.metric("Vento", f"{float(wind):.0f} {vento_unit}" if wind is not None else "-")
    c4.metric("Chuva", f"{float(pprob or 0):.0f}%")
    st.caption(f"{icon} {resolved} • Atualizado: {dt_txt}")

# Hoje (horas)
with tab_today:
    if df_hourly.empty:
        st.info("Sem dados horários disponíveis.")
    else:
        x = pd.to_datetime(df_hourly.get("timestamp", df_hourly.get("datetime")))
        temp_h = df_hourly.get("temp")
        precip_h = df_hourly.get("precip", df_hourly.get("precipprob", pd.Series([0]*len(x))))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=temp_h, name=f"Temperatura ({unit_t})",
                                 mode="lines+markers", line=dict(color="#f94144"), marker=dict(size=6)))
        fig.add_trace(go.Bar(x=x, y=precip_h, name="Precipitação", yaxis="y2",
                             marker_color="#277da1", opacity=0.35))
        fig.update_layout(
            height=360, hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(title=unit_t), yaxis2=dict(title="mm/%", overlaying="y", side="right"),
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig, use_container_width=True)

# 7 dias
with tab_week:
    if df_daily.empty:
        st.info("Sem dados diários disponíveis.")
    else:
        days_x = pd.to_datetime(df_daily.get("date", df_daily.get("datetime")))
        tmax = df_daily.get("tempmax")
        tmin = df_daily.get("tempmin")
        pprob = df_daily.get("precipprob", pd.Series([0]*len(days_x)))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=days_x, y=tmax, name="Máx", line=dict(color="#f3722c")))
        fig.add_trace(go.Scatter(x=days_x, y=tmin, name="Mín", fill="tonexty", line=dict(color="#577590")))
        fig.add_trace(go.Bar(x=days_x, y=pprob, name="Chuva (%)", marker_color="#277da1", opacity=0.25, yaxis="y2"))
        fig.update_layout(
            height=360, hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(title=unit_t), yaxis2=dict(title="%", overlaying="y", side="right"),
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig, use_container_width=True)

# Tabela
with tab_table:
    df = df_daily.copy()
    if not df.empty:
        df["Dia"] = pd.to_datetime(df.get("date", df.get("datetime"))).dt.strftime("%a, %d/%m")
        df[""] = df.get("conditions", "").apply(_icon_for)
        cols = ["Dia", "", "tempmax", "tempmin", "conditions", "precipprob"]
        df = df[[c for c in cols if c in df.columns]]
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "tempmax": st.column_config.NumberColumn(f"Temp Máx ({unit_t})", format="%.1f"),
                "tempmin": st.column_config.NumberColumn(f"Temp Mín ({unit_t})", format="%.1f"),
                "precipprob": st.column_config.NumberColumn("Chuva", format="%d%%"),
                "conditions": st.column_config.TextColumn("Condições"),
            },
        )
