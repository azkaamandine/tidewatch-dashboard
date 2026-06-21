import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

# 1. Konfigurasi Halaman
st.set_page_config(page_title="NaviWatch - Java Maritime Network", page_icon="⚓", layout="wide", initial_sidebar_state="expanded")

# --- CSS: TEMA DARK TERINSPIRASI ECDIS / PETA NAVIGASI ---
# Logika warna: gelap = laut dalam, cyan terang = "safety contour" (garis kedalaman aman
# di peta navigasi sungguhan), jadi cyan dipakai sebagai aksen hidup yang relevan
# secara fungsional, bukan sekadar dekorasi.
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@500;600&display=swap');

    html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }

    .stApp {
        background: linear-gradient(180deg, #041018 0%, #07202F 55%, #0A2638 100%);
        background-attachment: fixed;
    }

    /* bar tipis di atas, motif "skala kedalaman" pada peta navigasi */
    .depth-scale-bar { height: 4px; width: 100%; margin-bottom: 22px;
        background: linear-gradient(90deg, #041018 0%, #2DD4DA 50%, #041018 100%); border-radius: 2px; }

    h1, h2, h3 { font-family: 'Inter', sans-serif !important; font-weight: 700 !important; color: #F4F8FB !important; letter-spacing: -0.2px; }
    p, span, label, div { font-family: 'Inter', sans-serif; }

    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #0E2C42 0%, #0A1F30 100%);
        border: 1px solid #1B3A52;
        border-top: 2px solid #2DD4DA;
        padding: 10px 12px;
        border-radius: 8px;
        box-shadow: 0 4px 14px rgba(2, 10, 18, 0.45);
    }

    div[data-testid="stMetricValue"] > div, [data-testid="stMetricValue"] {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 19px !important;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        word-wrap: break-word !important;
        line-height: 1.2 !important;
        color: #F4F8FB !important;
        font-weight: 600 !important;
    }

    [data-testid="stMetricLabel"] { color: #2DD4DA !important; font-size: 12px !important; text-transform: uppercase; letter-spacing: 0.6px; }

    .status-box-aman { background: linear-gradient(135deg, rgba(52, 211, 153, 0.16), rgba(52, 211, 153, 0.05)); border: 1px solid #34D399; border-radius: 8px; padding: 20px; text-align: center; color: #34D399; box-shadow: 0 4px 14px rgba(2, 10, 18, 0.45); }
    .status-box-bahaya { background: linear-gradient(135deg, rgba(255, 107, 91, 0.18), rgba(255, 107, 91, 0.05)); border: 1px solid #FF6B5B; border-radius: 8px; padding: 20px; text-align: center; color: #FF6B5B; box-shadow: 0 4px 14px rgba(2, 10, 18, 0.45); }

    .ekstrem-box { background: linear-gradient(135deg, #0E2C42 0%, #0A1F30 100%); border: 1px solid #1B3A52; padding: 12px 14px; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 4px 14px rgba(2, 10, 18, 0.35); }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# DATABASE TPXO & BATIMETRI INTERNAL
# ==========================================
STASIUN_DB = {
    'Tanjung Priok, Jakarta': {'lat': -6.10, 'lon': 106.87, 'alur': 14.0, 'msl': 1.10, 'M2': 0.12, 'S2': 0.05, 'K1': 0.25, 'O1': 0.15},
    'Tanjung Emas, Semarang': {'lat': -6.93, 'lon': 110.42, 'alur': 10.0, 'msl': 0.80, 'M2': 0.10, 'S2': 0.04, 'K1': 0.22, 'O1': 0.14},
    'Tanjung Perak, Surabaya': {'lat': -7.19, 'lon': 112.74, 'alur': 13.0, 'msl': 1.50, 'M2': 0.45, 'S2': 0.20, 'K1': 0.35, 'O1': 0.25},
    'Pelabuhan Cirebon, Jawa Barat': {'lat': -6.71, 'lon': 108.56, 'alur': 6.5, 'msl': 0.85, 'M2': 0.15, 'S2': 0.06, 'K1': 0.28, 'O1': 0.16},
    'Tanjung Intan, Cilacap': {'lat': -7.74, 'lon': 108.99, 'alur': 12.0, 'msl': 1.50, 'M2': 0.60, 'S2': 0.25, 'K1': 0.15, 'O1': 0.10},
    'Pelabuhan Ratu, Sukabumi': {'lat': -7.03, 'lon': 106.55, 'alur': 10.0, 'msl': 1.30, 'M2': 0.55, 'S2': 0.22, 'K1': 0.12, 'O1': 0.08},
    'Pelabuhan Merak, Banten': {'lat': -5.93, 'lon': 105.99, 'alur': 10.0, 'msl': 0.90, 'M2': 0.25, 'S2': 0.10, 'K1': 0.20, 'O1': 0.12},
    'Pelabuhan Ketapang, Banyuwangi': {'lat': -8.14, 'lon': 114.39, 'alur': 9.0, 'msl': 1.20, 'M2': 0.40, 'S2': 0.18, 'K1': 0.15, 'O1': 0.10}
}

if 'lokasi_pilihan' not in st.session_state:
    st.session_state.lokasi_pilihan = list(STASIUN_DB.keys())[0]

@st.cache_data(ttl=1800)
def fetch_realtime_marine_data(lat, lon):
    avg_hs, max_hs = 0.45, 0.70
    wind_speed, wind_dir = 8.5, 45.0
    try:
        url_wave = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&hourly=wave_height&timezone=auto"
        r_wave = requests.get(url_wave, timeout=5)
        if r_wave.status_code == 200:
            j_wave = r_wave.json()
            wave_heights = j_wave['hourly']['wave_height']
            avg_hs = np.nanmean(wave_heights[:24]) if wave_heights else 0.4
            max_hs = np.nanmax(wave_heights[:24]) if wave_heights else 0.6
        url_wind = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=wind_speed_10m,wind_direction_10m&wind_speed_unit=kn&timezone=auto"
        r_wind = requests.get(url_wind, timeout=5)
        if r_wind.status_code == 200:
            j_wind = r_wind.json()
            wind_speed = j_wind['current']['wind_speed_10m']
            wind_dir = j_wind['current']['wind_direction_10m']
    except:
        pass
    return avg_hs, max_hs, wind_speed, wind_dir

@st.cache_data
def generate_tmd_prediction(target_date, days_duration, lokasi):
    data = STASIUN_DB[lokasi]
    start_predict = datetime.combine(target_date, datetime.min.time())
    end_predict = start_predict + timedelta(days=days_duration)
    time_series = pd.date_range(start=start_predict, end=end_predict, freq='10min')
    t_hours = (time_series - datetime(2025, 1, 1)).total_seconds() / 3600.0
    y_pred = np.zeros(len(t_hours))
    omega_M2, omega_S2 = 2 * np.pi / 12.4206, 2 * np.pi / 12.0000
    omega_K1, omega_O1 = 2 * np.pi / 23.9345, 2 * np.pi / 25.8193
    y_pred += data['M2'] * np.cos(omega_M2 * t_hours - 0.5)
    y_pred += data['S2'] * np.cos(omega_S2 * t_hours - 1.0)
    y_pred += data['K1'] * np.cos(omega_K1 * t_hours - 1.5)
    y_pred += data['O1'] * np.cos(omega_O1 * t_hours - 2.0)
    y_pred += data['msl']
    return pd.DataFrame({'Time': time_series, 'Prediksi_Pasut': y_pred})

with st.sidebar:
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { background: linear-gradient(180deg, #030D15 0%, #06202F 100%) !important; border-right: 1px solid #1B3A52; }
        .sidebar-title-container { text-align: center; margin-bottom: 28px; padding-bottom: 16px; border-bottom: 1px solid #1B3A52; }
        .sidebar-main-title { font-family: 'Inter', sans-serif; color: #F4F8FB; font-size: 1.55rem; font-weight: 800; letter-spacing: 1px; margin-top: 8px; }
        .sidebar-subtitle { font-family: 'IBM Plex Mono', monospace; color: #2DD4DA; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 2px; }
        .control-panel-box { background: linear-gradient(135deg, #0E2C42 0%, #0A1F30 100%); border: 1px solid #1B3A52; border-left: 3px solid #2DD4DA; border-radius: 8px; padding: 15px; margin-bottom: 20px; box-shadow: 0 4px 14px rgba(2, 10, 18, 0.4); }
        .control-header { font-family: 'Inter', sans-serif; color: #F4F8FB; font-size: 0.95rem; font-weight: 700; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 0.5px; }
        </style>
        <div class="sidebar-title-container">
            <div style='font-size: 40px; color: #2DD4DA; filter: drop-shadow(0 0 8px rgba(45,212,218,0.5));'>⚓</div>
            <div class="sidebar-main-title">NAVIWATCH</div>
            <div class="sidebar-subtitle">Pusat Kendali Navigasi</div>
        </div>
        <div class="control-panel-box">
            <div class="control-header">Kontrol Panel</div>
    """, unsafe_allow_html=True)
    mode_tampilan = st.radio("Rentang Waktu:", ["Harian (24 Jam)", "Bulanan (30 Hari)"])
    st.markdown("<br>", unsafe_allow_html=True)
    tanggal_pilihan = st.date_input("Pilih Tanggal Analisis:", datetime(2025, 1, 15))
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Sumber Data: TPXO Global Model & Open-Meteo Weather API")

st.markdown('<div class="depth-scale-bar"></div>', unsafe_allow_html=True)
st.markdown("""
    <div style="border-bottom: 1px solid #1B3A52; padding-bottom: 18px; margin-bottom: 26px;">
        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; letter-spacing: 3px; color: #2DD4DA; text-transform: uppercase; margin-bottom: 8px;">
            Sistem Pendukung Keputusan &middot; Jaringan Pelabuhan Jawa
        </div>
        <div style="font-family: 'Inter', sans-serif; font-weight: 800; font-size: 2.7rem; letter-spacing: -0.5px; line-height: 1.1;
                    background: linear-gradient(90deg, #F4F8FB 35%, #2DD4DA 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            NaviWatch
        </div>
        <div style="font-size: 0.95rem; color: #9FB3C8; margin-top: 6px;">
            Pemantauan pasut, gelombang, dan vektor angin untuk keselamatan navigasi pelabuhan secara terintegrasi.
        </div>
    </div>
""", unsafe_allow_html=True)

row1_col1, row1_col2 = st.columns([3, 1])

with row1_col1:
    st.subheader("🗺️ Peta Jaringan Stasiun")
    df_map = pd.DataFrame([{'Lokasi': k, 'Lat': v['lat'], 'Lon': v['lon']} for k, v in STASIUN_DB.items()])
    df_map['Nama_Pendek'] = df_map['Lokasi'].apply(lambda x: x.split(',')[0].upper())
    df_map['Status'] = df_map['Lokasi'].apply(lambda x: 'Terpilih' if x == st.session_state.lokasi_pilihan else 'Stasiun Lain')

    fig_map = px.scatter_mapbox(
        df_map, lat="Lat", lon="Lon", hover_name="Lokasi", color="Status", custom_data=["Lokasi"],
        text="Nama_Pendek", color_discrete_map={'Terpilih': '#2DD4DA', 'Stasiun Lain': '#F4F8FB'},
        zoom=5.8, center={"lat": -7.0, "lon": 110.2}, height=500
    )
    fig_map.update_traces(
        mode='markers+text', textposition='top center', textfont=dict(size=12, color='white', family='Inter'),
        marker=dict(size=10), selector=dict(type='scattermapbox')
    )
    fig_map.update_layout(
        mapbox_style="white-bg",
        mapbox_layers=[{
            "below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri",
            "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"]
        }],
        margin={"r":0,"t":0,"l":0,"b":0}, clickmode='event+select', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(font=dict(color='#F4F8FB', family='Inter'))
    )
    map_selection = st.plotly_chart(fig_map, width="stretch", on_select="rerun", selection_mode="points")
    if map_selection and "selection" in map_selection:
        titik_terpilih = map_selection["selection"]["points"]
        if len(titik_terpilih) > 0:
            nama_lokasi_klik = titik_terpilih[0]["customdata"][0]
            if nama_lokasi_klik != st.session_state.lokasi_pilihan:
                st.session_state.lokasi_pilihan = nama_lokasi_klik
                st.rerun()

lokasi = st.session_state.lokasi_pilihan
data_lokasi = STASIUN_DB[lokasi]
msl_val = data_lokasi['msl']
batimetri_peta = data_lokasi['alur']

avg_wave_hs, max_wave_hs, current_wind_speed, current_wind_dir = fetch_realtime_marine_data(data_lokasi['lat'], data_lokasi['lon'])
amp_gelombang = max_wave_hs / 2

durasi_hari = 1 if mode_tampilan == "Harian (24 Jam)" else 30
df_display = generate_tmd_prediction(tanggal_pilihan, durasi_hari, lokasi)

with row1_col2:
    st.subheader("📍 Stasiun Aktif")
    st.markdown(f"## {lokasi}")
    m_col1, m_col2 = st.columns(2)
    m_col1.metric("MSL (Rata-rata)", f"{msl_val:.2f} m")
    m_col2.metric("HHWL (Maks)", f"{df_display['Prediksi_Pasut'].max():.2f} m")
    m_col3, m_col4 = st.columns(2)
    m_col3.metric("LLWL (Min)", f"{df_display['Prediksi_Pasut'].min():.2f} m")

# ==========================================
# KIRI (METRIK), KANAN (GRAFIK ATAS, RADAR BAWAH)
# ==========================================
st.markdown("---")
st.subheader(f"📊 Kondisi Hidro-Meteorologi Harian: {tanggal_pilihan.strftime('%d %B %Y')}")
df_1_hari = df_display.head(144).copy()
df_1_hari['is_pasang'] = (df_1_hari['Prediksi_Pasut'] > df_1_hari['Prediksi_Pasut'].shift(1)) & (df_1_hari['Prediksi_Pasut'] > df_1_hari['Prediksi_Pasut'].shift(-1))
df_1_hari['is_surut'] = (df_1_hari['Prediksi_Pasut'] < df_1_hari['Prediksi_Pasut'].shift(1)) & (df_1_hari['Prediksi_Pasut'] < df_1_hari['Prediksi_Pasut'].shift(-1))
df_ekstrem = df_1_hari[df_1_hari['is_pasang'] | df_1_hari['is_surut']].copy()
df_ekstrem['Tipe'] = np.where(df_ekstrem['is_pasang'], 'Pasang', 'Surut')

harian_col1, harian_col2 = st.columns([1, 2.5])

with harian_col1:
    st.markdown(f"""
    <div class="ekstrem-box" style="border-left: 3px solid #2DD4DA;">
        <span style='color:#2DD4DA; font-size:13px; text-transform:uppercase; letter-spacing:0.5px;'>🌊 Tinggi Gelombang (Hs)</span><br>
        <span style='font-family:"IBM Plex Mono", monospace; font-size:25px; color:#F4F8FB; font-weight:600;'>{max_wave_hs:.2f} m</span><br>
        <span style='font-size:12px; color:#9FB3C8;'>Amplitudo: ±{amp_gelombang:.2f} m</span>
    </div>
    <div class="ekstrem-box" style="border-left: 3px solid #2DD4DA;">
        <span style='color:#2DD4DA; font-size:13px; text-transform:uppercase; letter-spacing:0.5px;'>🍃 Vektor Angin Permukaan</span><br>
        <span style='font-family:"IBM Plex Mono", monospace; font-size:25px; color:#F4F8FB; font-weight:600;'>{current_wind_speed:.1f} Knot</span><br>
        <span style='font-size:12px; color:#9FB3C8;'>Arah Datang: {current_wind_dir}°</span>
    </div>
    """, unsafe_allow_html=True)

    if not df_ekstrem.empty:
        for idx, row in df_ekstrem.iterrows():
            color = "#34D399" if row['Tipe'] == 'Pasang' else "#FF6B5B"
            simbol = "🟢" if row['Tipe'] == 'Pasang' else "🔴"
            st.markdown(f"""
            <div class="ekstrem-box" style="border-left: 3px solid {color};">
                <span style='color:{color}; font-size:13px; text-transform:uppercase; letter-spacing:0.5px;'>{simbol} Puncak {row['Tipe']}</span><br>
                <span style='font-family:"IBM Plex Mono", monospace; font-size:21px; color:#F4F8FB; font-weight:600;'>{row['Prediksi_Pasut']:.2f} m</span>
                <span style='color:#9FB3C8; font-size:12px;'>pukul {row['Time'].strftime('%H:%M')}</span>
            </div>
            """, unsafe_allow_html=True)

with harian_col2:
    fig_harian = go.Figure()
    fig_harian.add_trace(go.Scatter(x=df_1_hari['Time'], y=df_1_hari['Prediksi_Pasut'] + amp_gelombang, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
    fig_harian.add_trace(go.Scatter(x=df_1_hari['Time'], y=df_1_hari['Prediksi_Pasut'] - amp_gelombang, mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(45, 212, 218, 0.12)', name='Wave Envelope'))
    fig_harian.add_trace(go.Scatter(x=df_1_hari['Time'], y=df_1_hari['Prediksi_Pasut'], mode='lines', name='Elevasi Pasut (m)', line=dict(color='#2DD4DA', width=3)))

    df_pasang = df_1_hari[df_1_hari['is_pasang']]
    fig_harian.add_trace(go.Scatter(x=df_pasang['Time'], y=df_pasang['Prediksi_Pasut'], mode='markers+text', name='Pasang', marker=dict(color='#34D399', size=9), text=[f"{v:.2f} m" for v in df_pasang['Prediksi_Pasut']], textposition="top center", textfont=dict(color='#9FB3C8', size=10)))
    df_surut = df_1_hari[df_1_hari['is_surut']]
    fig_harian.add_trace(go.Scatter(x=df_surut['Time'], y=df_surut['Prediksi_Pasut'], mode='markers+text', name='Surut', marker=dict(color='#FF6B5B', size=9), text=[f"{v:.2f} m" for v in df_surut['Prediksi_Pasut']], textposition="bottom center", textfont=dict(color='#9FB3C8', size=10)))

    fig_harian.update_layout(
        height=350, margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family='Inter'),
        title=dict(text="GRAFIK ELEVASI MUKA AIR AKTUAL (PASUT + GELOMBANG)", font=dict(color="#2DD4DA", size=11, family='IBM Plex Mono')),
        xaxis=dict(showgrid=False, tickformat="%H:%M", tickfont=dict(color="#9FB3C8")), yaxis=dict(gridcolor="#1B3A52", tickfont=dict(color="#9FB3C8")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#9FB3C8"))
    )
    st.plotly_chart(fig_harian, use_container_width=True, config={'displayModeBar': False})

    st.markdown("<br>", unsafe_allow_html=True)

    r_col1, r_col2, r_col3 = st.columns([1, 1.5, 1])
    with r_col2:
        fig_wind = go.Figure()
        fig_wind.add_trace(go.Scatterpolar(r=[0, current_wind_speed], theta=[0, current_wind_dir], mode='lines+markers', line=dict(color='#2DD4DA', width=4), marker=dict(size=[0, 15], symbol='triangle-up', color='#2DD4DA')))
        fig_wind.update_layout(
            polar=dict(
              radialaxis=dict(showticklabels=True, gridcolor="#1B3A52", tickfont=dict(size=9, color="#9FB3C8")),
              angularaxis=dict(thetaunit="degrees", rotation=90, direction="clockwise", gridcolor="#1B3A52", tickfont=dict(color="#F4F8FB", size=11))
            ),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=280, margin=dict(l=20, r=20, t=35, b=20), showlegend=False,
            title=dict(text="Radar Arah Embusan Angin", font=dict(color="#2DD4DA", size=11, family='IBM Plex Mono'), x=0.5)
        )
        st.plotly_chart(fig_wind, use_container_width=True, config={'displayModeBar': False})

st.markdown("---")
row2_col1, row2_col2 = st.columns([3, 1])
with row2_col2:
    st.subheader("⚙️ Parameter Kapal")
    draft = st.number_input("Draft Kapal (m):", 1.0, 20.0, 8.5)
    ukc = st.number_input("UKC (m):", 0.0, 5.0, 1.0)
    ambang_keamanan = draft + ukc
    df_display['Total_Kedalaman'] = batimetri_peta + df_display['Prediksi_Pasut']
    kondisi_min_aktual = df_display['Total_Kedalaman'].min() - amp_gelombang

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🛡️ Status Keselamatan")

    if kondisi_min_aktual < ambang_keamanan:
        st.markdown(f'<div class="status-box-bahaya"><h2>BAHAYA: KANDAS</h2><p>Kedalaman aktual terendah ({kondisi_min_aktual:.2f} m) melanggar batas UKC.</p></div>', unsafe_allow_html=True)
    elif current_wind_speed > 20.0:
        st.markdown(f'<div class="status-box-bahaya"><h2>BAHAYA: ANGIN</h2><p>Kecepatan Angin ({current_wind_speed:.1f} knot) berbahaya bagi manuver lunas dan lambung lateral kapal.</p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-box-aman"><h2>AMAN OPERASIONAL</h2><p>Kondisi dinamis laut aman untuk manuver.</p></div>', unsafe_allow_html=True)

with row2_col1:
    st.subheader("📉 Simulasi Kedalaman Aktual (Pasut + Gelombang)")
    fig_depth = go.Figure()
    fig_depth.add_trace(go.Scatter(x=df_display['Time'], y=df_display['Total_Kedalaman'] + amp_gelombang, mode='lines', line=dict(width=0), showlegend=False))
    fig_depth.add_trace(go.Scatter(x=df_display['Time'], y=df_display['Total_Kedalaman'] - amp_gelombang, mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(45, 212, 218, 0.12)', name='Wave Envelope'))
    fig_depth.add_trace(go.Scatter(x=df_display['Time'], y=df_display['Total_Kedalaman'], mode='lines', name='Kedalaman Pasut', line=dict(color='#2DD4DA', width=3)))
    fig_depth.add_hline(y=ambang_keamanan, line_dash="dash", line_color="#FF6B5B", annotation_text="Batas Aman Kapal", annotation_font_color="#FF6B5B")
    fig_depth.update_layout(xaxis_title="Waktu", yaxis_title="Kedalaman (m)", height=450, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#9FB3C8", family='Inter'), xaxis=dict(gridcolor="#1B3A52"), yaxis=dict(gridcolor="#1B3A52"), legend=dict(font=dict(color="#9FB3C8")))
    st.plotly_chart(fig_depth, use_container_width=True)

# --- ROW 3: JENDELA WAKTU AMAN ---
st.markdown("---")
st.subheader("🕒 Jendela Waktu Aman Navigasi Alur Pelabuhan")
df_display['is_safe'] = (df_display['Total_Kedalaman'] - amp_gelombang) >= ambang_keamanan

if current_wind_speed > 20.0:
    st.error(f"Jendela navigasi ditutup total: kecepatan angin saat ini terpantau {current_wind_speed:.1f} knot, di atas ambang batas aman (20 knot). Risiko penyimpangan lunas dinamis tinggi akibat gaya dorong angin lateral.")
elif max_wave_hs > 1.5:
    st.error("Jendela navigasi ditutup akibat hantaman gelombang tinggi ekstrem di pelabuhan.")
elif df_display['is_safe'].all():
    st.success("Kapal dapat melakukan manuver olah gerak kapan saja tanpa batasan rentang waktu.")
elif not df_display['is_safe'].any():
    st.error("Alur tertutup total! Air terlalu dangkal sepanjang hari untuk dilewati jenis kapal ini.")
else:
    df_display['block'] = (df_display['is_safe'] != df_display['is_safe'].shift(1)).cumsum()
    safe_blocks = df_display[df_display['is_safe']].groupby('block')

    jadwal = []
    for _, block in safe_blocks:
        waktu_mulai = block['Time'].iloc[0]
        waktu_selesai = block['Time'].iloc[-1]
        durasi = (waktu_selesai - waktu_mulai).total_seconds() / 3600
        if durasi >= 1.0:
            jadwal.append({"Mulai Buka Alur": waktu_mulai.strftime("%d %b %Y, %H:%M"), "Tutup Alur": waktu_selesai.strftime("%d %b %Y, %H:%M"), "Durasi Aman (Jam)": f"{durasi:.1f} Jam"})
    if jadwal:
        st.table(pd.DataFrame(jadwal))
    else:
        st.warning("Jendela aman terlalu sempit (kurang dari 1 jam), manuver dinilai terlalu berisiko.")
