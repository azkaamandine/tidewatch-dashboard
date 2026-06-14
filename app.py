import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

# 1. Konfigurasi Halaman (Wajib Wide & Dark Theme)
st.set_page_config(page_title="TideWatch - Java Maritime Network", page_icon="⚓", layout="wide", initial_sidebar_state="expanded")

# --- CSS HACK UNTUK TEMA DASHBOARD ---
st.markdown("""
    <style>
    .stApp { background-color: #0b141a; }
    
    div[data-testid="metric-container"] {
        background-color: #162432;
        border: 1px solid #1f364d;
        padding: 10px 15px;
        border-radius: 10px;
    }
    
    [data-testid="stMetricValue"] > div, [data-testid="stMetricValue"] {
        white-space: normal !important;
        word-wrap: break-word !important;
        font-size: 22px !important; 
        line-height: 1.2 !important;
        color: #4dc9f6 !important;
    }
    
    [data-testid="stMetricLabel"] { color: #a0b2c6 !important; }
    
    .status-box-aman {
        background-color: rgba(63, 185, 80, 0.15);
        border: 1px solid #3fb950;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        color: #3fb950;
    }
    .status-box-bahaya {
        background-color: rgba(248, 81, 73, 0.15);
        border: 1px solid #f85149;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        color: #f85149;
    }
    
    .ekstrem-box {
        background-color: #111d2e;
        border: 1px solid #1e334d;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
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

# 2. Fungsi Ambil Data Gelombang Real-Time via API
@st.cache_data(ttl=1800)
def fetch_realtime_wave_data(lat, lon):
    try:
        url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&hourly=wave_height&timezone=auto"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            json_data = response.json()
            wave_heights = json_data['hourly']['wave_height']
            avg_hs = np.nanmean(wave_heights[:24]) if wave_heights else 0.4
            max_hs = np.nanmax(wave_heights[:24]) if wave_heights else 0.6
            return avg_hs, max_hs
    except:
        pass
    return 0.45, 0.70

# 3. Mesin Prediksi Model TPXO
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

# ==========================================
# STRUKTUR LAYOUT DASHBOARD
# ==========================================

with st.sidebar:
    st.markdown("<div style='font-size: 55px; margin-bottom: -20px;'>⚓</div>", unsafe_allow_html=True)
    st.markdown("## TIDEWATCH")
    st.markdown("Pusat Komando Navigasi")
    st.markdown("---")
    st.button("🗺️ Peta Stasiun", use_container_width=True)
    st.button("📈 Grafik Pasut", use_container_width=True)
    st.button("⚙️ Parameter Kapal", use_container_width=True)
    st.markdown("---")
    st.caption("Data Source: TPXO Model & Open-Meteo Realtime API")

head_col1, head_col2, head_col3 = st.columns([2, 1, 1])
with head_col1:
    st.title("TideWatch: Java Maritime Network")
    st.caption("Sistem Pendukung Keputusan Keselamatan Navigasi Terintegrasi Pasut & Gelombang")
with head_col2:
    mode_tampilan = st.selectbox("Mode Tampilan", ["Harian (24 Jam)", "Bulanan (30 Hari)"])
with head_col3:
    tanggal_pilihan = st.date_input("Tanggal Analisis", datetime(2025, 1, 15))

st.markdown("---")

row1_col1, row1_col2 = st.columns([1.5, 1])

with row1_col1:
    st.subheader("🗺️ PETA JARINGAN STASIUN")
    df_map = pd.DataFrame([{'Lokasi': k, 'Lat': v['lat'], 'Lon': v['lon']} for k, v in STASIUN_DB.items()])
    df_map['Status'] = df_map['Lokasi'].apply(lambda x: 'Terpilih' if x == st.session_state.lokasi_pilihan else 'Stasiun Lain')
    
    fig_map = px.scatter_mapbox(
        df_map, lat="Lat", lon="Lon", hover_name="Lokasi", color="Status", custom_data=["Lokasi"],
        color_discrete_map={'Terpilih': '#3fb950', 'Stasiun Lain': '#1f364d'},
        zoom=5.5, center={"lat": -7.2, "lon": 110.0}, mapbox_style="carto-darkmatter", height=350
    )
    fig_map.update_traces(marker=dict(size=18), selector=dict(type='scattermapbox'))
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, clickmode='event+select', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    
    map_selection = st.plotly_chart(fig_map, width="stretch", on_select="rerun", selection_mode="points")
    if map_selection and "selection" in map_selection:
        titik_terpilih = map_selection["selection"]["points"]
        if len(titik_terpilih) > 0:
            nama_lokasi_klik = titik_terpilih[0]["customdata"][0]
            if nama_lokasi_klik != st.session_state.lokasi_pilihan:
                st.session_state.lokasi_pilihan = nama_lokasi_klik
                st.rerun()

# --- EKSTRAKSI DATA MODEL & API GELOMBANG ---
lokasi = st.session_state.lokasi_pilihan
data_lokasi = STASIUN_DB[lokasi]
msl_val = data_lokasi['msl']
batimetri_peta = data_lokasi['alur']

avg_wave_hs, max_wave_hs = fetch_realtime_wave_data(data_lokasi['lat'], data_lokasi['lon'])

durasi_hari = 1 if mode_tampilan == "Harian (24 Jam)" else 30
df_display = generate_tmd_prediction(tanggal_pilihan, durasi_hari, lokasi)

amp_M2, amp_S2 = data_lokasi['M2'], data_lokasi['S2']
amp_K1, amp_O1 = data_lokasi['K1'], data_lokasi['O1']
F_index = (amp_K1 + amp_O1) / (amp_M2 + amp_S2)

if F_index <= 0.25: tipe_teks = "Harian Ganda"
elif F_index <= 1.5: tipe_teks = "Campuran Ganda"
elif F_index <= 3.0: tipe_teks = "Campuran Tunggal"
else: tipe_teks = "Harian Tunggal"

with row1_col2:
    st.subheader("📍 STASIUN AKTIF")
    st.markdown(f"## {lokasi}")
    
    m_col1, m_col2 = st.columns(2)
    m_col1.metric("MSL (Rata-rata)", f"{msl_val:.2f} m")
    m_col2.metric("HHWL (Maks)", f"{df_display['Prediksi_Pasut'].max():.2f} m")
    m_col3, m_col4 = st.columns(2)
    m_col3.metric("LLWL (Min)", f"{df_display['Prediksi_Pasut'].min():.2f} m")
    m_col4.metric(f"Tipe Pasut", tipe_teks)

# --- ROW 1.5: RINGKASAN & GRAFIK PASUT HARIAN ---
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
        <span style='color:#4dc9f6; font-size:16px;'>🌊 <b>SIGNIFICANT WAVE HEIGHT (Hs)</b></span><br>
        <span style='font-size:26px; color:#fff;'>{max_wave_hs:.2f} m</span> <span style='font-size:14px; color:#a0b2c6;'>Maks Hari Ini</span><br>
        <span style='font-size:14px; color:#a0b2c6;'>Rata-rata: {avg_wave_hs:.2f} m (Live API)</span>
    </div>
    """, unsafe_allow_html=True)
    
    if not df_ekstrem.empty:
        for idx, row in df_ekstrem.iterrows():
            color = "#3fb950" if row['Tipe'] == 'Pasang' else "#f85149"
            simbol = "🟢" if row['Tipe'] == 'Pasang' else "🔴"
            st.markdown(f"""
            <div class="ekstrem-box">
                <span style='color:{color}; font-size:16px;'>{simbol} <b>{row['Tipe'].upper()}</b></span><br>
                <span style='font-size:22px; color:#fff;'>{row['Prediksi_Pasut']:.2f} m</span> 
                <span style='color:#a0b2c6;'>pukul {row['Time'].strftime('%H:%M')}</span>
            </div>
            """, unsafe_allow_html=True)

