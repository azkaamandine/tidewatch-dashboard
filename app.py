%%writefile app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

# 1. Konfigurasi Halaman
st.set_page_config(page_title="TideWatch - Java Maritime Network", page_icon="⚓", layout="wide", initial_sidebar_state="expanded")

# --- CSS HACK UNTUK TEMA DASHBOARD FUTURISTIK ---
st.markdown("""
    <style>
    .stApp { background-color: #0b141a; }
    
    div[data-testid="metric-container"] {
        background-color: #162432;
        border: 1px solid #1f364d;
        padding: 10px 10px; 
        border-radius: 10px;
    }
    
    div[data-testid="stMetricValue"] > div, [data-testid="stMetricValue"] {
        font-size: 19px !important; 
        white-space: normal !important; 
        overflow: visible !important;
        text-overflow: clip !important;
        word-wrap: break-word !important;
        line-height: 1.2 !important;
        color: #4dc9f6 !important;
    }
    
    [data-testid="stMetricLabel"] { color: #a0b2c6 !important; font-size: 13px !important; }
    
    .status-box-aman { background-color: rgba(63, 185, 80, 0.15); border: 1px solid #3fb950; border-radius: 10px; padding: 20px; text-align: center; color: #3fb950; }
    .status-box-bahaya { background-color: rgba(248, 81, 73, 0.15); border: 1px solid #f85149; border-radius: 10px; padding: 20px; text-align: center; color: #f85149; }
    
    .ekstrem-box { background-color: #111d2e; border: 1px solid #1e334d; padding: 12px; border-radius: 8px; margin-bottom: 10px; }
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
        [data-testid="stSidebar"] { background-color: #050b14 !important; border-right: 2px solid #00CFD5; box-shadow: 5px 0px 20px rgba(0, 207, 213, 0.15); }
        .sidebar-title-container { text-align: center; margin-bottom: 30px; padding-bottom: 15px; border-bottom: 1px solid rgba(0, 207, 213, 0.3); }
        .sidebar-main-title { font-family: 'Orbitron', sans-serif; color: #00CFD5; font-size: 2rem; font-weight: 900; letter-spacing: 3px; text-shadow: 0px 0px 15px rgba(0, 207, 213, 0.6); margin-top: -10px; }
        .sidebar-subtitle { font-family: 'Rajdhani', sans-serif; color: #a0b2c6; font-size: 1rem; text-transform: uppercase; letter-spacing: 2px; }
        .control-panel-box { background: linear-gradient(145deg, #111d2e 0%, #0b141a 100%); border: 1px solid #1f364d; border-left: 4px solid #38bdf8; border-radius: 8px; padding: 15px; margin-bottom: 20px; }
        .control-header { font-family: 'Orbitron', sans-serif; color: #ffffff; font-size: 1.1rem; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px; }
        </style>
        <div class="sidebar-title-container">
            <div style='font-size: 60px; text-shadow: 0 0 20px #00CFD5; margin-bottom: 10px;'>⚓</div>
            <div class="sidebar-main-title">TIDEWATCH</div>
            <div class="sidebar-subtitle">Pusat Komando Navigasi</div>
        </div>
        <div class="control-panel-box">
            <div class="control-header">⚙️ KONTROL PANEL</div>
    """, unsafe_allow_html=True)
    mode_tampilan = st.radio("Rentang Waktu:", ["Harian (24 Jam)", "Bulanan (30 Hari)"])
    st.markdown("<br>", unsafe_allow_html=True)
    tanggal_pilihan = st.date_input("Pilih Tanggal Analisis:", datetime(2025, 1, 15))
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("📡 Telemetry Data: TPXO Global Model & Open-Meteo Weather API Engine")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Rajdhani:wght@500;700&display=swap');
    .title-container { margin-bottom: 25px; padding-bottom: 20px; border-bottom: 1px solid #1f364d; }
    .glow-text { font-family: 'Orbitron', sans-serif; font-size: 4.2rem; font-weight: 900; background: linear-gradient(to right, #00CFD5, #38bdf8, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-transform: uppercase; letter-spacing: 4px; margin-bottom: -5px; text-shadow: 0px 0px 30px rgba(0, 207, 213, 0.4); line-height: 1.1; }
    .sub-glow { font-family: 'Orbitron', sans-serif; font-size: 2rem; color: #ffffff; letter-spacing: 8px; text-transform: uppercase; margin-bottom: 15px; }
    .cyber-caption { font-family: 'Rajdhani', sans-serif; font-size: 1.3rem; color: #a0b2c6; letter-spacing: 2px; border-left: 5px solid #00CFD5; padding-left: 15px; text-transform: uppercase; background: linear-gradient(to right, rgba(0, 207, 213, 0.15), transparent); padding-top: 6px; padding-bottom: 6px; display: inline-block; }
    </style>
    <div class="title-container">
        <div class="glow-text">TIDEWATCH</div>
        <div class="sub-glow">Java Maritime Network</div>
        <div class="cyber-caption">Sistem Pendukung Keputusan Keselamatan Navigasi Terintegrasi Pasut & Vektor Angin</div>
    </div>
""", unsafe_allow_html=True)

row1_col1, row1_col2 = st.columns([3, 1])

with row1_col1:
    st.subheader("🗺️ PETA JARINGAN STASIUN SATELIT")
    df_map = pd.DataFrame([{'Lokasi': k, 'Lat': v['lat'], 'Lon': v['lon']} for k, v in STASIUN_DB.items()])
    # Menggunakan fungsi UPPERCASE agar nama menonjol di satelit tanpa merusak sistem peta Plotly
    df_map['Nama_Pendek'] = df_map['Lokasi'].apply(lambda x: x.split(',')[0].upper())
    df_map['Status'] = df_map['Lokasi'].apply(lambda x: 'Terpilih' if x == st.session_state.lokasi_pilihan else 'Stasiun Lain')
    
    fig_map = px.scatter_mapbox(
        df_map, lat="Lat", lon="Lon", hover_name="Lokasi", color="Status", custom_data=["Lokasi"],
        text="Nama_Pendek", color_discrete_map={'Terpilih': '#00CFD5', 'Stasiun Lain': '#ffffff'},
        zoom=5.8, center={"lat": -7.0, "lon": 110.2}, height=500
    )
    fig_map.update_traces(
        mode='markers+text', textposition='top center', textfont=dict(size=12, color='white'),
        marker=dict(size=9), selector=dict(type='scattermapbox')
    )
    fig_map.update_layout(
        mapbox_style="white-bg",
        mapbox_layers=[{
            "below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri",
            "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"]
        }],
        margin={"r":0,"t":0,"l":0,"b":0}, clickmode='event+select', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
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
    st.subheader("📍 STASIUN AKTIF")
    st.markdown(f"## {lokasi}")
    m_col1, m_col2 = st.columns(2)
    m_col1.metric("MSL (Rata-rata)", f"{msl_val:.2f} m")
    m_col2.metric("HHWL (Maks)", f"{df_display['Prediksi_Pasut'].max():.2f} m")
    m_col3, m_col4 = st.columns(2)
    m_col3.metric("LLWL (Min)", f"{df_display['Prediksi_Pasut'].min():.2f} m")

# ==========================================
# REVISI STRUKTUR: KIRI (METRIK), KANAN (GRAFIK ATAS, RADAR BAWAH)
# ==========================================
st.markdown("---")
st.subheader(f"📊 KONDISI HIDRO-METEOROLOGI HARIAN: {tanggal_pilihan.strftime('%d %B %Y')}")
df_1_hari = df_display.head(144).copy()
df_1_hari['is_pasang'] = (df_1_hari['Prediksi_Pasut'] > df_1_hari['Prediksi_Pasut'].shift(1)) & (df_1_hari['Prediksi_Pasut'] > df_1_hari['Prediksi_Pasut'].shift(-1))
df_1_hari['is_surut'] = (df_1_hari['Prediksi_Pasut'] < df_1_hari['Prediksi_Pasut'].shift(1)) & (df_1_hari['Prediksi_Pasut'] < df_1_hari['Prediksi_Pasut'].shift(-1))
df_ekstrem = df_1_hari[df_1_hari['is_pasang'] | df_1_hari['is_surut']].copy()
df_ekstrem['Tipe'] = np.where(df_ekstrem['is_pasang'], 'Pasang', 'Surut')

harian_col1, harian_col2 = st.columns([1, 2.5])

with harian_col1:
    st.markdown(f"""
    <div class="ekstrem-box" style="border-left: 5px solid #4dc9f6;">
        <span style='color:#4dc9f6; font-size:15px;'>🌊 <b>TINGGI GELOMBANG (Hs)</b></span><br>
        <span style='font-size:26px; color:#fff;'>{max_wave_hs:.2f} m</span><br>
        <span style='font-size:13px; color:#a0b2c6;'>Amplitudo: ±{amp_gelombang:.2f} m</span>
    </div>
    <div class="ekstrem-box" style="border-left: 5px solid #00CFD5;">
        <span style='color:#00CFD5; font-size:15px;'>🍃 <b>VEKTOR ANGIN PERMUKAAN</b></span><br>
        <span style='font-size:26px; color:#fff;'>{current_wind_speed:.1f} Knot</span><br>
        <span style='font-size:13px; color:#a0b2c6;'>Arah Datang: {current_wind_dir}°</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Mengembalikan jam puncak pasut astronomis yang tersembunyi
    if not df_ekstrem.empty:
        for idx, row in df_ekstrem.iterrows():
            color = "#3fb950" if row['Tipe'] == 'Pasang' else "#f85149"
            simbol = "🟢" if row['Tipe'] == 'Pasang' else "🔴"
            st.markdown(f"""
            <div class="ekstrem-box">
                <span style='color:{color}; font-size:14px;'>{simbol} <b>PUNCAK {row['Tipe'].upper()}</b></span><br>
                <span style='font-size:22px; color:#fff;'>{row['Prediksi_Pasut']:.2f} m</span> 
                <span style='color:#a0b2c6; font-size:13px;'>pukul {row['Time'].strftime('%H:%M')}</span>
            </div>
            """, unsafe_allow_html=True)

with harian_col2:
    # Grafik Pasut ditinggikan menjadi 350px agar sangat lega dibaca
    fig_harian = go.Figure()
    fig_harian.add_trace(go.Scatter(x=df_1_hari['Time'], y=df_1_hari['Prediksi_Pasut'] + amp_gelombang, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
    fig_harian.add_trace(go.Scatter(x=df_1_hari['Time'], y=df_1_hari['Prediksi_Pasut'] - amp_gelombang, mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(255, 255, 255, 0.1)', name='Wave Envelope'))
    fig_harian.add_trace(go.Scatter(x=df_1_hari['Time'], y=df_1_hari['Prediksi_Pasut'], mode='lines', name='Elevasi Pasut (m)', line=dict(color='#38bdf8', width=3)))
    
    df_pasang = df_1_hari[df_1_hari['is_pasang']]
    fig_harian.add_trace(go.Scatter(x=df_pasang['Time'], y=df_pasang['Prediksi_Pasut'], mode='markers+text', name='Pasang', marker=dict(color='#3fb950', size=10), text=[f"{v:.2f} m" for v in df_pasang['Prediksi_Pasut']], textposition="top center"))
    df_surut = df_1_hari[df_1_hari['is_surut']]
    fig_harian.add_trace(go.Scatter(x=df_surut['Time'], y=df_surut['Prediksi_Pasut'], mode='markers+text', name='Surut', marker=dict(color='#f85149', size=10), text=[f"{v:.2f} m" for v in df_surut['Prediksi_Pasut']], textposition="bottom center"))

    fig_harian.update_layout(
        height=350, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        title=dict(text="🌊 GRAFIK ELEVASI MUKA AIR AKTUAL (PASUT + GELOMBANG)", font=dict(color="#38bdf8", size=14)),
        xaxis=dict(showgrid=False, tickformat="%H:%M", tickfont=dict(color="#a0b2c6")), yaxis=dict(gridcolor="#1e334d", tickfont=dict(color="#a0b2c6")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_harian, use_container_width=True, config={'displayModeBar': False})

    st.markdown("<br>", unsafe_allow_html=True)

    # Radar Angin disusun di bawah kurva pasut agar proporsional
    r_col1, r_col2, r_col3 = st.columns([1, 1.5, 1])
    with r_col2:
        fig_wind = go.Figure()
        fig_wind.add_trace(go.Scatterpolar(r=[0, current_wind_speed], theta=[0, current_wind_dir], mode='lines+markers', line=dict(color='#00CFD5', width=4), marker=dict(size=[0, 15], symbol='triangle-up', color='#00CFD5')))
        fig_wind.update_layout(
            polar=dict(
              radialaxis=dict(showticklabels=True, gridcolor="#1f364d", tickfont=dict(size=9, color="#a0b2c6")),
              angularaxis=dict(thetaunit="degrees", rotation=90, direction="clockwise", gridcolor="#1f364d", tickfont=dict(color="#fff", size=11))
            ),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=280, margin=dict(l=20, r=20, t=35, b=20), showlegend=False,
            title=dict(text="🌀 Radar Arah Embusan Angin", font=dict(color="#00CFD5", size=10), x=0.5)
        )
        st.plotly_chart(fig_wind, use_container_width=True, config={'displayModeBar': False})

st.markdown("---")
row2_col1, row2_col2 = st.columns([3, 1])
with row2_col2:
    st.subheader("⚙️ PARAMETER KAPAL")
    draft = st.number_input("Draft Kapal (m):", 1.0, 20.0, 8.5)
    ukc = st.number_input("UKC (m):", 0.0, 5.0, 1.0)
    ambang_keamanan = draft + ukc
    df_display['Total_Kedalaman'] = batimetri_peta + df_display['Prediksi_Pasut']
    kondisi_min_aktual = df_display['Total_Kedalaman'].min() - amp_gelombang
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🛡️ STATUS KESELAMATAN")
    
    if kondisi_min_aktual < ambang_keamanan:
        st.markdown(f'<div class="status-box-bahaya"><h2>🔴 BAHAYA: KANDAS</h2><p>Kedalaman aktual terendah ({kondisi_min_aktual:.2f} m) melanggar batas UKC.</p></div>', unsafe_allow_html=True)
    elif current_wind_speed > 20.0:
        st.markdown(f'<div class="status-box-bahaya"><h2>🔴 BAHAYA: ANGIN</h2><p>Kecepatan Angin ({current_wind_speed:.1f} knot) berbahaya bagi manuver lunas dan lambung lateral kapal.</p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-box-aman"><h2>✅ AMAN OPERASIONAL</h2><p>Kondisi dinamis laut aman untuk manuver.</p></div>', unsafe_allow_html=True)

with row2_col1:
    st.subheader("📉 SIMULASI KEDALAMAN AKTUAL (PASUT + GELOMBANG)")
    fig_depth = go.Figure()
    fig_depth.add_trace(go.Scatter(x=df_display['Time'], y=df_display['Total_Kedalaman'] + amp_gelombang, mode='lines', line=dict(width=0), showlegend=False))
    fig_depth.add_trace(go.Scatter(x=df_display['Time'], y=df_display['Total_Kedalaman'] - amp_gelombang, mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(255, 255, 255, 0.1)', name='Wave Envelope'))
    fig_depth.add_trace(go.Scatter(x=df_display['Time'], y=df_display['Total_Kedalaman'], mode='lines', name='Kedalaman Pasut', line=dict(color='#00CFD5', width=3)))
    fig_depth.add_hline(y=ambang_keamanan, line_dash="dash", line_color="#f85149", annotation_text="Batas Draft + UKC")
    fig_depth.update_layout(xaxis_title="Waktu", yaxis_title="Kedalaman (m)", height=450, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#a0b2c6"), xaxis=dict(gridcolor="#1f364d"), yaxis=dict(gridcolor="#1f364d"))
    st.plotly_chart(fig_depth, use_container_width=True)

# --- ROW 3: JENDELA WAKTU AMAN (SUDAH DIKEMBALIKAN KE TEMPAT SEMESTINYA) ---
st.markdown("---")
st.subheader("🕒 Jendela Waktu Aman Navigasi Alur Pelabuhan")
df_display['is_safe'] = (df_display['Total_Kedalaman'] - amp_gelombang) >= ambang_keamanan

if current_wind_speed > 20.0:
    st.error(f"🚫 JENDELA NAVIGASI DITUTUP TOTAL: Kecepatan angin saat ini terpantau {current_wind_speed:.1f} knot di atas ambang batas aman (20 knot). Risiko penyimpangan koordinat lunas dinamis sangat tinggi akibat gaya dorong angin lateral.")
elif max_wave_hs > 1.5:
    st.error("🚫 Jendela navigasi ditutup akibat hantaman gelombang tinggi ekstrem di pelabuhan.")
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
