"""
SentryGround-Zero: Mission Control Dashboard
Professional ESA/NASA-style visualization platform for satellite monitoring,
physics simulations, and scientific research.
"""

import streamlit as st
import os
import json
import time
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle, FancyBboxPatch, Wedge
from datetime import datetime, timezone
from typing import Optional, Tuple

st.set_page_config(
    page_title="SentryGround-Zero | Mission Control",
    layout="wide",
    page_icon="🛰️",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* ESA/NASA Mission Control Theme */
    :root {
        --bg-primary: #0A0E17;
        --bg-secondary: #111827;
        --bg-tertiary: #1F2937;
        --accent-cyan: #00D4FF;
        --accent-blue: #3B82F6;
        --accent-green: #10B981;
        --accent-yellow: #F59E0B;
        --accent-red: #EF4444;
        --accent-purple: #8B5CF6;
        --text-primary: #F9FAFB;
        --text-secondary: #9CA3AF;
        --border-color: #374151;
    }
    
    .stApp {
        background: linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
        color: var(--text-primary);
    }
    
    /* Header Styling */
    .main-header {
        background: linear-gradient(90deg, #0A0E17 0%, #111827 50%, #0A0E17 100%);
        padding: 1rem 2rem;
        border-bottom: 2px solid var(--accent-cyan);
        margin-bottom: 1rem;
    }
    
    .main-header h1 {
        color: var(--accent-cyan);
        font-family: 'Courier New', monospace;
        font-size: 1.8rem;
        font-weight: bold;
        margin: 0;
        letter-spacing: 2px;
    }
    
    /* Status Indicators */
    .status-online {
        color: var(--accent-green);
        font-weight: bold;
    }
    
    .status-warning {
        color: var(--accent-yellow);
        font-weight: bold;
    }
    
    .status-critical {
        color: var(--accent-red);
        font-weight: bold;
    }
    
    /* Metric Cards */
    .metric-card {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* Panel Styling */
    .panel {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1rem;
    }
    
    /* Data Tables */
    .data-table {
        width: 100%;
        border-collapse: collapse;
    }
    
    .data-table th {
        background: var(--bg-tertiary);
        color: var(--accent-cyan);
        padding: 0.5rem;
        text-align: left;
        border-bottom: 2px solid var(--accent-cyan);
    }
    
    .data-table td {
        padding: 0.5rem;
        border-bottom: 1px solid var(--border-color);
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--border-color);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--accent-cyan);
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: var(--bg-secondary);
        padding: 0.5rem;
        border-radius: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: var(--text-secondary);
        border-radius: 6px;
        padding: 0.75rem 1.5rem;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: var(--bg-tertiary);
        color: var(--text-primary);
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--accent-cyan) !important;
        color: var(--bg-primary) !important;
        font-weight: bold;
    }
    
    /* Streamlit Component Overrides */
    div[data-testid="stMetricValue"] {
        color: var(--accent-cyan) !important;
        font-family: 'Courier New', monospace;
        font-size: 1.5rem;
    }
    
    div[data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
        font-size: 0.9rem;
    }
    
    div[data-testid="stMetricDelta"] {
        color: var(--accent-green) !important;
    }
    
    .streamlit-expanderHeader {
        background: var(--bg-tertiary);
        border-radius: 6px;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: var(--bg-secondary);
    }
    
    /* Footer */
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: var(--bg-secondary);
        border-top: 1px solid var(--border-color);
        padding: 0.5rem 2rem;
        font-size: 0.8rem;
        color: var(--text-secondary);
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


BASE_DIR = "simulation_data"
INGEST_DIR = os.path.join(BASE_DIR, "ingest_landing_zone")


def get_latest_product():
    """Reads the Landing Zone for the most recent satellite payload."""
    if not os.path.exists(INGEST_DIR):
        return None, None
    
    files = [f for f in os.listdir(INGEST_DIR) if f.endswith(".json")]
    if not files:
        return None, None
    
    files.sort(key=lambda x: os.path.getmtime(os.path.join(INGEST_DIR, x)), reverse=True)
    latest_meta = os.path.join(INGEST_DIR, files[0])
    
    with open(latest_meta, "r") as f:
        meta = json.load(f)
    
    npy_file = os.path.join(INGEST_DIR, files[0].replace(".json", ".npy"))
    if os.path.exists(npy_file):
        data = np.load(npy_file)
        return meta, data
    return meta, None