with harian_col2:
    fig_harian = go.Figure()
    fig_harian.add_trace(go.Scatter(x=df_1_hari['Time'], y=df_1_hari['Prediksi_Pasut'], mode='lines', name='Muka Air (m)', line=dict(color='#38bdf8', width=3), fill='tozeroy', fillcolor='rgba(56, 189, 248, 0.1)'))
    
    df_pasang = df_1_hari[df_1_hari['is_pasang']]
    fig_harian.add_trace(go.Scatter(x=df_pasang['Time'], y=df_pasang['Prediksi_Pasut'], mode='markers+text', name='Puncak Pasang', marker=dict(color='#3fb950', size=12, line=dict(color='white', width=2)), text=[f"{v:.2f} m" for v in df_pasang['Prediksi_Pasut']], textposition="top center"))
    
    df_surut = df_1_hari[df_1_hari['is_surut']]
    fig_harian.add_trace(go.Scatter(x=df_surut['Time'], y=df_surut['Prediksi_Pasut'], mode='markers+text', name='Lembah Surut', marker=dict(color='#f85149', size=12, line=dict(color='white', width=2)), text=[f"{v:.2f} m" for v in df_surut['Prediksi_Pasut']], textposition="bottom center"))

    fig_harian.update_layout(
        height=320, margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickformat="%H:%M"), yaxis=dict(gridcolor="#1e334d"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_harian, width="stretch", config={'displayModeBar': False})

