"""
Enhanced Dashboard for SentryGround-Zero.

Comprehensive visualization of:
- Satellite telemetry and orbital state
- Physics simulations (climate, cosmology, gravitational waves)
- Real-time metrics and statistics
- Multi-catalog satellite browser
"""

import streamlit as st
import os
import json
import time
import math
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

st.set_page_config(
    page_title="SentryGround-Zero Mission Control",
    layout="wide",
    page_icon="🛰️",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .css-1d391kg { background-color: #1E2530; }
    div[data-testid="stMetricValue"] { color: #00D4FF; }
    div[data-testid="stMetricLabel"] { color: #B0B0B0; }
</style>
""", unsafe_allow_html=True)

BASE_DIR = "simulation_data"
INGEST_DIR = os.path.join(BASE_DIR, "ingest_landing_zone")


def get_latest_product():
    """Reads the Landing Zone for the most recently downlinked satellite payload."""
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


def draw_world_map(ax, lat, lon, regime, trail_lats=None, trail_lons=None):
    """Draw world map with satellite position and ground track."""
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_xlabel('Longitude (°)')
    ax.set_ylabel('Latitude (°)')
    ax.set_title(f'Satellite Ground Track — {lat:.2f}°, {lon:.2f}°')
    ax.set_facecolor('#0E1117')
    ax.tick_params(colors='white')
    ax.grid(True, alpha=0.3, color='gray')
    
    if trail_lats is not None and trail_lons is not None:
        ax.plot(trail_lons, trail_lats, 'b-', alpha=0.3, linewidth=0.5)
    
    ax.plot(lon, lat, 'r*', markersize=15, label='Satellite')
    
    regime_colors = {
        'LEO': '#00FF00',
        'MEO': '#FFFF00',
        'GEO': '#FF6600',
        'HEO': '#FF00FF',
        'Lunar Transfer': '#00FFFF',
    }
    color = regime_colors.get(regime, '#FFFFFF')
    ax.plot(lon, lat, 'o', color=color, markersize=8, alpha=0.7)


def draw_orbital_diagram(ax, meta):
    """Draw simplified orbital mechanics diagram."""
    ax.set_aspect('equal')
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)
    ax.set_facecolor('#0E1117')
    ax.axis('off')
    ax.set_title('Orbital Geometry', color='white')
    
    from matplotlib.patches import Circle
    earth = Circle((0, 0), 0.15, color='#4169E1', alpha=0.8)
    ax.add_patch(earth)
    
    orb_state = meta.get('orbital_state', {})
    a = orb_state.get('semimajor_axis_km', 7000) / 42000
    e = orb_state.get('eccentricity', 0)
    i_deg = orb_state.get('inclination_deg', 0)
    
    theta = np.linspace(0, 2*np.pi, 100)
    r = a * (1 - e**2) / (1 + e * np.cos(theta))
    x_orbit = r * np.cos(theta)
    y_orbit = r * np.sin(theta)
    
    rotation = np.radians(i_deg)
    x_rot = x_orbit * np.cos(rotation) - y_orbit * np.sin(rotation)
    y_rot = x_orbit * np.sin(rotation) + y_orbit * np.cos(rotation)
    
    ax.plot(x_rot, y_rot, 'c-', alpha=0.5, linewidth=1, label='Orbit')
    
    x_sat = a * np.cos(0) * np.cos(rotation)
    y_sat = a * np.cos(0) * np.sin(rotation)
    
    ax.plot(x_sat, y_sat, 'r*', markersize=12)
    ax.plot([0, x_sat], [0, y_sat], 'r--', alpha=0.5)
    
    perigee = orb_state.get('perigee_km', 400)
    apogee = orb_state.get('apogee_km', 40000)
    ax.text(0.5, 1.2, f"Perigee: {perigee:.0f} km\nApogee: {apogee:.0f} km\nPeriod: {orb_state.get('period_min', 0):.1f} min",
             color='white', fontsize=8, transform=ax.transAxes)


def draw_climate_chart():
    """Draw climate simulation preview."""
    try:
        from secure_eo_pipeline.physics import ClimateSimulation, radiative_forcing_CO2
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.patch.set_facecolor('#0E1117')
        
        sim = ClimateSimulation()
        years = []
        temps = []
        co2_levels = []
        amoc_vals = []
        sea_levels = []
        
        for _ in range(100):
            sim.step()
            state = sim.get_state()
            years.append(state['year'])
            temps.append(state['dT_global'])
            co2_levels.append(state['CO2_ppm'])
            amoc_vals.append(state.get('AMOC_sv', 17))
            sea_levels.append(state.get('sea_level_m', 0) * 100)
        
        axes[0, 0].plot(years, temps, 'r-', linewidth=2)
        axes[0, 0].set_title('Global Temperature Anomaly', color='white')
        axes[0, 0].set_facecolor('#1E2530')
        axes[0, 0].set_xlabel('Year')
        axes[0, 0].set_ylabel('ΔT (K)')
        axes[0, 0].tick_params(colors='white')
        
        axes[0, 1].plot(years, co2_levels, 'g-', linewidth=2)
        axes[0, 1].set_title('CO2 Concentration', color='white')
        axes[0, 1].set_facecolor('#1E2530')
        axes[0, 1].set_xlabel('Year')
        axes[0, 1].set_ylabel('ppm')
        axes[0, 1].tick_params(colors='white')
        
        axes[1, 0].plot(years, amoc_vals, 'b-', linewidth=2)
        axes[1, 0].set_title('AMOC Strength', color='white')
        axes[1, 0].set_facecolor('#1E2530')
        axes[1, 0].set_xlabel('Year')
        axes[1, 0].set_ylabel('Sv')
        axes[1, 0].tick_params(colors='white')
        
        axes[1, 1].plot(years, sea_levels, 'm-', linewidth=2)
        axes[1, 1].set_title('Sea Level Rise', color='white')
        axes[1, 1].set_facecolor('#1E2530')
        axes[1, 1].set_xlabel('Year')
        axes[1, 1].set_ylabel('cm')
        axes[1, 1].tick_params(colors='white')
        
        for ax in axes.flat:
            for spine in ax.spines.values():
                spine.set_color('gray')
        
        plt.tight_layout()
        return fig
    except Exception as e:
        st.error(f"Climate simulation error: {e}")
        return None


def draw_cosmology_chart():
    """Draw cosmology simulation preview."""
    try:
        from secure_eo_pipeline.physics import CosmologyParams, Hubble, comoving_distance, power_spectrum_EH
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        fig.patch.set_facecolor('#0E1117')
        
        z_vals = np.linspace(0.01, 3, 100)
        H_vals = [Hubble(z) for z in z_vals]
        D_vals = [comoving_distance(z, n_steps=50) for z in z_vals]
        
        axes[0].plot(z_vals, H_vals, 'r-', linewidth=2)
        axes[0].set_title('Hubble Parameter H(z)', color='white')
        axes[0].set_facecolor('#1E2530')
        axes[0].set_xlabel('Redshift z')
        axes[0].set_ylabel('H(z) [km/s/Mpc]')
        axes[0].tick_params(colors='white')
        
        axes[1].plot(z_vals, D_vals, 'b-', linewidth=2)
        axes[1].set_title('Comoving Distance', color='white')
        axes[1].set_facecolor('#1E2530')
        axes[1].set_xlabel('Redshift z')
        axes[1].set_ylabel('D(z) [Mpc]')
        axes[1].tick_params(colors='white')
        
        for ax in axes:
            for spine in ax.spines.values():
                spine.set_color('gray')
        
        plt.tight_layout()
        return fig
    except Exception as e:
        st.error(f"Cosmology error: {e}")
        return None


def draw_planetary_defense():
    """Draw NEO catalog visualization."""
    try:
        from secure_eo_pipeline.physics import NEO_CATALOG, impact_energy_mt
        
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor('#0E1117')
        ax.set_facecolor('#1E2530')
        
        names = []
        sizes = []
        energies = []
        
        for sb in list(NEO_CATALOG.values())[:15]:
            names.append(sb.name.split()[-1] if ' ' in sb.name else sb.name)
            size = sb.physical.diameter_km * 1000
            sizes.append(size)
            energies.append(impact_energy_mt(sb.physical.diameter_km, 2.5, 20.0))
        
        colors = plt.cm.YlOrRd(np.linspace(0.2, 0.8, len(names)))
        
        bars = ax.barh(names, energies, color=colors)
        ax.set_xscale('log')
        ax.set_title('Near-Earth Objects: Impact Energy (Mt TNT)', color='white')
        ax.set_xlabel('Energy [Mt]')
        ax.tick_params(colors='white')
        ax.set_facecolor('#1E2530')
        
        for spine in ax.spines.values():
            spine.set_color('gray')
        
        plt.tight_layout()
        return fig
    except Exception as e:
        st.error(f"Planetary defense error: {e}")
        return None


def draw_gw_detection():
    """Draw gravitational wave visualization."""
    try:
        from secure_eo_pipeline.physics import generate_chirp_timeseries, ligo_noise_psd
        import numpy as np
        
        fig, axes = plt.subplots(2, 1, figsize=(10, 8))
        fig.patch.set_facecolor('#0E1117')
        
        m1, m2 = 30.0, 25.0
        h_plus, h_cross = generate_chirp_timeseries(m1, m2, 410.0, f_start=20.0, f_end=100.0)
        
        t = np.linspace(0, 1, len(h_plus))
        
        axes[0].plot(t, h_plus, 'g-', linewidth=1.5, label='h+')
        axes[0].set_title('GW150914-like Chirp Signal', color='white')
        axes[0].set_facecolor('#1E2530')
        axes[0].set_xlabel('Time [s]')
        axes[0].set_ylabel('Strain h(t)')
        axes[0].tick_params(colors='white')
        axes[0].legend(facecolor='#1E2530', labelcolor='white')
        
        f = np.linspace(20, 200, 1000)
        psd = ligo_noise_psd(f)
        axes[1].semilogy(f, np.sqrt(psd), 'r-', linewidth=1.5)
        axes[1].set_title('LIGO Noise PSD', color='white')
        axes[1].set_facecolor('#1E2530')
        axes[1].set_xlabel('Frequency [Hz]')
        axes[1].set_ylabel('Strain/√Hz')
        axes[1].tick_params(colors='white')
        
        for ax in axes:
            for spine in ax.spines.values():
                spine.set_color('gray')
        
        plt.tight_layout()
        return fig
    except Exception as e:
        st.error(f"GW error: {e}")
        return None


def draw_exoplanet_transit():
    """Draw exoplanet transit simulation."""
    try:
        from secure_eo_pipeline.physics import generate_transit_lightcurve, habitable_zone_Kopparapu
        
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor('#0E1117')
        ax.set_facecolor('#1E2530')
        
        time_arr, flux = generate_transit_lightcurve(
            time_hours=12.0, P_hours=5.0, Rp_Rs=0.1, a_Rs=10.0
        )
        
        ax.plot(time_arr, flux, 'c-', linewidth=1.5)
        ax.set_title('Exoplanet Transit Lightcurve', color='white')
        ax.set_xlabel('Time [hours]')
        ax.set_ylabel('Normalized Flux')
        ax.tick_params(colors='white')
        
        inner, outer = habitable_zone_Kopparapu(5778, 1.0)
        ax.axhspan(0.99, 1.01, alpha=0.3, color='green', label=f'HZ: {inner:.2f}-{outer:.2f} AU')
        ax.legend(facecolor='#1E2530', labelcolor='white')
        
        for spine in ax.spines.values():
            spine.set_color('gray')
        
        plt.tight_layout()
        return fig
    except Exception as e:
        st.error(f"Exoplanet error: {e}")
        return None


def main():
    st.title("🛰️ SentryGround-Zero: Mission Control Dashboard")
    st.markdown("Comprehensive satellite monitoring and scientific simulation platform.")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📡 Live Telemetry",
        "🌍 Orbital State",
        "🔬 Physics Sim",
        "🪐 Planetary Defense",
        "📊 Catalog"
    ])
    
    with tab1:
        meta, data = get_latest_product()
        
        if meta and data is not None:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### 📡 Active Downlink Metadata")
                st.json(meta)
                
                if 'orbital_state' in meta:
                    orb = meta['orbital_state']
                    st.markdown("### 🌍 Orbital State")
                    
                    metrics = {
                        "Regime": orb.get('regime', 'N/A'),
                        "Altitude": f"{orb.get('current_alt_km', 0):.1f} km",
                        "Velocity": f"{orb.get('velocity_km_s', 0):.3f} km/s",
                        "Period": f"{orb.get('period_min', 0):.1f} min",
                    }
                    
                    for key, value in metrics.items():
                        st.metric(key, value)
            
            with col2:
                profile = meta.get("mission_profile", "dark_matter")
                st.markdown(f"### 🔭 Payload Analysis: `{profile.upper()}`")
                
                fig, ax = plt.subplots(figsize=(10, 6))
                fig.patch.set_facecolor('#0E1117')
                ax.set_facecolor('#0E1117')
                
                if profile == "exoplanet":
                    lightcurve = data[0, :, 0]
                    ax.plot(lightcurve, color='cyan', linewidth=2)
                    ax.set_title("Keplerian Exoplanet Transit")
                elif profile in ("earth", "earth_observation"):
                    ax.imshow(data)
                    ax.set_title("Earth Observation Multi-Spectra")
                    ax.axis('off')
                elif profile == "stellar":
                    im = ax.imshow(data[:, :, 0], cmap='plasma')
                    ax.set_title("Stellar Photosphere")
                    ax.axis('off')
                    plt.colorbar(im, ax=ax)
                elif profile == "black_hole":
                    im = ax.imshow(data[:, :, 0], cmap='inferno')
                    ax.set_title("Black Hole Shadow + Photon Ring")
                    ax.axis('off')
                    plt.colorbar(im, ax=ax)
                elif profile == "gravitational_wave":
                    ax.plot(data[0, :, 0], color='lime', linewidth=1.5)
                    ax.set_title("Gravitational Wave Chirp")
                elif profile == "dark_matter":
                    im = ax.imshow(data[:, :, 0], cmap='magma')
                    ax.set_title("Dark Matter Halo Density")
                    ax.axis('off')
                    plt.colorbar(im, ax=ax)
                else:
                    im = ax.imshow(data[:, :, 0], cmap='gray')
                    ax.set_title(f"{profile.upper()} Analysis")
                    ax.axis('off')
                
                st.pyplot(fig)
        else:
            st.info("📡 Waiting for Mission Control to downlink a satellite payload...")
            st.markdown("""
            ### Quick Start
            1. Attach to ground segment: `docker attach sentryground-zero-ground-segment-1`
            2. Login: `login admin admin123`
            3. Link satellite: `link sentry-deep-space`
            4. Scan: `scan`
            """)
    
    with tab2:
        st.markdown("### 🌍 Orbital Mechanics")
        
        try:
            from secure_eo_pipeline.physics import orbital_period, escape_velocity
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                alt = st.number_input("Altitude (km)", 200, 40000, 400)
                period = orbital_period(alt + 6371)
                st.metric("Orbital Period", f"{period:.1f} s")
            
            with col2:
                v_orb = st.number_input("Orbital Velocity (km/s)", 3.0, 10.0, 7.6)
                st.metric("Circumference", f"{v_orb * period / 1000:.0f} km")
            
            with col3:
                v_esc = escape_velocity(alt + 6371)
                st.metric("Escape Velocity", f"{v_esc:.2f} km/s")
            
            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor('#0E1117')
            ax.set_facecolor('#1E2530')
            
            alts = np.linspace(200, 40000, 100)
            periods = [orbital_period(a + 6371) for a in alts]
            
            ax.plot(alts, [p/3600 for p in periods], 'b-', linewidth=2)
            ax.axvline(35786, color='orange', linestyle='--', label='GEO')
            ax.set_title('Orbital Period vs Altitude', color='white')
            ax.set_xlabel('Altitude (km)')
            ax.set_ylabel('Period (hours)')
            ax.legend(facecolor='#1E2530', labelcolor='white')
            ax.tick_params(colors='white')
            
            for spine in ax.spines.values():
                spine.set_color('gray')
            
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Orbital mechanics error: {e}")
    
    with tab3:
        st.markdown("### 🔬 Physics Simulations")
        
        sim_tabs = st.tabs(["Climate", "Cosmology", "Gravitational Waves", "Exoplanets"])
        
        with sim_tabs[0]:
            st.markdown("#### Climate Model (Energy Balance)")
            fig = draw_climate_chart()
            if fig:
                st.pyplot(fig)
        
        with sim_tabs[1]:
            st.markdown("#### Cosmological Parameters")
            fig = draw_cosmology_chart()
            if fig:
                st.pyplot(fig)
            
            try:
                from secure_eo_pipeline.physics import CosmologyParams, age_universe, bao_peak_position
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Age of Universe", f"{age_universe(0, n_steps=100):.1f} Gyr")
                with col2:
                    st.metric("BAO Peak", f"{bao_peak_position():.1f} Mpc")
                with col3:
                    st.metric("H0", "67.4 km/s/Mpc")
            except:
                pass
        
        with sim_tabs[2]:
            st.markdown("#### Gravitational Wave Detection")
            fig = draw_gw_detection()
            if fig:
                st.pyplot(fig)
            
            try:
                from secure_eo_pipeline.physics import chirp_mass, classify_cbc
                
                col1, col2 = st.columns(2)
                with col1:
                    m1 = st.number_input("Mass 1 (Msun)", 1.0, 100.0, 30.0)
                with col2:
                    m2 = st.number_input("Mass 2 (Msun)", 1.0, 100.0, 25.0)
                
                Mc = chirp_mass(m1, m2)
                st.metric("Chirp Mass", f"{Mc:.2f} Msun")
                st.metric("Source Type", classify_cbc(m1, m2))
            except:
                pass
        
        with sim_tabs[3]:
            st.markdown("#### Exoplanet Transit")
            fig = draw_exoplanet_transit()
            if fig:
                st.pyplot(fig)
    
    with tab4:
        st.markdown("### 🪐 Planetary Defense")
        
        fig = draw_planetary_defense()
        if fig:
            st.pyplot(fig)
        
        st.markdown("#### Impact Scenarios")
        try:
            from secure_eo_pipeline.physics import NEO_CATALOG, impact_energy_mt, palermo_scale, torino_scale
            
            col1, col2, col3 = st.columns(3)
            with col1:
                diameter = st.number_input("Asteroid Diameter (km)", 0.01, 10.0, 0.5)
            with col2:
                velocity = st.number_input("Impact Velocity (km/s)", 5.0, 30.0, 20.0)
            with col3:
                density = st.number_input("Density (g/cm³)", 1.0, 5.0, 2.5)
            
            energy = impact_energy_mt(diameter, density, velocity)
            ps = palermo_scale(1e-4, energy, 2460000)
            ts = torino_scale(energy, 1e-4)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Impact Energy", f"{energy:.1f} Mt")
            with col2:
                st.metric("Palermo Scale", f"{ps:.2f}")
            with col3:
                st.metric("Torino Scale", f"{ts}")
        except Exception as e:
            st.error(f"Error: {e}")
    
    with tab5:
        st.markdown("### 📊 Satellite Catalog")
        
        try:
            from secure_eo_pipeline.constellation_catalog import all_catalogs
            from secure_eo_pipeline.physics import orbital_regime
            
            catalogs = all_catalogs()
            
            search = st.text_input("Search satellites", "")
            
            for cat_name, sats in catalogs.items():
                filtered = [s for s in sats if search.lower() in s.title.lower()] if search else sats
                
                if filtered:
                    with st.expander(f"📡 {cat_name.replace('_', ' ').title()} ({len(filtered)} satellites)"):
                        for sat in filtered[:20]:
                            regime = "N/A"
                            if sat.orbital_elements:
                                a_km = getattr(sat.orbital_elements, 'semimajor_axis_km', 7000)
                                regime = orbital_regime(a_km) if a_km else "N/A"
                            
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.markdown(f"**{sat.title}**")
                                st.caption(f"Profile: {sat.mission_profile}")
                            with col2:
                                st.markdown(f"`{regime}`")
        except Exception as e:
            st.error(f"Catalog error: {e}")
    
    st.markdown("---")
    st.markdown(
        f"🛰️ SentryGround-Zero Mission Control | "
        f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


if __name__ == "__main__":
    main()