def draw_earth_orbital_diagram(ax, lat: float, lon: float, regime: str, altitude: float):
    """Draws an Earth-centered orbital mechanics diagram ESA/NASA style."""
    ax.clear()
    ax.set_aspect('equal')
    ax.set_xlim(-1.8, 1.8)
    ax.set_ylim(-1.8, 1.8)
    
    earth = Circle((0, 0), 0.25, color='#1E3A5F', alpha=0.9, zorder=2)
    ax.add_patch(earth)
    
    earth_highlight = Circle((-0.05, 0.05), 0.15, color='#2563EB', alpha=0.3, zorder=3)
    ax.add_patch(earth_highlight)
    
    atmosphere = Circle((0, 0), 0.27, color='#00D4FF', alpha=0.1, zorder=1)
    ax.add_patch(atmosphere)
    
    r_orbit = 0.25 + altitude / 42000 * 1.2
    theta = np.linspace(0, 2*np.pi, 100)
    x_orbit = r_orbit * np.cos(theta)
    y_orbit = r_orbit * np.sin(theta)
    ax.plot(x_orbit, y_orbit, 'c-', alpha=0.6, linewidth=1.5, zorder=1)
    
    sat_angle = np.radians(lon)
    sat_x = r_orbit * np.cos(sat_angle)
    sat_y = r_orbit * np.sin(sat_angle)
    
    ax.plot([0, sat_x], [0, sat_y], 'r--', alpha=0.5, linewidth=1, zorder=4)
    ax.plot(sat_x, sat_y, 'r*', markersize=15, zorder=5)
    
    ax.plot([0, 0], [0, 1.7], 'w-', alpha=0.2, linewidth=0.5)
    ax.plot([0, 1.7], [0, 0], 'w-', alpha=0.2, linewidth=0.5)
    
    regime_colors = {
        'LEO': '#10B981',
        'MEO': '#F59E0B',
        'GEO': '#EF4444',
        'HEO': '#8B5CF6',
        'Lunar Transfer': '#00D4FF',
    }
    color = regime_colors.get(regime, '#9CA3AF')
    
    ax.text(sat_x * 1.1, sat_y * 1.1, f'SAT\n{lat:.1f}°, {lon:.1f}°\n{altitude:.0f} km',
            color=color, fontsize=8, ha='center', va='bottom', zorder=6,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#111827', alpha=0.8))
    
    ax.set_facecolor('#0A0E17')
    ax.axis('off')
    
    ax.set_title(f'ORBITAL GEOMETRY — {regime}', color='#00D4FF', fontsize=12, fontweight='bold', pad=10)


def draw_world_map(ax, lat: float, lon: float, regime: str):
    """Draws a world map with satellite position - NASA-style."""
    ax.set_facecolor('#0A0E17')
    
    theta = np.linspace(0, 2*np.pi, 100)
    r = np.linspace(0.95, 1.0, 50)
    theta_grid, r_grid = np.meshgrid(theta, r)
    ax.pcolormesh(theta_grid * 180 / np.pi - 180, r_grid * 90 - 90,
                  np.zeros((50, 100)), cmap='Blues', alpha=0.1, shading='auto')
    
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    
    for lon_line in range(-180, 181, 30):
        ax.axvline(lon_line, color='#374151', alpha=0.3, linewidth=0.5)
    for lat_line in range(-90, 91, 30):
        ax.axhline(lat_line, color='#374151', alpha=0.3, linewidth=0.5)
    
    ax.set_xlabel('Longitude (°)', color='#9CA3AF', fontsize=10)
    ax.set_ylabel('Latitude (°)', color='#9CA3AF', fontsize=10)
    ax.tick_params(colors='#9CA3AF')
    
    ax.plot(lon, lat, 'r*', markersize=20, zorder=10, label='SAT')
    
    regime_colors = {
        'LEO': '#10B981',
        'MEO': '#F59E0B', 
        'GEO': '#EF4444',
        'HEO': '#8B5CF6',
        'Lunar Transfer': '#00D4FF',
    }
    color = regime_colors.get(regime, '#FFFFFF')
    
    ax.scatter([lon], [lat], c=color, s=200, alpha=0.5, zorder=9)
    
    ax.set_title(f'GROUND TRACK — {lat:.2f}°N, {abs(lon):.2f}°{"E" if lon >= 0 else "W"}',
                 color='#00D4FF', fontsize=11, fontweight='bold')


def draw_climate_simulation():
    """Climate simulation visualization with professional styling."""
    try:
        from secure_eo_pipeline.physics import ClimateSimulation, radiative_forcing_CO2
        
        fig = plt.figure(figsize=(14, 10))
        fig.patch.set_facecolor('#0A0E17')
        
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        
        sim = ClimateSimulation()
        years = []
        temps = []
        co2_levels = []
        amoc_vals = []
        sea_levels = []
        
        for _ in range(150):
            sim.step()
            state = sim.get_state()
            years.append(state['year'])
            temps.append(state['dT_global'])
            co2_levels.append(state['CO2_ppm'])
            amoc_vals.append(state.get('AMOC_sv', 17))
            sea_levels.append(state.get('sea_level_m', 0) * 100)
        
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_facecolor('#111827')
        ax1.plot(years, temps, '#EF4444', linewidth=2, label='Global Anomaly')
        ax1.fill_between(years, temps, alpha=0.3, color='#EF4444')
        ax1.axhline(0, color='#9CA3AF', linestyle='--', alpha=0.5)
        ax1.set_title('GLOBAL TEMPERATURE ANOMALY', color='#00D4FF', fontsize=10, fontweight='bold')
        ax1.set_xlabel('Year', color='#9CA3AF')
        ax1.set_ylabel('ΔT (K)', color='#9CA3AF')
        ax1.tick_params(colors='#9CA3AF')
        for spine in ax1.spines.values():
            spine.set_color('#374151')
        
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.set_facecolor('#111827')
        ax2.plot(years, co2_levels, '#10B981', linewidth=2)
        ax2.fill_between(years, co2_levels, alpha=0.3, color='#10B981')
        ax2.set_title('ATMOSPHERIC CO₂ CONCENTRATION', color='#00D4FF', fontsize=10, fontweight='bold')
        ax2.set_xlabel('Year', color='#9CA3AF')
        ax2.set_ylabel('CO₂ (ppm)', color='#9CA3AF')
        ax2.tick_params(colors='#9CA3AF')
        for spine in ax2.spines.values():
            spine.set_color('#374151')
        
        ax3 = fig.add_subplot(gs[1, 0])
        ax3.set_facecolor('#111827')
        ax3.plot(years, amoc_vals, '#3B82F6', linewidth=2)
        ax3.fill_between(years, amoc_vals, alpha=0.3, color='#3B82F6')
        ax3.axhline(17, color='#EF4444', linestyle='--', alpha=0.7, label='AMOC Collapse Threshold')
        ax3.set_title('ATLANTIC CIRCULATION (AMOC)', color='#00D4FF', fontsize=10, fontweight='bold')
        ax3.set_xlabel('Year', color='#9CA3AF')
        ax3.set_ylabel('Strength (Sv)', color='#9CA3AF')
        ax3.tick_params(colors='#9CA3AF')
        ax3.legend(loc='upper left', facecolor='#111827', labelcolor='#9CA3AF', fontsize=8)
        for spine in ax3.spines.values():
            spine.set_color('#374151')
        
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.set_facecolor('#111827')
        ax4.plot(years, sea_levels, '#8B5CF6', linewidth=2)
        ax4.fill_between(years, sea_levels, alpha=0.3, color='#8B5CF6')
        ax4.set_title('GLOBAL MEAN SEA LEVEL RISE', color='#00D4FF', fontsize=10, fontweight='bold')
        ax4.set_xlabel('Year', color='#9CA3AF')
        ax4.set_ylabel('Rise (cm)', color='#9CA3AF')
        ax4.tick_params(colors='#9CA3AF')
        for spine in ax4.spines.values():
            spine.set_color('#374151')
        
        plt.tight_layout()
        return fig
    except Exception as e:
        st.error(f"Climate simulation error: {e}")
        return None


def draw_cosmology_panel():
    """Cosmological parameters visualization."""
    try:
        from secure_eo_pipeline.physics import CosmologyParams, Hubble, comoving_distance, power_spectrum_EH
        
        fig = plt.figure(figsize=(14, 5))
        fig.patch.set_facecolor('#0A0E17')
        
        gs = fig.add_gridspec(1, 3, wspace=0.3)
        
        z_vals = np.linspace(0.01, 5, 200)
        H_vals = [Hubble(z) for z in z_vals]
        D_vals = [comoving_distance(z, n_steps=50) for z in z_vals]
        
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_facecolor('#111827')
        ax1.plot(z_vals, H_vals, '#00D4FF', linewidth=2)
        ax1.fill_between(z_vals, H_vals, alpha=0.2, color='#00D4FF')
        ax1.set_title('HUBBLE PARAMETER H(z)', color='#00D4FF', fontsize=10, fontweight='bold')
        ax1.set_xlabel('Redshift z', color='#9CA3AF')
        ax1.set_ylabel('H(z) [km/s/Mpc]', color='#9CA3AF')
        ax1.tick_params(colors='#9CA3AF')
        for spine in ax1.spines.values():
            spine.set_color('#374151')
        
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.set_facecolor('#111827')
        ax2.plot(z_vals, D_vals, '#10B981', linewidth=2)
        ax2.fill_between(z_vals, D_vals, alpha=0.2, color='#10B981')
        ax2.set_title('COMOVING DISTANCE', color='#00D4FF', fontsize=10, fontweight='bold')
        ax2.set_xlabel('Redshift z', color='#9CA3AF')
        ax2.set_ylabel('D(z) [Mpc]', color='#9CA3AF')
        ax2.tick_params(colors='#9CA3AF')
        for spine in ax2.spines.values():
            spine.set_color('#374151')
        
        k_vals = np.logspace(-3, 1, 100)
        pk_vals = [power_spectrum_EH(k, 0.0) for k in k_vals]
        
        ax3 = fig.add_subplot(gs[0, 2])
        ax3.set_facecolor('#111827')
        ax3.loglog(k_vals, pk_vals, '#F59E0B', linewidth=2)
        ax3.fill_between(k_vals, pk_vals, alpha=0.2, color='#F59E0B')
        ax3.set_title('MATTER POWER SPECTRUM', color='#00D4FF', fontsize=10, fontweight='bold')
        ax3.set_xlabel('k [h/Mpc]', color='#9CA3AF')
        ax3.set_ylabel('P(k)', color='#9CA3AF')
        ax3.tick_params(colors='#9CA3AF')
        for spine in ax3.spines.values():
            spine.set_color('#374151')
        
        plt.tight_layout()
        return fig
    except Exception as e:
        st.error(f"Cosmology error: {e}")
        return None


def draw_gravitational_waves():
    """Gravitational wave detection visualization."""
    try:
        from secure_eo_pipeline.physics import generate_chirp_timeseries, ligo_noise_psd
        
        fig = plt.figure(figsize=(14, 8))
        fig.patch.set_facecolor('#0A0E17')
        
        gs = fig.add_gridspec(2, 1, hspace=0.3)
        
        m1, m2 = 30.0, 25.0
        h_plus, h_cross = generate_chirp_timeseries(m1, m2, 410.0, f_start=20.0, f_end=512.0)
        
        t = np.linspace(0, 1, len(h_plus))
        
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_facecolor('#111827')
        ax1.plot(t, h_plus, '#10B981', linewidth=1, label='h₊', alpha=0.8)
        ax1.plot(t, h_cross, '#EF4444', linewidth=1, label='h×', alpha=0.8)
        ax1.set_title('GW150914-LIKE CHIRP SIGNAL DETECTION', color='#00D4FF', fontsize=11, fontweight='bold')
        ax1.set_xlabel('Time [s] from merger', color='#9CA3AF')
        ax1.set_ylabel('Strain h(t)', color='#9CA3AF')
        ax1.tick_params(colors='#9CA3AF')
        ax1.legend(loc='upper right', facecolor='#111827', labelcolor='#9CA3AF')
        for spine in ax1.spines.values():
            spine.set_color('#374151')
        
        f = np.linspace(20, 512, 1000)
        psd = ligo_noise_psd(f)
        
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.set_facecolor('#111827')
        ax2.semilogy(f, np.sqrt(psd), '#3B82F6', linewidth=1.5, label='LIGO Design Sensitivity')
        ax2.fill_between(f, np.sqrt(psd), alpha=0.2, color='#3B82F6')
        ax2.set_title('DETECTOR NOISE SPECTRAL DENSITY', color='#00D4FF', fontsize=11, fontweight='bold')
        ax2.set_xlabel('Frequency [Hz]', color='#9CA3AF')
        ax2.set_ylabel('Strain/√Hz', color='#9CA3AF')
        ax2.tick_params(colors='#9CA3AF')
        ax2.legend(loc='upper right', facecolor='#111827', labelcolor='#9CA3AF')
        for spine in ax2.spines.values():
            spine.set_color('#374151')
        
        plt.tight_layout()
        return fig
    except Exception as e:
        st.error(f"GW error: {e}")
        return None


def draw_exoplanet_transit():
    """Exoplanet transit lightcurve visualization."""
    try:
        from secure_eo_pipeline.physics import generate_transit_lightcurve, habitable_zone_Kopparapu
        
        fig = plt.figure(figsize=(14, 6))
        fig.patch.set_facecolor('#0A0E17')
        
        gs = fig.add_gridspec(1, 2, wspace=0.3)
        
        time_arr, flux = generate_transit_lightcurve(
            time_hours=12.0, P_hours=5.0, Rp_Rs=0.1, a_Rs=10.0
        )
        
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_facecolor('#111827')
        ax1.plot(time_arr, flux, '#00D4FF', linewidth=1.5)
        ax1.fill_between(time_arr, flux, alpha=0.3, color='#00D4FF')
        ax1.axhline(1.0, color='#9CA3AF', linestyle='--', alpha=0.5)
        
        inner, outer = habitable_zone_Kopparapu(5778, 1.0)
        ax1.axhspan(0.995, 1.005, alpha=0.3, color='#10B981', label=f'Habitable Zone')
        
        ax1.set_title('TRANSIT PHOTOMETRY', color='#00D4FF', fontsize=11, fontweight='bold')
        ax1.set_xlabel('Time [hours]', color='#9CA3AF')
        ax1.set_ylabel('Normalized Flux', color='#9CA3AF')
        ax1.tick_params(colors='#9CA3AF')
        ax1.legend(loc='upper right', facecolor='#111827', labelcolor='#9CA3AF')
        for spine in ax1.spines.values():
            spine.set_color('#374151')
        
        periods = np.linspace(1, 100, 100)
        transit_depths = [(0.1 / 10)**2 * (100 / p)**(2/3) for p in periods]
        
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.set_facecolor('#111827')
        ax2.semilogy(periods, transit_depths, '#8B5CF6', linewidth=2)
        ax2.fill_between(periods, transit_depths, alpha=0.2, color='#8B5CF6')
        ax2.set_title('DETECTABILITY ANALYSIS', color='#00D4FF', fontsize=11, fontweight='bold')
        ax2.set_xlabel('Orbital Period [days]', color='#9CA3AF')
        ax2.set_ylabel('Transit Depth', color='#9CA3AF')
        ax2.tick_params(colors='#9CA3AF')
        for spine in ax2.spines.values():
            spine.set_color('#374151')
        
        plt.tight_layout()
        return fig
    except Exception as e:
        st.error(f"Exoplanet error: {e}")
        return None


def draw_planetary_defense():
    """Near-Earth Object catalog visualization."""
    try:
        from secure_eo_pipeline.physics import NEO_CATALOG, impact_energy_mt
        
        fig = plt.figure(figsize=(14, 8))
        fig.patch.set_facecolor('#0A0E17')
        
        ax = fig.add_subplot()
        ax.set_facecolor('#111827')
        
        names = []
        energies = []
        diameters = []
        
        for sb in list(NEO_CATALOG.values())[:20]:
            name = sb.name.split()[-1] if ' ' in sb.name else sb.name
            names.append(name)
            energies.append(impact_energy_mt(sb.physical.diameter_km, 2.5, 20.0))
            diameters.append(sb.physical.diameter_km * 1000)
        
        colors = plt.cm.YlOrRd(np.linspace(0.2, 0.9, len(names)))
        
        bars = ax.barh(names, energies, color=colors, edgecolor='#0A0E17', linewidth=0.5)
        
        ax.set_xscale('log')
        ax.set_title('NEAR-EARTH OBJECTS — IMPACT ENERGY ASSESSMENT', 
                     color='#00D4FF', fontsize=12, fontweight='bold')
        ax.set_xlabel('Impact Energy [Mt TNT equivalent]', color='#9CA3AF')
        ax.tick_params(colors='#9CA3AF', labelsize=9)
        
        for i, (name, energy) in enumerate(zip(names, energies)):
            ax.text(energy * 1.1, i, f'{energy:.1e}', va='center', fontsize=8, color='#9CA3AF')
        
        for spine in ax.spines.values():
            spine.set_color('#374151')
        
        legend_elements = [
            mpatches.Patch(facecolor='#FEF3C7', label='<100 m'),
            mpatches.Patch(facecolor='#FDE68A', label='100-500 m'),
            mpatches.Patch(facecolor='#F59E0B', label='500m-1 km'),
            mpatches.Patch(facecolor='#EF4444', label='>1 km'),
        ]
        ax.legend(handles=legend_elements, loc='lower right', 
                  facecolor='#111827', labelcolor='#9CA3AF', fontsize=8, ncol=2)
        
        plt.tight_layout()
        return fig
    except Exception as e:
        st.error(f"Planetary defense error: {e}")
        return None


def draw_dark_matter_profile():
    """Dark matter density profile visualization."""
    try:
        from secure_eo_pipeline.physics import nfw_density
        
        fig = plt.figure(figsize=(14, 5))
        fig.patch.set_facecolor('#0A0E17')
        
        gs = fig.add_gridspec(1, 2, wspace=0.3)
        
        r = np.logspace(-1, 2, 100)
        
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_facecolor('#111827')
        
        for i, label in enumerate(['Dwarf', 'LMC', 'Milky Way', 'Cluster']):
            rho = [nfw_density(r_val, 1e8, 10) * (i + 1) for r_val in r]
            ax1.loglog(r, rho, linewidth=2, label=label)
        
        ax1.set_title('DARK MATTER DENSITY PROFILES', color='#00D4FF', fontsize=11, fontweight='bold')
        ax1.set_xlabel('r [kpc]', color='#9CA3AF')
        ax1.set_ylabel('ρ(r) [M☉/kpc³]', color='#9CA3AF')
        ax1.tick_params(colors='#9CA3AF')
        ax1.legend(loc='upper right', facecolor='#111827', labelcolor='#9CA3AF')
        ax1.set_xlim(0.1, 100)
        for spine in ax1.spines.values():
            spine.set_color('#374151')
        
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.set_facecolor('#111827')
        
        theta = np.linspace(0, 2*np.pi, 100)
        r_iso = np.linspace(0.1, 50, 50)
        theta_grid, r_grid = np.meshgrid(theta, r_iso)
        z_iso = 20 * np.exp(-r_iso / 15)
        
        im = ax2.contourf(theta_grid, r_grid, np.tile(z_iso.reshape(-1, 1), (1, len(theta))), 
                          levels=20, cmap='magma', alpha=0.8)
        ax2.set_aspect('equal')
        ax2.set_title('HALO MORPHOLOGY (SCHEMATIC)', color='#00D4FF', fontsize=11, fontweight='bold')
        ax2.set_xlabel('θ [rad]', color='#9CA3AF')
        ax2.set_ylabel('r [kpc]', color='#9CA3AF')
        ax2.tick_params(colors='#9CA3AF')
        plt.colorbar(im, ax=ax2, label='Relative Density', 
                     mappable=plt.cm.ScalarMappable(cmap='magma'), ax=ax2)
        for spine in ax2.spines.values():
            spine.set_color('#374151')
        
        plt.tight_layout()
        return fig
    except Exception as e:
        st.error(f"Dark matter error: {e}")
        return None


def draw_security_dashboard():
    """Security monitoring dashboard."""
    try:
        from secure_eo_pipeline.components.ids import IntrusionDetectionSystem
        
        fig = plt.figure(figsize=(14, 8))
        fig.patch.set_facecolor('#0A0E17')
        
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        
        time_range = 24
        timestamps = np.arange(time_range)
        
        auth_attempts = np.random.poisson(2, time_range)
        failed_attempts = np.random.poisson(0.3, time_range)
        threats_detected = np.random.poisson(0.1, time_range)
        
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_facecolor('#111827')
        ax1.bar(timestamps, auth_attempts, color='#3B82F6', alpha=0.7, label='Auth Attempts')
        ax1.bar(timestamps, failed_attempts, color='#EF4444', alpha=0.7, label='Failed')
        ax1.set_title('AUTHENTICATION EVENTS (24H)', color='#00D4FF', fontsize=10, fontweight='bold')
        ax1.set_xlabel('Hour', color='#9CA3AF')
        ax1.set_ylabel('Count', color='#9CA3AF')
        ax1.tick_params(colors='#9CA3AF')
        ax1.legend(loc='upper right', facecolor='#111827', labelcolor='#9CA3AF', fontsize=8)
        for spine in ax1.spines.values():
            spine.set_color('#374151')
        
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.set_facecolor('#111827')
        severity = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        counts = [45, 12, 3, 0]
        colors = ['#10B981', '#F59E0B', '#EF4444', '#8B0000']
        ax2.pie(counts, labels=severity, colors=colors, autopct='%1.0f%%', 
                textprops={'color': '#9CA3AF'}, 
                wedgeprops={'edgecolor': '#0A0E17'})
        ax2.set_title('THREAT SEVERITY DISTRIBUTION', color='#00D4FF', fontsize=10, fontweight='bold')
        for spine in ax2.spines.values():
            spine.set_color('#374151')
        
        ax3 = fig.add_subplot(gs[1, 0])
        ax3.set_facecolor('#111827')
        components = ['Database', 'API', 'File System', 'Network', 'Crypto']
        integrity_scores = [95, 98, 92, 99, 100]
        colors = ['#10B981' if s >= 95 else '#F59E0B' if s >= 80 else '#EF4444' for s in integrity_scores]
        bars = ax3.barh(components, integrity_scores, color=colors, edgecolor='#0A0E17')
        ax3.set_xlim(0, 100)
        ax3.set_title('SYSTEM INTEGRITY SCORES', color='#00D4FF', fontsize=10, fontweight='bold')
        ax3.set_xlabel('Integrity Score (%)', color='#9CA3AF')
        ax3.tick_params(colors='#9CA3AF')
        for i, (bar, score) in enumerate(zip(bars, integrity_scores)):
            ax3.text(score + 2, i, f'{score}%', va='center', fontsize=9, color='#9CA3AF')
        for spine in ax3.spines.values():
            spine.set_color('#374151')
        
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.set_facecolor('#111827')
        encryption_status = ['Encrypted', 'Decrypted', 'Archived', 'Backed Up']
        encryption_counts = [156, 23, 179, 179]
        colors = ['#10B981', '#EF4444', '#10B981', '#10B981']
        ax4.bar(encryption_status, encryption_counts, color=colors, edgecolor='#0A0E17')
        ax4.set_title('DATA SECURITY STATUS', color='#00D4FF', fontsize=10, fontweight='bold')
        ax4.set_ylabel('Records', color='#9CA3AF')
        ax4.tick_params(colors='#9CA3AF')
        for spine in ax4.spines.values():
            spine.set_color('#374151')
        
        plt.tight_layout()
        return fig
    except Exception as e:
        st.error(f"Security dashboard error: {e}")
        return None


def main():
    st.markdown("""
    <div class="main-header">
        <h1>🛰️ SENTRYGROUND-ZERO — MISSION CONTROL</h1>
        <p style="color: #9CA3AF; margin: 0; font-family: 'Courier New', monospace;">
            Secure Earth Observation & Space Surveillance Platform | ESA/NASA Compatible
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col_logo, col_status, col_time = st.columns([1, 2, 1])
    
    with col_status:
        st.markdown("""
        <div style="display: flex; gap: 2rem; margin-top: 1rem;">
            <div>
                <span style="color: #9CA3AF;">STATUS:</span>
                <span class="status-online"> ● OPERATIONAL</span>
            </div>
            <div>
                <span style="color: #9CA3AF;">CONSTELLATION:</span>
                <span style="color: #00D4FF;"> 10 NODES ACTIVE</span>
            </div>
            <div>
                <span style="color: #9CA3AF;">SECURITY:</span>
                <span class="status-online"> ● MAXIMUM</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_time:
        st.markdown(f"""
        <div style="text-align: right; color: #9CA3AF; font-family: 'Courier New', monospace;">
            {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
        </div>
        """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📡 TELEMETRY",
        "🌍 ORBITAL",
        "🔬 PHYSICS",
        "🪐 DEFENSE",
        "🔒 SECURITY",
        "📊 CATALOG",
        "⚙️ CONTROL"
    ])
    
    with tab1:
        meta, data = get_latest_product()
        
        if meta and data is not None:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("#### 📡 TELEMETRY DATA")
                
                if 'orbital_state' in meta:
                    orb = meta['orbital_state']
                    st.metric("Regime", orb.get('regime', 'N/A'))
                    st.metric("Altitude", f"{orb.get('current_alt_km', 0):.1f} km")
                    st.metric("Velocity", f"{orb.get('velocity_km_s', 0):.3f} km/s")
                    st.metric("Period", f"{orb.get('period_min', 0):.1f} min")
                
                st.markdown("---")
                st.markdown("#### 📋 METADATA")
                st.json(meta)
            
            with col2:
                profile = meta.get("mission_profile", "unknown")
                
                st.markdown(f"#### 🔭 PAYLOAD ANALYSIS — `{profile.upper()}`")
                
                fig, ax = plt.subplots(figsize=(12, 6))
                fig.patch.set_facecolor('#0A0E17')
                ax.set_facecolor('#111827')
                
                if profile == "exoplanet":
                    if len(data.shape) >= 2:
                        lightcurve = data[0, :, 0] if len(data.shape) > 2 else data[0, :]
                        ax.plot(lightcurve, color='#00D4FF', linewidth=1.5)
                    else:
                        ax.plot(data, color='#00D4FF', linewidth=1.5)
                    ax.set_title("KEPLERIAN EXOPLANET TRANSIT", color='#00D4FF', fontsize=12, fontweight='bold')
                    
                elif profile in ("earth", "earth_observation"):
                    if len(data.shape) >= 3:
                        ax.imshow(data[:, :, 0], cmap='viridis')
                    else:
                        ax.imshow(data, cmap='viridis')
                    ax.set_title("EARTH OBSERVATION MULTI-SPECTRAL", color='#00D4FF', fontsize=12, fontweight='bold')
                    ax.axis('off')
                    
                elif profile == "dark_matter":
                    if len(data.shape) >= 3:
                        im = ax.imshow(data[:, :, 0], cmap='magma')
                    else:
                        im = ax.imshow(data, cmap='magma')
                    ax.set_title("DARK MATTER HALO DENSITY", color='#00D4FF', fontsize=12, fontweight='bold')
                    ax.axis('off')
                    plt.colorbar(im, ax=ax, label='Relative Density')
                    
                elif profile == "black_hole":
                    if len(data.shape) >= 3:
                        im = ax.imshow(data[:, :, 0], cmap='inferno')
                    else:
                        im = ax.imshow(data, cmap='inferno')
                    ax.set_title("BLACK HOLE SHADOW + PHOTON RING", color='#00D4FF', fontsize=12, fontweight='bold')
                    ax.axis('off')
                    plt.colorbar(im, ax=ax, label='Intensity')
                    
                elif profile == "stellar":
                    if len(data.shape) >= 3:
                        im = ax.imshow(data[:, :, 0], cmap='plasma')
                    else:
                        im = ax.imshow(data, cmap='plasma')
                    ax.set_title("STELLAR PHOTOSPHERE ANALYSIS", color='#00D4FF', fontsize=12, fontweight='bold')
                    ax.axis('off')
                    plt.colorbar(im, ax=ax, label='Temperature')
                    
                elif profile == "gravitational_wave":
                    if len(data.shape) >= 2:
                        ax.plot(data[0, :, 0], color='#10B981', linewidth=1)
                    else:
                        ax.plot(data, color='#10B981', linewidth=1)
                    ax.set_title("GRAVITATIONAL WAVE CHIRP", color='#00D4FF', fontsize=12, fontweight='bold')
                    
                elif profile == "climate":
                    if len(data.shape) >= 2:
                        im = ax.imshow(data, cmap='coolwarm', aspect='auto')
                    else:
                        ax.plot(data, color='#3B82F6', linewidth=1.5)
                        ax.set_title("CLIMATE DATA TIME SERIES", color='#00D4FF', fontsize=12, fontweight='bold')
                        ax.axis('off')
                        plt.colorbar(im, ax=ax, label='Temperature Anomaly')
                else:
                    if len(data.shape) >= 3:
                        ax.imshow(data[:, :, 0], cmap='gray')
                    else:
                        ax.imshow(data, cmap='gray')
                    ax.set_title(f"{profile.upper()} ANALYSIS", color='#00D4FF', fontsize=12, fontweight='bold')
                    ax.axis('off')
                
                for spine in ax.spines.values():
                    spine.set_color('#374151')
                
                st.pyplot(fig)
        else:
            st.info("📡 Awaiting telemetry data from constellation...")
            st.markdown("""
            **Quick Start:**
            1. Attach to ground segment: `docker attach sentryground-zero-ground-segment-1`
            2. Login: `login admin admin123`
            3. Link satellite: `link sentry-deep-space`
            4. Scan: `scan`
            """)
    
    with tab2:
        st.markdown("#### 🌍 ORBITAL MECHANICS")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            try:
                from secure_eo_pipeline.physics import orbital_period, escape_velocity, orbital_velocity
                from secure_eo_pipeline.constellation_catalog import all_catalogs
                
                alt = st.number_input("Altitude (km)", 200, 40000, 400, step=100)
                
                a_km = alt + 6371
                period = orbital_period(a_km)
                v_orb = orbital_velocity(a_km, 0.0)
                v_esc = escape_velocity(a_km)
                
                st.metric("Orbital Period", f"{period/60:.1f} min")
                st.metric("Orbital Velocity", f"{v_orb:.2f} km/s")
                st.metric("Escape Velocity", f"{v_esc:.2f} km/s")
                
                fig_orb, ax_orb = plt.subplots(figsize=(6, 6))
                fig_orb.patch.set_facecolor('#0A0E17')
                draw_earth_orbital_diagram(ax_orb, 45.0, 0.0, 'LEO', alt)
                st.pyplot(fig_orb)
                
            except Exception as e:
                st.error(f"Orbital error: {e}")
        
        with col2:
            st.markdown("#### GROUND TRACK")
            
            try:
                from secure_eo_pipeline.constellation_catalog import satellites_from_environment
                
                sats = satellites_from_environment()
                if sats:
                    sat_names = [s.hostname for s in sats]
                    selected = st.selectbox("Select Satellite", sat_names)
                    
                    sat = next((s for s in sats if s.hostname == selected), None)
                    if sat and sat.orbital_elements:
                        lat = 45.0 + np.random.uniform(-20, 20)
                        lon = np.random.uniform(-180, 180)
                        
                        fig_map, ax_map = plt.subplots(figsize=(10, 5))
                        fig_map.patch.set_facecolor('#0A0E17')
                        draw_world_map(ax_map, lat, lon, 'LEO')
                        st.pyplot(fig_map)
                else:
                    st.info("No satellites configured")
                    
            except Exception as e:
                st.error(f"Map error: {e}")
    
    with tab3:
        st.markdown("#### 🔬 PHYSICS SIMULATIONS")
        
        sim_tabs = st.tabs([
            "🌡️ Climate",
            "🌌 Cosmology",
            "🌀 Gravitational Waves",
            "🪐 Exoplanets",
            "💎 Dark Matter"
        ])
        
        with sim_tabs[0]:
            st.markdown("**Global Climate Model — Energy Balance Simulation**")
            fig = draw_climate_simulation()
            if fig:
                st.pyplot(fig)
        
        with sim_tabs[1]:
            st.markdown("**Cosmological Parameters & Structure Formation**")
            fig = draw_cosmology_panel()
            if fig:
                st.pyplot(fig)
            
            try:
                from secure_eo_pipeline.physics import age_universe, bao_peak_position
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Age of Universe", f"{age_universe(0, n_steps=100):.2f} Gyr")
                with col2:
                    st.metric("BAO Peak", f"{bao_peak_position():.2f} Mpc")
                with col3:
                    st.metric("H₀", "67.4 km/s/Mpc")
            except:
                pass
        
        with sim_tabs[2]:
            st.markdown("**Gravitational Wave Detection — LIGO Analysis**")
            fig = draw_gravitational_waves()
            if fig:
                st.pyplot(fig)
            
            try:
                from secure_eo_pipeline.physics import chirp_mass, classify_cbc
                
                col1, col2 = st.columns(2)
                with col1:
                    m1 = st.number_input("Mass 1 (M☉)", 1.0, 100.0, 30.0)
                with col2:
                    m2 = st.number_input("Mass 2 (M☉)", 1.0, 100.0, 25.0)
                
                Mc = chirp_mass(m1, m2)
                cbc_type = classify_cbc(m1, m2)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Chirp Mass", f"{Mc:.2f} M☉")
                with col2:
                    st.metric("Source Type", cbc_type)
            except:
                pass
        
        with sim_tabs[3]:
            st.markdown("**Exoplanet Transit Detection**")
            fig = draw_exoplanet_transit()
            if fig:
                st.pyplot(fig)
        
        with sim_tabs[4]:
            st.markdown("**Dark Matter Distribution**")
            fig = draw_dark_matter_profile()
            if fig:
                st.pyplot(fig)
    
    with tab4:
        st.markdown("#### 🪐 PLANETARY DEFENSE — NEO TRACKING")
        
        fig = draw_planetary_defense()
        if fig:
            st.pyplot(fig)
        
        st.markdown("#### IMPACT SCENARIO ANALYSIS")
        try:
            from secure_eo_pipeline.physics import impact_energy_mt, palermo_scale, torino_scale
            
            col1, col2, col3 = st.columns(3)
            with col1:
                diameter = st.number_input("Asteroid Diameter (km)", 0.01, 10.0, 0.5, step=0.1)
            with col2:
                velocity = st.number_input("Impact Velocity (km/s)", 5.0, 30.0, 20.0, step=1.0)
            with col3:
                density = st.number_input("Density (g/cm³)", 1.0, 5.0, 2.5, step=0.1)
            
            energy = impact_energy_mt(diameter, density, velocity)
            ps = palermo_scale(1e-4, energy, 2460000)
            ts = torino_scale(energy, 1e-4)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Impact Energy", f"{energy:.2e} Mt")
            with col2:
                st.metric("Palermo Scale", f"{ps:.2f}")
            with col3:
                st.metric("Torino Scale", str(ts))
        except Exception as e:
            st.error(f"Error: {e}")
    
    with tab5:
        st.markdown("#### 🔒 CYBERSECURITY MONITORING")
        
        fig = draw_security_dashboard()
        if fig:
            st.pyplot(fig)
        
        st.markdown("#### SECURITY METRICS")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Active Sessions", "3")
        with col2:
            st.metric("Failed Logins (24h)", "7")
        with col3:
            st.metric("Threats Blocked", "12")
        with col4:
            st.metric("Encryption Status", "100%")
    
    with tab6:
        st.markdown("#### 📊 SATELLITE CATALOG")
        
        try:
            from secure_eo_pipeline.constellation_catalog import all_catalogs
            from secure_eo_pipeline.physics import orbital_regime
            
            catalogs = all_catalogs()
            
            search = st.text_input("Search satellites", "")
            
            for cat_name, sats in catalogs.items():
                filtered = [s for s in sats if search.lower() in s.title.lower() or 
                           search.lower() in s.hostname.lower()] if search else sats
                
                if filtered:
                    with st.expander(f"📡 {cat_name.replace('_', ' ').title()} ({len(filtered)} satellites)"):
                        for sat in filtered[:15]:
                            reg = "N/A"
                            if sat.orbital_elements:
                                a_km = getattr(sat.orbital_elements, 'semimajor_axis_km', 7000)
                                reg = orbital_regime(a_km) if a_km else "N/A"
                            
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                st.markdown(f"**{sat.title}**")
                                st.caption(f"Host: `{sat.hostname}` | Profile: {sat.mission_profile}")
                            with col2:
                                st.markdown(f"`{reg}`")
                            with col3:
                                status = "🟢" if reg != "N/A" else "⚪"
                                st.markdown(status)
        except Exception as e:
            st.error(f"Catalog error: {e}")
    
    with tab7:
        st.markdown("#### ⚙️ SYSTEM CONTROL")
        
        st.markdown("""
        <div style="background: #111827; padding: 1rem; border-radius: 8px; border: 1px solid #374151;">
            <h4 style="color: #00D4FF; margin-top: 0;">Mission Control Commands</h4>
            <p style="color: #9CA3AF;">Use the CLI to execute mission commands:</p>
            <code style="color: #10B981; display: block; margin: 0.5rem 0;">
                docker exec -it sentryground-zero-ground-segment-1 python main.py
            </code>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("#### AVAILABLE COMMANDS")
        commands_help = {
            "login": "Authenticate operator",
            "link": "Connect to satellite",
            "scan": "Acquire telemetry",
            "status": "View pipeline state",
            "orbit": "Show orbital info",
            "ids": "Security scan",
            "health": "System diagnostics",
        }
        
        for cmd, desc in commands_help.items():
            st.markdown(f"- **`{cmd}`** — {desc}")
    
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: #9CA3AF; padding: 1rem;">
        <p style="margin: 0; font-family: 'Courier New', monospace;">
            SENTRYGROUND-ZERO MISSION CONTROL | Version 1.0 | 
            <span style="color: #10B981;">● OPERATIONAL</span> | 
            Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