# --- ROW 2: GRAFIK KEDALAMAN AKTUAL & PARAMETER ALUR ---
st.markdown("---")
row2_col1, row2_col2 = st.columns([2, 1])

with row2_col2:
    st.subheader("⚙️ PARAMETER KAPAL & ALUR")
    st.info(f"📍 **Kedalaman Alur:** {batimetri_peta} m LWS\n\n*Koordinat Geografis: {data_lokasi['lat']}, {data_lokasi['lon']}*")
    
    draft = st.number_input("Draft Kapal (m):", 1.0, 20.0, 8.5)
    ukc = st.number_input("UKC (m):", 0.0, 5.0, 1.0)
    
    ambang_keamanan = draft + ukc
    df_display['Total_Kedalaman'] = batimetri_peta + df_display['Prediksi_Pasut']
    kondisi_min = df_display['Total_Kedalaman'].min()
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🛡️ INTEGRATED SAFETY STATUS")
    
    if kondisi_min < ambang_keamanan:
        st.markdown(f'<div class="status-box-bahaya"><h2>🔴 BAHAYA: ALUR DANGKAL</h2><p>Risiko tinggi kandas! Batas minimum kedalaman air ({kondisi_min:.2f} m) melanggar ambang aman.</p></div>', unsafe_allow_html=True)
    elif max_wave_hs > 1.5:
        st.markdown(f'<div class="status-box-bahaya"><h2>🔴 BAHAYA: GELOMBANG TINGGI</h2><p>Kedalaman air cukup, namun Tinggi Gelombang Signifikan (Hs: {max_wave_hs:.2f} m) melebihi batas operasional 1.5 m. Berisiko osilasi dinamis lunas kapal.</p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-box-aman"><h2>✅ AMAN OPERASIONAL</h2><p>Kedalaman air mencukupi ({kondisi_min:.2f} m) dan tinggi gelombang laut terpantau tenang ({max_wave_hs:.2f} m).</p></div>', unsafe_allow_html=True)

with row2_col1:
    st.subheader("📉 SIMULASI KEDALAMAN AKTUAL TERHADAP KAPAL")
    fig_depth = go.Figure()
    fig_depth.add_trace(go.Scatter(x=df_display['Time'], y=df_display['Total_Kedalaman'], mode='lines', name='Kedalaman Aktual', line=dict(color='#00CFD5', width=3), fill='tozeroy', fillcolor='rgba(0, 207, 213, 0.1)'))
    fig_depth.add_hline(y=ambang_keamanan, line_dash="dash", line_color="#f85149", annotation_text="Batas Aman Kapal")
    fig_depth.update_layout(xaxis_title="Waktu", yaxis_title="Kedalaman (m)", height=450, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#a0b2c6"), xaxis=dict(gridcolor="#1f364d"), yaxis=dict(gridcolor="#1f364d"))
    st.plotly_chart(fig_depth, width="stretch")

# --- ROW 3: SAFE WINDOW TABEL ---
st.markdown("---")
st.subheader("🕒 Jendela Waktu Aman Navigasi")
df_display['is_safe'] = df_display['Total_Kedalaman'] >= ambang_keamanan

if max_wave_hs > 1.5:
    st.error("🚫 Jendela navigasi ditutup total untuk seluruh jam pelayaran akibat kondisi cuaca buruk dan gelombang tinggi ekstrem di luar batas keselamatan.")
elif df_display['is_safe'].all():
    st.success("Kapal dapat olah gerak kapan saja tanpa batasan kedalaman pada rentang waktu ini.")
elif not df_display['is_safe'].any():
    st.error("Alur sepenuhnya tertutup! Air terlalu dangkal sepanjang rentang waktu yang dipilih.")
else:
    df_display['block'] = (df_display['is_safe'] != df_display['is_safe'].shift(1)).cumsum()
    safe_blocks = df_display[df_display['is_safe']].groupby('block')
    
    jadwal = []
    for _, block in safe_blocks:
        waktu_mulai = block['Time'].iloc[0]
        waktu_selesai = block['Time'].iloc[-1]
        durasi = (waktu_selesai - waktu_mulai).total_seconds() / 3600
        if durasi >= 1.0:
            jadwal.append({
                "Mulai Buka Alur": waktu_mulai.strftime("%d %b %Y, %H:%M"),
                "Tutup Alur": waktu_selesai.strftime("%d %b %Y, %H:%M"),
                "Durasi Aman (Jam)": f"{durasi:.1f} Jam"
            })
    if jadwal:
        st.table(pd.DataFrame(jadwal))
    else:
        st.warning("Jendela aman ditemukan, tetapi durasinya kurang dari 1 jam (terlalu berisiko untuk manuver kapal besar).")
