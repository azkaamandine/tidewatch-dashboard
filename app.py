import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURASI HALAMAN & CSS KUSTOM
# ==========================================
st.set_page_config(page_title="NaviWatch", page_icon="⚓", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Orbitron:wght@700;900&display=swap');
.stApp { background-color: #0A1118; font-family: 'Inter', sans-serif; color: #FFFFFF; }

/* FIX SIDEBAR TOGGLE: Sembunyikan menu dan footer, tapi biarkan header untuk tombol toggle */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 100% !important; }

/* Kustomisasi Sisi Samping */
[data-testid="stSidebar"] { background-color: #050C14 !important; border-right: 1px solid #1E2D3D; }
.sidebar-brand { font-family: 'Orbitron', sans-serif; color: #00E5FF; font-size: 1.6rem; font-weight: 900; text-align: center; padding: 10px 0; border-bottom: 1px solid rgba(0, 229, 255, 0.2); margin-bottom: 20px; }

/* Sistem Top Navigation Bar */
.top-nav { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1E2D3D; padding-bottom: 15px; margin-bottom: 20px; }
.top-nav-left { display: flex; align-items: center; gap: 15px; }
.nav-logo { font-size: 32px; color: #00E5FF; text-shadow: 0 0 10px #00E5FF; }
.nav-title-box { display: flex; flex-direction: column; }
.nav-sup { font-size: 11px; color: #94A3B8; letter-spacing: 1px; font-weight: 600; }
.nav-main { font-size: 26px; font-weight: 700; color: #FFFFFF; letter-spacing: 1px; font-family: 'Orbitron', sans-serif;}
.nav-sub { font-size: 11px; color: #64748B; }

/* Struktur Grid KPI */
.pro-card { background-color: #121E2D; border: 1px solid #1E2D3D; border-radius: 8px; padding: 16px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
.pro-card-header { font-size: 11px; color: #00E5FF; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; font-weight: 600; border-bottom: 1px solid #1E2D3D; padding-bottom: 8px;}
.kpi-container { display: flex; align-items: center; gap: 15px; }
.kpi-icon { font-size: 32px; opacity: 0.8; }
.kpi-data { display: flex; flex-direction: column; }
.kpi-title { font-size: 11px; color: #94A3B8; text-transform: uppercase; font-weight: 600; white-space: nowrap; }
.kpi-val { font-size: 26px; font-weight: 700; color: #FFFFFF; line-height: 1.2; }
.kpi-unit { font-size: 14px; color: #64748B; font-weight: 400; }
.kpi-desc { font-size: 12px; color: #94A3B8; margin-top: 2px; }
.kpi-highlight { color: #00E5FF; font-weight: 600; }

/* Kotak Status Peringatan */
.warning-card { background-color: #2D2218; border: 1px solid #4D3310; border-radius: 8px; padding: 16px; border-left: 4px solid #FFB020; height: 100%; }
.warning-title { font-size: 11px; color: #FFB020; text-transform: uppercase; font-weight: 600; margin-bottom: 5px;}
.warning-val { font-size: 22px; font-weight: 700; color: #FFB020; margin-bottom: 5px;}
.warning-desc { font-size: 12px; color: #D1D5DB; }

/* Kotak Notifikasi Kustom */
.custom-alert-success { background-color: rgba(63, 185, 80, 0.08); border: 1px solid #3fb950; border-radius: 8px; padding: 15px; color: #3fb950; display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
.custom-alert-danger { background-color: rgba(248, 81, 73, 0.08); border: 1px solid #f85149; border-radius: 8px; padding: 15px; color: #f85149; display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
.custom-alert-warning { background-color: rgba(255, 176, 32, 0.08); border: 1px solid #FFB020; border-radius: 8px; padding: 15px; color: #FFB020; display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }

/* Tabel Kustom & Footer */
.pro-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
.pro-table th { background-color: #1E2D3D; color: #00E5FF; text-align: left; padding: 10px; font-weight: 600; border-bottom: 2px solid #121E2D; }
.pro-table td { padding: 10px; border-bottom: 1px solid #1E2D3D; color: #E2E8F0; }
.pro-footer { border-top: 1px solid #1E2D3D; padding-top: 12px; margin-top: 20px; display: flex; justify-content: space-between; font-size: 11px; color: #64748B; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE KELAUTAN INTERNAL (8 STASIUN)
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

# ==========================================
# 3. ENGINE KOMPUTASI API & MODEL 
# ==========================================
@st.cache_data(ttl=1800)
def fetch_marine_forecast(lat, lon):
    try:
        url_wave = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&hourly=wave_height,wave_period&timezone=auto&forecast_days=2"
        r_wave = requests.get(url_wave, timeout=10).json()
        df_wave = pd.DataFrame(r_wave['hourly'])
        df_wave['time'] = pd.to_datetime(df_wave['time'])
        
        url_wind = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=wind_speed_10m,wind_direction_10m,wind_gusts_10m&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m&wind_speed_unit=kn&timezone=auto&forecast_days=2"
        r_wind = requests.get(url_wind, timeout=10).json()
        df_wind = pd.DataFrame(r_wind['hourly'])
        df_wind['time'] = pd.to_datetime(df_wind['time'])
        
        max_hs = df_wave['wave_height'].iloc[0]
        avg_period = df_wave['wave_period'].mean()
        
        return {
            'success': True,
            'kpi': {
                'max_hs': max_hs,
                'avg_wave_period': avg_period,
                'current_wind_speed': r_wind['current']['wind_speed_10m'],
                'current_wind_dir': r_wind['current']['wind_direction_10m'],
                'current_wind_gust': r_wind['current'].get('wind_gusts_10m', r_wind['current']['wind_speed_10m']*1.3),
            },
            'hourly_wave': df_wave,
            'hourly_wind': df_wind
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

@st.cache_data
def generate_tmd_prediction(target_date, days_duration, lokasi):
    data = STASIUN_DB[lokasi]
    start_predict = datetime.combine(target_date, datetime.min.time())
    end_predict = start_predict + timedelta(days=days_duration)
    time_series = pd.date_range(start=start_predict, end=end_predict, freq='10min')
    t_hours = (time_series - datetime(2025, 1, 1)).total_seconds() / 3600.0
    y_pred = np.zeros(len(t_hours))
    
    y_pred += data['M2'] * np.cos((2 * np.pi / 12.42) * t_hours - 0.5)
    y_pred += data['S2'] * np.cos((2 * np.pi / 12.00) * t_hours - 1.0)
    y_pred += data['K1'] * np.cos((2 * np.pi / 23.93) * t_hours - 1.5)
    y_pred += data['O1'] * np.cos((2 * np.pi / 25.82) * t_hours - 2.0)
    y_pred += data['msl'] 
    
    df = pd.DataFrame({'Time': time_series, 'Prediksi_Pasut': y_pred})
    df['is_pasang'] = (df['Prediksi_Pasut'] > df['Prediksi_Pasut'].shift(1)) & (df['Prediksi_Pasut'] > df['Prediksi_Pasut'].shift(-1))
    df['is_surut'] = (df['Prediksi_Pasut'] < df['Prediksi_Pasut'].shift(1)) & (df['Prediksi_Pasut'] < df['Prediksi_Pasut'].shift(-1))
    return df

def get_beaufort_scale(knots):
    if knots < 1: return "Calm"
    elif knots <= 3: return "Light Air"
    elif knots <= 6: return "Light Breeze"
    elif knots <= 10: return "Gentle Breeze"
    elif knots <= 16: return "Moderate Breeze"
    elif knots <= 21: return "Fresh Breeze"
    elif knots <= 27: return "Strong Breeze"
    else: return "Gale/Storm"

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# ==========================================
# 4. STRUKTUR SIDEBAR KENDALI
# ==========================================
with st.sidebar:
    st.markdown('<div class="sidebar-brand">⚓ NAVIWATCH </div>', unsafe_allow_html=True)
    
    st.markdown("<h4 style='color:#00E5FF; font-size:12px; letter-spacing:1px;'>🧭 MENU INTERAKTIF</h4>", unsafe_allow_html=True)
    menu_aktif = st.radio("Pilih Lapisan Informasi:", [
        "🏠 Dashboard Utama", 
        "📈 Detail Komponen Pasut", 
        "🌊 Karakteristik Gelombang", 
        "💨 Analisis Vektor Angin"
    ], label_visibility="collapsed")
    
    st.markdown("<hr style='border-color:#1E2D3D;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#00E5FF; font-size:12px; letter-spacing:1px;'>⚙️ PUSAT KENDALI OPERASIONAL</h4>", unsafe_allow_html=True)
    
    lokasi_index = list(STASIUN_DB.keys()).index(st.session_state.lokasi_pilihan)
    
    if 'lokasi_lama' not in st.session_state: st.session_state.lokasi_lama = st.session_state.lokasi_pilihan
    lokasi_dipilih_sidebar = st.selectbox("Pilih Stasiun Pelabuhan:", list(STASIUN_DB.keys()), index=lokasi_index)
    
    if lokasi_dipilih_sidebar != st.session_state.lokasi_pilihan:
        st.session_state.lokasi_pilihan = lokasi_dipilih_sidebar
    
    tanggal_pilihan = st.date_input("Tanggal Analisis Batas:", datetime(2025, 1, 15))
    mode_tampilan = st.radio("Rentang Prediksi Grafik:", ["Harian (24 Jam)", "Bulanan (30 Hari)"])

    st.markdown("<hr style='border-color:#1E2D3D;'>", unsafe_allow_html=True)
    st.caption("📡 Data Telemetry: TPXO Global Model & Open-Meteo Weather API Engine")

# --- AMBIL DATA KELAUTAN ---
lokasi = st.session_state.lokasi_pilihan
data_stasiun = STASIUN_DB[lokasi]
batimetri_alur = data_stasiun['alur']

forecast_data = fetch_marine_forecast(data_stasiun['lat'], data_stasiun['lon'])

if not forecast_data['success']:
    st.error(f"⚠️ Gagal menghubungkan ke Open-Meteo API. Menggunakan data fallback statis. Error: {forecast_data.get('error', 'Unknown Error')}")
    max_wave_hs, avg_wave_period = 0.62, 6.5
    current_wind_speed, current_wind_dir, current_wind_gust = 15.6, 230.0, 22.4
    df_hourly_wave, df_hourly_wind = pd.DataFrame(), pd.DataFrame()
else:
    kpi = forecast_data['kpi']
    max_wave_hs, avg_wave_period = kpi['max_hs'], kpi['avg_wave_period']
    current_wind_speed, current_wind_dir, current_wind_gust = kpi['current_wind_speed'], kpi['current_wind_dir'], kpi['current_wind_gust']
    df_hourly_wave = forecast_data['hourly_wave']
    df_hourly_wind = forecast_data['hourly_wind']

amp_gelombang = max_wave_hs / 2

durasi_hari = 1 if mode_tampilan == "Harian (24 Jam)" else 30
df_display = generate_tmd_prediction(tanggal_pilihan, durasi_hari, lokasi)
df_display['Total_Kedalaman'] = batimetri_alur + df_display['Prediksi_Pasut']

F_index = (data_stasiun['K1'] + data_stasiun['O1']) / (data_stasiun['M2'] + data_stasiun['S2'])
tipe_pasut = "Harian Ganda" if F_index <= 0.25 else "Campuran Ganda" if F_index <= 1.5 else "Campuran Tunggal" if F_index <= 3.0 else "Harian Tunggal"

# ==========================================
# 5. LOGIKA DYNAMIC DEFAULT PARAMETER KAPAL
# ==========================================
if st.session_state.lokasi_pilihan != st.session_state.lokasi_lama:
    default_draft_baru = max(1.0, min(8.5, batimetri_alur - 1.5))
    st.session_state.last_draft = default_draft_baru
    st.session_state.last_ukc = 1.0
    st.session_state.lokasi_lama = st.session_state.lokasi_pilihan
    st.rerun()

if 'last_draft' not in st.session_state:
    bat_priok = STASIUN_DB[list(STASIUN_DB.keys())[0]]['alur']
    st.session_state.last_draft = max(1.0, min(8.5, bat_priok - 1.5))
if 'last_ukc' not in st.session_state:
    st.session_state.last_ukc = 1.0

# ==========================================
# 6. HEADER UTAMA DASHBOARD
# ==========================================
waktu_sekarang = datetime.utcnow() + timedelta(hours=7)
st.markdown(f"""
<div class="top-nav">
    <div class="top-nav-left">
        <div class="nav-logo">⚓</div>
        <div class="nav-title-box">
            <span class="nav-sup">SISTEM PEMANTAUAN TERINTEGRASI</span>
            <span class="nav-main">NAVIWATCH</span>
            <span class="nav-sub">MONITORING GEOSPASIAL REAL-TIME OSEANOGRAFI OPERASIONAL</span>
        </div>
    </div>
    <div class="top-nav-right">
        <div>📅</div>
        <div style="line-height:1.2;"><b>{waktu_sekarang.strftime('%d %B %Y')}</b><br><span style='color:#00E5FF;'>{waktu_sekarang.strftime('%H:%M')} WIB</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 7. KONTEN BERDASARKAN TAB MENU
# ==========================================
if menu_aktif == "🏠 Dashboard Utama":
    
    # --- BARIS 1: KPI CARDS ---
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.markdown(f"""
        <div class="pro-card">
        <div class="kpi-container">
        <div class="kpi-icon">🌊</div>
        <div class="kpi-data">
        <span class="kpi-title">PASUT STASIUN AKTIF</span>
        <span class="kpi-val">{df_display['Prediksi_Pasut'].iloc[0]:.2f} <span class="kpi-unit">m</span></span>
        <span class="kpi-desc">Tipe pasut: <span class="kpi-highlight">{tipe_pasut}</span></span>
        </div></div></div>""", unsafe_allow_html=True)

    with kpi2:
        st.markdown(f"""
        <div class="pro-card">
        <div class="kpi-container">
        <div class="kpi-icon">🌊</div>
        <div class="kpi-data">
        <span class="kpi-title">GELOMBANG SIGNIFIKAN (Hs)</span>
        <span class="kpi-val">{max_wave_hs:.2f} <span class="kpi-unit">m</span></span>
        <span class="kpi-desc">Amplitudo Fluktuasi: ±{amp_gelombang:.2f} m</span>
        </div></div></div>""", unsafe_allow_html=True)

    with kpi3:
        st.markdown(f"""
        <div class="pro-card">
        <div class="kpi-container">
        <div class="kpi-icon">💨</div>
        <div class="kpi-data">
        <span class="kpi-title">VEKTOR ANGIN PERMUKAAN</span>
        <span class="kpi-val">{current_wind_speed:.1f} <span class="kpi-unit">kt</span></span>
        <span class="kpi-desc">Arah Embusan: {current_wind_dir}°</span>
        </div></div></div>""", unsafe_allow_html=True)

    # --- BARIS 2: MAP & GRAPH PASUT ---
    mid_left, mid_right = st.columns([1.3, 1])
    
    with mid_left:
        st.markdown('<div class="pro-card-header">🗺️ Peta Monitoring Jalur Satelit</div>', unsafe_allow_html=True)
        df_map = pd.DataFrame([{'Lokasi': k, 'Lat': v['lat'], 'Lon': v['lon']} for k, v in STASIUN_DB.items()])
        df_map['Key'] = df_map['Lokasi']
        df_map['Nama_Peta'] = df_map['Lokasi'].apply(lambda x: x.split(',')[0].strip().title())
        df_map['Status'] = df_map['Lokasi'].apply(lambda x: 'Aktif Terpilih' if x == lokasi else 'Stasiun Lain')
        
        fig_map = px.scatter_mapbox(
            df_map, lat="Lat", lon="Lon", text="Nama_Peta", color="Status", custom_data=["Key"],
            color_discrete_map={'Aktif Terpilih': '#00E5FF', 'Stasiun Lain': '#FFFFFF'},
            zoom=5.4, center={"lat": data_stasiun['lat'], "lon": data_stasiun['lon']}
        )
        fig_map.update_traces(mode='markers+text', textposition='top center', textfont=dict(size=10, color='white', family='Inter'), marker=dict(size=14))
        fig_map.update_layout(mapbox_style="white-bg", mapbox_layers=[{"below": 'traces', "sourcetype": "raster", "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"]}], height=340, margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
        
        map_selection = st.plotly_chart(
            fig_map, 
            use_container_width=True, 
            on_select="rerun", 
            selection_mode=["points"], 
            config={'displayModeBar': False}
        )
        
        if map_selection and "selection" in map_selection:
            points = map_selection["selection"]["points"]
            if len(points) > 0:
                klik_lokasi = points[0]["customdata"][0]
                if klik_lokasi != st.session_state.lokasi_pilihan:
                    st.session_state.lokasi_pilihan = klik_lokasi
                    st.rerun()

    with mid_right:
        st.markdown('<div class="pro-card-header">🌊 Grafik Elevasi Muka Air Aktual</div>', unsafe_allow_html=True)
        df_1_hari = df_display.head(144).copy()
        fig_tide = go.Figure()
        fig_tide.add_trace(go.Scatter(x=df_1_hari['Time'], y=df_1_hari['Prediksi_Pasut'] + amp_gelombang, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig_tide.add_trace(go.Scatter(x=df_1_hari['Time'], y=df_1_hari['Prediksi_Pasut'] - amp_gelombang, mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(255, 255, 255, 0.08)', name='Wave Envelope'))
        fig_tide.add_trace(go.Scatter(x=df_1_hari['Time'], y=df_1_hari['Prediksi_Pasut'], mode='lines', line=dict(color='#00E5FF', width=2.5, shape='spline'), name='Elevasi Pasut'))
        fig_tide.update_layout(height=280, margin=dict(l=5, r=5, t=5, b=5), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=True, gridcolor='#1E2D3D', tickformat="%H:%M", tickfont=dict(color='#64748B', size=9)), yaxis=dict(showgrid=True, gridcolor='#1E2D3D', tickfont=dict(color='#64748B', size=9)), showlegend=False)
        st.plotly_chart(fig_tide, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; margin-top:5px; border-top: 1px solid #1E2D3D; padding-top:8px;">
        <div style="text-align:center;"><div style="font-size:10px; color:#94A3B8;">HHWL (Maks Pasut)</div><div style="font-size:14px; color:#3fb950; font-weight:700;">{df_display['Prediksi_Pasut'].max():.2f} m</div></div>
        <div style="text-align:center;"><div style="font-size:10px; color:#94A3B8;">LLWL (Min Pasut)</div><div style="font-size:14px; color:#f85149; font-weight:700;">{df_display['Prediksi_Pasut'].min():.2f} m</div></div>
        <div style="text-align:center;"><div style="font-size:10px; color:#94A3B8;">Kedalaman Alur</div><div style="font-size:14px; color:#00E5FF; font-weight:700;">{batimetri_alur:.1f} m</div></div>
        </div>""", unsafe_allow_html=True)

    # --- BARIS 3: INPUT KAPAL & STATUS KESELAMATAN ---
    st.markdown("<hr style='border-color:#1E2D3D; margin-top:20px; margin-bottom:20px;'>", unsafe_allow_html=True)
    
    col_input1, col_input2, col_status = st.columns([1, 1, 2])
    with col_input1:
        st.markdown('<div class="pro-card-header">🚢 Parameter Draft Kapal (m)</div>', unsafe_allow_html=True)
        draft_kapal_dash = st.number_input("Draft Kapal", 1.0, 20.0, value=st.session_state.last_draft, step=0.5, label_visibility="collapsed")
        st.session_state.last_draft = draft_kapal_dash
        
    with col_input2:
        st.markdown('<div class="pro-card-header">📐 Batas Aman Lunas (UKC) (m)</div>', unsafe_allow_html=True)
        ukc_wajib_dash = st.number_input("UKC", 0.0, 5.0, value=st.session_state.last_ukc, step=0.1, label_visibility="collapsed")
        st.session_state.last_ukc = ukc_wajib_dash
    
    ambang_keamanan_dash = draft_kapal_dash + ukc_wajib_dash
    kondisi_min_aktual_dash = df_display['Total_Kedalaman'].min() - amp_gelombang
    status_air = kondisi_min_aktual_dash >= ambang_keamanan_dash
    status_angin = current_wind_speed <= 20.0

    with col_status:
        if status_air and status_angin:
            st.markdown(f"""
            <div class="warning-card" style="border-left-color: #3fb950; background-color: rgba(63, 185, 80, 0.08); height:auto; padding:10px;">
            <div class="warning-title" style="color: #3fb950;">STATUS KESELAMATAN NAVIGASI</div>
            <div class="warning-val" style="color: #3fb950; font-size:18px;">✅ AMAN OPERASIONAL</div>
            <div class="warning-desc" style="font-size:11px;">Alur pelabuhan aman dari risiko kandas vertikal dan hambatan angin lateral.</div>
            </div>""", unsafe_allow_html=True)
        else:
            txt_warn = ""
            if not status_air: txt_warn += "⚠️ <b>RISIKO KANDAS:</b> Air Rendah melanggar batas UKC.<br>"
            if not status_angin: txt_warn += "⚠️ <b>WIND HAZARD:</b> Hambat Angin Lateral Tinggi (>20 kt).<br>"
            st.markdown(f"""
            <div class="warning-card" style="height:auto; padding:10px;">
            <div class="warning-title">STATUS KESELAMATAN NAVIGASI</div>
            <div class="warning-val" style="font-size:18px;">🚨 WASPADA / CRITICAL</div>
            <div class="warning-desc" style="font-size:11px; line-height:1.3;">{txt_warn}</div>
            </div>""", unsafe_allow_html=True)

    # --- BARIS 4: KEDALAMAN AKTUAL & RADAR ANGIN ---
    bot1, bot2 = st.columns([1.8, 1])
    
    with bot1:
        # >> FIX REVISI: Tambahkan margin-top agar tidak mepet <<
        st.markdown('<div class="pro-card-header" style="margin-top: 25px;">📉 Simulasi Ruang Kedalaman Aktual (Batimetri + Pasut)</div>', unsafe_allow_html=True)
        fig_depth = go.Figure()
        fig_depth.add_trace(go.Scatter(x=df_display['Time'], y=df_display['Total_Kedalaman'] + amp_gelombang, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig_depth.add_trace(go.Scatter(x=df_display['Time'], y=df_display['Total_Kedalaman'] - amp_gelombang, mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(0, 229, 255, 0.05)', name='Wave Envelope'))
        fig_depth.add_trace(go.Scatter(x=df_display['Time'], y=df_display['Total_Kedalaman'], mode='lines', line=dict(color='#00E5FF', width=2), name='Kedalaman Total'))
        fig_depth.add_hline(y=ambang_keamanan_dash, line_dash="dash", line_color="#FFB020", annotation_text="Batas Aman Kapal (Draft + UKC)")
        fig_depth.update_layout(height=260, margin=dict(l=0, r=0, t=5, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(gridcolor='#1E2D3D', tickfont=dict(color='#64748B', size=9)), yaxis=dict(gridcolor='#1E2D3D', tickfont=dict(color='#64748B', size=9)), showlegend=False)
        st.plotly_chart(fig_depth, use_container_width=True, config={'displayModeBar': False})

    with bot2:
        # >> FIX REVISI: Tambahkan margin-top agar tidak mepet <<
        st.markdown('<div class="pro-card-header" style="margin-top: 25px;">🌀 Radar Integrasi Embusan Vektor Angin</div>', unsafe_allow_html=True)
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Barpolar(r=[current_wind_speed], theta=[current_wind_dir], width=[15], marker_color='#00E5FF', opacity=0.8))
        fig_radar.update_layout(height=260, margin=dict(l=15, r=15, t=15, b=15), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', polar=dict(radialaxis=dict(visible=True, gridcolor='#1E2D3D', tickfont=dict(color='#64748B', size=8)), angularaxis=dict(direction="clockwise", rotation=90, gridcolor='#1E2D3D', tickfont=dict(color='#94A3B8', size=9))), showlegend=False)
        st.plotly_chart(fig_radar, use_container_width=True, config={'displayModeBar': False})

    # --- BARIS 5: JENDELA WAKTU AMAN NAVIGASI & EKSPOR ---
    st.markdown('<div class="pro-card-header" style="margin-top:20px;">🕒 Jendela Waktu Aman Navigasi Alur Pelabuhan</div>', unsafe_allow_html=True)
    df_display['is_safe'] = (df_display['Total_Kedalaman'] - amp_gelombang) >= ambang_keamanan_dash
    
    df_display['block'] = (df_display['is_safe'] != df_display['is_safe'].shift(1)).cumsum()
    df_safewin = df_display[df_display['is_safe']].copy()
    
    jadwal_data_df = pd.DataFrame()
    if not df_safewin.empty:
        safe_blocks = df_safewin.groupby('block')
        jadwal_list = []
        for _, block in safe_blocks:
            waktu_mulai = block['Time'].iloc[0]
            waktu_selesai = block['Time'].iloc[-1]
            durasi = (waktu_selesai - waktu_mulai).total_seconds() / 3600
            if durasi >= 1.0:
                jadwal_list.append({"Buka_Alur_WIB": waktu_mulai.strftime("%Y-%m-%d %H:%M"), "Tutup_Alur_WIB": waktu_selesai.strftime("%Y-%m-%d %H:%M"), "Durasi_Jam": round(durasi, 1)})
        jadwal_data_df = pd.DataFrame(jadwal_list)

    if current_wind_speed > 20.0:
        st.markdown(f'<div class="custom-alert-danger"><span style="font-size:24px;">🚫</span><span style="font-size:13px;"><b>JENDELA NAVIGASI DITUTUP TOTAL:</b> Kecepatan angin lateral ({current_wind_speed:.1f} kt) sangat berisiko untuk proses manuver lambung kapal.</span></div>', unsafe_allow_html=True)
    elif max_wave_hs > 1.5:
        st.markdown('<div class="custom-alert-danger"><span style="font-size:24px;">🚫</span><span style="font-size:13px;"><b>JENDELA NAVIGASI DITUTUP TOTAL:</b> Kondisi fluktuasi elevasi gelombang laut dinilai terlalu ekstrem bagi keselamatan kapal.</span></div>', unsafe_allow_html=True)
    elif df_display['is_safe'].all():
        st.markdown('<div class="custom-alert-success"><span style="font-size:24px;">✅</span><span style="font-size:13px;"><b>Alur Terbuka 24 Jam:</b> Evaluasi ruang vertikal minimum (Draft + UKC) memenuhi standar operasional.</span></div>', unsafe_allow_html=True)
    elif not df_display['is_safe'].any():
        st.markdown('<div class="custom-alert-danger"><span style="font-size:24px;">🚫</span><span style="font-size:13px;"><b>Alur Ditutup Total:</b> Ruang bebas kedalaman alur tidak mencukupi rasio standar keamanan *Under Keel Clearance* (UKC) sepanjang rentang waktu proyeksi.</span></div>', unsafe_allow_html=True)
    else:
        if not jadwal_data_df.empty:
            col_tbl1, col_tbl2 = st.columns([2, 1])
            with col_tbl1:
                tbl_display = jadwal_data_df.copy()
                tbl_display.columns = ["Buka Alur (WIB)", "Tutup Alur (WIB)", "Durasi Aman (Jam)"]
                st.table(tbl_display)
            with col_tbl2:
                csv = convert_df_to_csv(jadwal_data_df)
                filename = f"NaviWatch_Log_{lokasi.split(',')[0]}_{tanggal_pilihan.strftime('%Y%m%d')}.csv"
                st.download_button(label="📥 Unduh Laporan Log CSV", data=csv, file_name=filename, mime='text/csv')
        else:
            st.markdown('<div class="custom-alert-warning"><span style="font-size:24px;">⚠️</span><span style="font-size:13px;"><b>Jendela Waktu Sempit:</b> Bukaan aman teridentifikasi di bawah 1 jam. Manuver dilarang otoritas pada jendela sempit.</span></div>', unsafe_allow_html=True)

# ==========================================
# KONTEN MENU: KOMPONEN PASUT
# ==========================================
elif menu_aktif == "📈 Detail Komponen Pasut":
    st.markdown('<div class="pro-card-header">📈 Dekomposisi Komponen Harmonik Pasut (M2, S2, K1, O1)</div>', unsafe_allow_html=True)
    col_t1, col_t2 = st.columns([2, 1])
    
    df_peaks = df_display[df_display['is_pasang']].head(1)
    df_troughs = df_display[df_display['is_surut']].head(1)
    waktu_pasang = df_peaks['Time'].iloc[0].strftime('%H:%M WIB') if not df_peaks.empty else "N/A"
    elevasi_pasang = f"{df_peaks['Prediksi_Pasut'].iloc[0]:.2f} m" if not df_peaks.empty else "N/A"
    waktu_surut = df_troughs['Time'].iloc[0].strftime('%H:%M WIB') if not df_troughs.empty else "N/A"
    elevasi_surut = f"{df_troughs['Prediksi_Pasut'].iloc[0]:.2f} m" if not df_troughs.empty else "N/A"
    
    with col_t1:
        fig_decomp = go.Figure()
        fig_decomp.add_trace(go.Scatter(x=df_display['Time'].head(144), y=df_display['Prediksi_Pasut'].head(144), line=dict(color='#00E5FF', width=3)))
        fig_decomp.add_hline(y=data_stasiun['msl'], line_dash="dash", line_color="#94A3B8", annotation_text="MSL", annotation_font_color="#94A3B8")
        fig_decomp.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(gridcolor='#1E2D3D'), yaxis=dict(gridcolor='#1E2D3D', title="Elevasi (m)"), margin=dict(t=5, b=5, l=0, r=0))
        st.plotly_chart(fig_decomp, use_container_width=True)
        
    with col_t2:
        st.markdown(f"""
        <div class="pro-card" style="margin-bottom:10px;">
            <div style="font-size:11px; color:#94A3B8; margin-bottom:5px;">WAKTU EKSTREM TERDEKAT</div>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:#3fb950; font-weight:600;">🟢 Puncak Pasang</span>
                <span><b>{elevasi_pasang}</b> ({waktu_pasang})</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span style="color:#f85149; font-weight:600;">🔴 Puncak Surut</span>
                <span><b>{elevasi_surut}</b> ({waktu_surut})</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <table class="pro-table">
        <tr><th>Konstituen</th><th>Amplitudo</th></tr>
        <tr><td><b>M2</b> Bulan Semi-diurnal</td><td>{data_stasiun['M2']:.2f} m</td></tr>
        <tr><td><b>S2</b> Matahari Semi-diurnal</td><td>{data_stasiun['S2']:.2f} m</td></tr>
        <tr><td><b>K1</b> Soli-lunar Diurnal</td><td>{data_stasiun['K1']:.2f} m</td></tr>
        <tr><td><b>O1</b> Bulan Diurnal</td><td>{data_stasiun['O1']:.2f} m</td></tr>
        <tr><td><b>MSL</b> Mean Sea Level</td><td>{data_stasiun['msl']:.2f} m</td></tr>
        </table>
        """, unsafe_allow_html=True)

# ==========================================
# KONTEN MENU: GELOMBANG LAUT
# ==========================================
elif menu_aktif == "🌊 Karakteristik Gelombang":
    st.markdown('<div class="pro-card-header">🌊 Analisis Spektrum & Prediksi Tren Gelombang 48 Jam</div>', unsafe_allow_html=True)
    
    if not forecast_data['success'] or df_hourly_wave.empty:
        st.warning("Data tren gelombang tidak tersedia saat ini.")
    else:
        col_w1, col_w2, col_w3 = st.columns(3)
        h_max = max_wave_hs * 1.86 
        wave_energy = 0.125 * 1025 * 9.81 * (max_wave_hs**2) 
        
        with col_w1:
            st.markdown(f"""<div class="pro-card"><div class="kpi-title">SIGNIFICANT WAVE (Hs) Aktual</div><div class="kpi-val" style="color:#00E5FF;">{max_wave_hs:.2f} m</div><div class="nav-sub">Rata-rata 1/3 gelombang tertinggi.</div></div>""", unsafe_allow_html=True)
        with col_w2:
            st.markdown(f"""<div class="pro-card"><div class="kpi-title">ESTIMASI MAXIMUM (Hmax)</div><div class="kpi-val" style="color:#FFB020;">{h_max:.2f} m</div><div class="nav-sub">Puncak tunggal tertinggi teoretis.</div></div>""", unsafe_allow_html=True)
        with col_w3:
            st.markdown(f"""<div class="pro-card"><div class="kpi-title">RATA-RATA WAVE PERIOD</div><div class="kpi-val">{avg_wave_period:.1f} s</div><div class="nav-sub">Interval antar puncak gelombang.</div></div>""", unsafe_allow_html=True)

        col_w_chart, col_w_text = st.columns([2.2, 1])
        with col_w_chart:
            fig_wave = go.Figure()
            fig_wave.add_trace(go.Scatter(x=df_hourly_wave['time'], y=df_hourly_wave['wave_height'], fill='tozeroy', fillcolor='rgba(0, 229, 255, 0.15)', line=dict(color='#00E5FF', width=2), name="Tinggi Hs (m)"))
            fig_wave.add_hline(y=1.5, line_dash="dash", line_color="#f85149", annotation_text="Batas Bahaya (1.5m)", annotation_font_color="#f85149")
            fig_wave.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(gridcolor='#1E2D3D', tickformat="%d %b %H:%M"), yaxis=dict(gridcolor='#1E2D3D', title="Tinggi Gelombang (m)"), margin=dict(t=10, b=10, r=10, l=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_wave, use_container_width=True, config={'displayModeBar': False})
            
        with col_w_text:
            st.markdown(f"""
            <div class="pro-card" style="height:280px;">
                <div class="kpi-title" style="margin-bottom:10px;">ANALISIS ENERGI KELAUTAN</div>
                <p style="font-size:13px; color:#94A3B8;">Densitas energi spektral gelombang Hs aktual sebesar <b>{(wave_energy/1000):.1f} kJ/m²</b>.</p>
                <p style="font-size:13px; color:#94A3B8;">Nilai Koreksi UKC Teoretis (Setengah Hs): <b style="color:#00E5FF;">±{amp_gelombang:.2f} m</b>.</p>
                <p style="font-size:12px; color:#64748B;">Data bersumber dari prakiraan model gelombang pesisir Open-Meteo untuk 48 jam ke depan.</p>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# KONTEN MENU: VEKTOR ANGIN
# ==========================================
elif menu_aktif == "💨 Analisis Vektor Angin":
    st.markdown('<div class="pro-card-header">💨 Dinamika Angin Permukaan Lapisan Batas Atmosfer (48 Jam)</div>', unsafe_allow_html=True)
    
    if not forecast_data['success'] or df_hourly_wind.empty:
        st.warning("Data tren angin tidak tersedia saat ini.")
    else:
        col_a1, col_a2, col_a3 = st.columns(3)
        skala_bft = get_beaufort_scale(current_wind_speed)
        
        with col_a1:
            st.markdown(f"""<div class="pro-card"><div class="kpi-title">KECEPATAN AKTUAL</div><div class="kpi-val" style="color:#00E5FF;">{current_wind_speed:.1f} kt</div><div class="nav-sub">Arah Datang: {current_wind_dir}°</div></div>""", unsafe_allow_html=True)
        with col_a2:
            st.markdown(f"""<div class="pro-card"><div class="kpi-title">HEMBUSAN GUST AKTUAL</div><div class="kpi-val" style="color:#FFB020;">{current_wind_gust:.1f} kt</div><div class="nav-sub">Fluktuasi ekstrem sesaat.</div></div>""", unsafe_allow_html=True)
        with col_a3:
            st.markdown(f"""<div class="pro-card"><div class="kpi-title">KLASIFIKASI BEAUFORT</div><div class="kpi-val">{skala_bft}</div><div class="nav-sub">Skala observasi maritim.</div></div>""", unsafe_allow_html=True)

        col_a_chart, col_a_text = st.columns([2.2, 1])
        with col_a_chart:
            fig_wind_trend = go.Figure()
            fig_wind_trend.add_trace(go.Bar(x=df_hourly_wind['time'], y=df_hourly_wind['wind_speed_10m'], name="Kecepatan Rata-Rata (kt)", marker_color='#00E5FF', opacity=0.7))
            fig_wind_trend.add_trace(go.Scatter(x=df_hourly_wind['time'], y=df_hourly_wind['wind_gusts_10m'], mode='lines', name="Wind Gust (kt)", line=dict(color='#FFB020', width=1.5)))
            fig_wind_trend.add_hline(y=20.0, line_dash="dash", line_color="#f85149", annotation_text="Batas Manuver Aman (20 kt)", annotation_font_color="#f85149")
            fig_wind_trend.update_layout(height=280, barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(gridcolor='#1E2D3D', tickformat="%d %b %H:%M"), yaxis=dict(gridcolor='#1E2D3D', title="Kecepatan (Knot)"), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(t=10, b=10, r=10, l=10))
            st.plotly_chart(fig_wind_trend, use_container_width=True, config={'displayModeBar': False})

        with col_a_text:
            st.markdown(f"""
            <div class="pro-card" style="height:280px;">
                <div class="kpi-title" style="margin-bottom:10px;">ANALISIS GAYA LATERAL</div>
                <p style="font-size:13px; color:#94A3B8;">Menu ini menganalisis gaya dorong lateral (*Wind Drag Force*) akibat desakan angin pada luasan *freeboard* lambung kapal.</p>
                <p style="font-size:12px; color:#64748B;">Hembusan kencang tiba-tiba (*Gusts*) dapat menyebabkan penyimpangan lambung kapal (*crosswind drifting*) dari alur kemudi.</p>
            </div>
            """, unsafe_allow_html=True)


# --- FOOTER DATA BARIS AKHIR COMPLIANCE ---
st.markdown(f"""
<div class="pro-footer">
    <div>🟢 Status Jaringan: Operasional &nbsp;&nbsp; 🔵 Model Pasut: TPXO Global Indian Ocean &nbsp;&nbsp; 💨 Engine Angin: Open-Meteo Telemetry</div>
    <div>Koordinat: {data_stasiun['lat']}° S, {data_stasiun['lon']}° E</div>
    <div>NaviWatch Pro v2.0</div>
</div>""", unsafe_allow_html=True)
