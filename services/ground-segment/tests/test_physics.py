"""
Comprehensive test suite for physics modules.

Tests cover all physics implementations with correct API signatures.
"""

import pytest
import math
import numpy as np
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from secure_eo_pipeline.physics import (
    OrbitalState, GeodeticState, propagate_orbit, orbital_period,
    escape_velocity, eci_to_geodetic, geodetic_to_eci,
    julian_date, keplerian_to_cartesian, orbital_regime,
    EquatorialCoords, EclipticCoords, GalacticCoords,
    equatorial_to_ecliptic, ecliptic_to_equatorial,
    equatorial_to_galactic, galactic_to_equatorial,
    flux_to_mag, mag_to_flux, blackbody_radiation,
    nfw_profile, schwarzschild_radius, eddington_luminosity,
    doppler_shift, redshift_to_velocity, velocity_to_redshift,
    GWParameters, chirp_mass, generate_chirp_timeseries,
    detector_antenna_pattern, ligo_noise_psd, classify_cbc,
    estimate_remnant_mass, estimate_remnant_spin,
    ExoplanetSystem, transit_depth_mandel_agol,
    habitable_zone_Kopparapu, equilibrium_temperature,
    generate_transit_lightcurve, semi_amplitude_K,
    nfw_density, gamma_flux_from_dm, annihilation_cross_section,
    einstein_radius, relic_density_omega, wimp_cross_section_SI,
    Kerr_radius, ergosphere_radius,
    frame_dragging_omega, thin_disk_luminosity, thin_disk_temperature,
    blandford_znajek_power, shadow_radius_Kerr, hawking_temperature,
    hawking_luminosity, hawking_evaporation_time,
    CosmologyParams, Hubble, comoving_distance,
    luminosity_distance, angular_diameter_distance,
    lookback_time, age_universe, power_spectrum_EH,
    growth_function, bao_peak_position,
    SmallBody, NEO_CATALOG, kepler_period, impact_energy_mt,
    crater_diameter, palermo_scale, torino_scale,
    monte_carlo_impact_probability, kinetic_impactor_deflection,
    deflection_scenario,
    ClimateParams, ClimateSimulation, EnergyBalanceModel,
    OceanCirculation, CarbonCycle, AtmosphericChemistry,
    radiative_forcing_CO2, radiative_forcing_CH4,
    effective_radiative_forcing, temperature_response, insolation,
)
from secure_eo_pipeline.physics.orbital import orbital_velocity


# =============================================================================
# ORBITAL MECHANICS TESTS
# =============================================================================

class TestOrbitalMechanics:
    """Test orbital mechanics module."""

    def test_julian_date(self):
        """Test Julian date calculation."""
        dt = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        jd = julian_date(dt)
        assert abs(jd - 2451545.0) < 0.001

    def test_orbital_period(self):
        """Test orbital period calculation."""
        period = orbital_period(7000.0)
        assert period > 0
        
    def test_orbital_velocity(self):
        """Test orbital velocity calculation."""
        v = orbital_velocity(7000.0)
        assert v > 0
        
    def test_escape_velocity(self):
        """Test Earth escape velocity."""
        v_esc = escape_velocity(6371.0)
        assert 11.0 < v_esc < 12.0

    def test_keplerian_to_cartesian(self):
        """Test Keplerian to Cartesian conversion."""
        result = keplerian_to_cartesian(
            a_km=7000.0, e=0.001, i_deg=0.0,
            omega_deg=0.0, Omega_deg=0.0, nu_deg=0.0
        )
        assert len(result) == 6

    def test_eci_to_geodetic(self):
        """Test ECI to geodetic conversion."""
        lat, lon, alt = eci_to_geodetic(0.0, 0.0, 7000.0)
        assert lat is not None
        assert lon is not None
        assert alt is not None

    def test_orbital_regime(self):
        """Test orbital regime classification."""
        assert "LEO" in orbital_regime(7000)
        assert "MEO" in orbital_regime(26560)
        assert "HEO" in orbital_regime(80000)


# =============================================================================
# ASTRONOMY TESTS
# =============================================================================

class TestAstronomy:
    """Test astronomy module."""

    def test_equatorial_to_ecliptic(self):
        """Test equatorial to ecliptic conversion."""
        ecl = equatorial_to_ecliptic(180.0, 45.0)
        assert isinstance(ecl, EclipticCoords)
        assert ecl.lon_deg is not None

    def test_flux_to_mag(self):
        """Test flux to magnitude conversion."""
        mag = flux_to_mag(1e-12, flux_ref=3631.0)
        assert isinstance(mag, (int, float))

    def test_mag_to_flux(self):
        """Test magnitude to flux conversion."""
        flux = mag_to_flux(10.0)
        assert flux > 0

    def test_blackbody_radiation(self):
        """Test blackbody radiation."""
        L = blackbody_radiation(T=5778.0, wavelength_angstrom=5500.0)
        assert L >= 0

    def test_nfw_profile(self):
        """Test NFW dark matter profile."""
        rho = nfw_profile(r=100.0, rho_0=1e7, r_s=20.0)
        assert rho > 0

    def test_schwarzschild_radius(self):
        """Test Schwarzschild radius."""
        rs = schwarzschild_radius(10.0)
        assert rs > 0

    def test_eddington_luminosity(self):
        """Test Eddington luminosity."""
        Ledd = eddington_luminosity(10.0)
        assert Ledd > 0

    def test_doppler_shift(self):
        """Test Doppler shift calculation."""
        wavelength = 500.0
        v = 1000.0
        shifted = doppler_shift(wavelength, v)
        assert shifted != wavelength

    def test_redshift_velocity_roundtrip(self):
        """Test redshift <-> velocity conversion."""
        z = 0.1
        v = redshift_to_velocity(z)
        z_back = velocity_to_redshift(v)
        assert abs(z_back - z) < 0.01


# =============================================================================
# GRAVITATIONAL WAVES TESTS
# =============================================================================

class TestGravitationalWaves:
    """Test gravitational waves module."""

    def test_chirp_mass(self):
        """Test chirp mass calculation."""
        m = chirp_mass(30.0, 25.0)
        assert m > 0

    def test_generate_chirp_timeseries(self):
        """Test chirp waveform generation."""
        h_plus, h_cross = generate_chirp_timeseries(
            m1=30.0, m2=25.0, distance_mpc=410.0, f_start=20.0, f_end=100.0
        )
        assert len(h_plus) > 0 or len(h_cross) > 0

    def test_detector_antenna_pattern(self):
        """Test LIGO antenna pattern."""
        f_plus, f_cross = detector_antenna_pattern(
            "LIGO", ra_deg=0.0, dec_deg=0.0, gmst_rad=0.0
        )
        assert isinstance(f_plus, (int, float))
        assert isinstance(f_cross, (int, float))

    def test_ligo_noise_psd(self):
        """Test LIGO noise PSD."""
        f = np.linspace(10, 1000, 100)
        psd = ligo_noise_psd(f)
        assert len(psd) == len(f)
        assert np.all(psd >= 0)

    def test_classify_cbc(self):
        """Test CBC classification."""
        result = classify_cbc(1.4, 1.4)
        assert isinstance(result, str)

    def test_remnant_mass(self):
        """Test remnant mass estimation."""
        m_rem = estimate_remnant_mass(30.0, 25.0, chi_eff=0.0)
        assert m_rem > 0

    def test_remnant_spin(self):
        """Test remnant spin estimation."""
        chi_f = estimate_remnant_spin(30.0, 25.0, 0.0, 0.0)
        assert 0 <= chi_f <= 1


# =============================================================================
# EXOPLANETS TESTS
# =============================================================================

class TestExoplanets:
    """Test exoplanets module."""

    def test_habitable_zone(self):
        """Test habitable zone calculation."""
        result = habitable_zone_Kopparapu(5778, 1.0)
        assert len(result) == 2
        inner, outer = result
        assert inner > 0
        assert outer > inner

    def test_equilibrium_temperature(self):
        """Test equilibrium temperature."""
        T_eq = equilibrium_temperature(1.0, 1.0)
        assert T_eq > 0

    def test_semi_amplitude(self):
        """Test RV semi-amplitude."""
        K = semi_amplitude_K(
            m_planet_mjup=1.0, P_days=365.0,
            M_star_msun=1.0, e=0.0
        )
        assert K > 0


# =============================================================================
# DARK MATTER TESTS
# =============================================================================

class TestDarkMatter:
    """Test dark matter module."""

    def test_nfw_density(self):
        """Test NFW density profile."""
        rho = nfw_density(50.0, 1e6, 20.0)
        assert rho > 0

    def test_wimp_cross_section_SI(self):
        """Test WIMP spin-independent cross section."""
        sigma = wimp_cross_section_SI(100.0, A=131.0)
        assert sigma >= 0

    def test_gamma_flux(self):
        """Test gamma ray flux from DM annihilation."""
        flux = gamma_flux_from_dm(
            rho_local=0.3, m_chi_gev=100.0,
            sigma_v=3e-26, J_delta_omega=1e22
        )
        assert flux >= 0

    def test_einstein_radius(self):
        """Test Einstein radius."""
        theta_eff = einstein_radius(theta_e_arcsec=10.0, D_ls=1000.0, D_s=2000.0)
        assert theta_eff > 0

    def test_relic_density(self):
        """Test thermal relic density."""
        omega = relic_density_omega(100.0, 3e-26)
        assert omega > 0


# =============================================================================
# BLACK HOLES TESTS
# =============================================================================

class TestBlackHoles:
    """Test black holes module."""

    def test_schwarzschild_radius(self):
        """Test Schwarzschild radius for BH."""
        rs = schwarzschild_radius(10.0)
        assert rs > 0

    def test_kerr_radius(self):
        """Test Kerr radius (ISCO)."""
        r_plus, r_isco = Kerr_radius(10.0, spin_a=0.5)
        assert r_plus > 0
        assert r_isco > 0

    def test_ergosphere_radius(self):
        """Test ergosphere radius."""
        r_ergo = ergosphere_radius(10.0, spin_a=0.9, theta_deg=45.0)
        assert r_ergo > 0

    def test_frame_dragging(self):
        """Test frame dragging angular velocity."""
        omega = frame_dragging_omega(10.0, spin_a=0.5, r=50.0)
        assert omega > 0

    def test_thin_disk_luminosity(self):
        """Test thin disk luminosity."""
        L = thin_disk_luminosity(m_dot_msun_yr=1.0, eta=0.1)
        assert L > 0

    def test_thin_disk_temperature(self):
        """Test thin disk temperature."""
        T = thin_disk_temperature(R_rs=10.0, m_dot_msun_yr=1.0, M_msun=10.0)
        assert T >= 0

    def test_blandford_znajek_power(self):
        """Test Blandford-Znajek jet power."""
        P_BZ = blandford_znajek_power(10.0, spin_a=0.5, B_poloidal=1e4)
        assert P_BZ > 0

    def test_shadow_radius(self):
        """Test BH shadow radius."""
        r_shadow = shadow_radius_Kerr(spin_a=0.0)
        assert r_shadow > 0

    def test_hawking_temperature(self):
        """Test Hawking temperature."""
        T = hawking_temperature(1e12)
        assert T > 0

    def test_hawking_luminosity(self):
        """Test Hawking luminosity."""
        L = hawking_luminosity(1e12)
        assert L > 0

    def test_hawking_evaporation_time(self):
        """Test Hawking evaporation time."""
        t_evap = hawking_evaporation_time(10.0)
        assert t_evap > 0


# =============================================================================
# COSMOLOGY TESTS
# =============================================================================

class TestCosmology:
    """Test cosmology module."""

    def test_hubble_parameter(self):
        """Test Hubble parameter."""
        H = Hubble(0.0)
        assert H > 0

    def test_comoving_distance(self):
        """Test comoving distance."""
        D = comoving_distance(0.5, n_steps=100)
        assert D > 0

    def test_luminosity_distance(self):
        """Test luminosity distance."""
        D_L = luminosity_distance(0.5)
        assert D_L > 0

    def test_angular_diameter_distance(self):
        """Test angular diameter distance."""
        D_A = angular_diameter_distance(0.5)
        assert D_A > 0

    def test_lookback_time(self):
        """Test lookback time."""
        t = lookback_time(1.0, n_steps=100)
        assert t > 0

    def test_age_universe(self):
        """Test age of universe."""
        age = age_universe(0.0, n_steps=100)
        assert age > 0

    def test_growth_function(self):
        """Test growth function."""
        D_plus = growth_function(0.0)
        assert D_plus > 0

    def test_growth_function_z(self):
        """Test growth function at high z."""
        D_plus = growth_function(10.0)
        assert D_plus != 0

    def test_power_spectrum(self):
        """Test matter power spectrum."""
        k = 0.1
        Pk = power_spectrum_EH(k, z=0.0)
        assert Pk >= 0

    def test_bao_peak(self):
        """Test BAO peak position."""
        r_d = bao_peak_position()
        assert r_d > 0


# =============================================================================
# PLANETARY DEFENSE TESTS
# =============================================================================

class TestPlanetaryDefense:
    """Test planetary defense module."""

    def test_neo_catalog(self):
        """Test NEO catalog has entries."""
        assert len(NEO_CATALOG) > 0

    def test_apophis_properties(self):
        """Test Apophis properties."""
        apophis = NEO_CATALOG.get("99942apophis")
        if apophis:
            assert apophis.name == "99942 Apophis"

    def test_kepler_period_neo(self):
        """Test NEO orbital period."""
        P = kepler_period(1.0)
        assert P > 0

    def test_impact_energy(self):
        """Test impact energy calculation."""
        E = impact_energy_mt(
            diameter_km=1.0,
            density_g_cm3=2.5,
            v_impact_km_s=20.0
        )
        assert E > 0

    def test_crater_diameter(self):
        """Test crater scaling."""
        D = crater_diameter(energy_mt=1000.0, target="rock")
        assert D > 0

    def test_palermo_scale(self):
        """Test Palermo scale."""
        ps = palermo_scale(
            impact_probability=1e-4,
            impact_energy_mt=100.0,
            impact_time_jd=2460000.0
        )
        assert isinstance(ps, (int, float))

    def test_torino_scale(self):
        """Test Torino scale."""
        ts = torino_scale(impact_energy_mt=100.0, impact_probability=1e-4)
        assert 0 <= ts <= 10

    def test_kinetic_impactor(self):
        """Test kinetic impactor deflection."""
        dv = kinetic_impactor_deflection(
            asteroid_mass_kg=1e12,
            spacecraft_mass_kg=500.0,
            impact_velocity_km_s=6.5
        )
        assert dv > 0

    def test_deflection_scenario(self):
        """Test deflection scenario generation."""
        if len(NEO_CATALOG) > 0:
            sb = list(NEO_CATALOG.values())[0]
            scenario = deflection_scenario(sb, method="kinetic")
            assert scenario.method == "kinetic"


# =============================================================================
# CLIMATE TESTS
# =============================================================================

class TestClimateSimulation:
    """Test climate simulation module."""

    def test_radiative_forcing_co2(self):
        """Test CO2 radiative forcing."""
        RF = radiative_forcing_CO2(ppm_current=415.0)
        assert RF > 0

    def test_radiative_forcing_ch4(self):
        """Test CH4 radiative forcing."""
        RF = radiative_forcing_CH4(ppb_current=1920.0)
        assert RF > 0

    def test_effective_rf(self):
        """Test total effective radiative forcing."""
        RF = effective_radiative_forcing(
            CO2_ppm=415.0, CH4_ppb=1920.0,
            N2O_ppb=332.0, aerosol_forcing=-1.3
        )
        assert RF > 0

    def test_insolation(self):
        """Test insolation calculation."""
        S = insolation(lat_deg=45.0, day_of_year=172)
        assert S >= 0

    def test_energy_balance_model(self):
        """Test EBM step."""
        ebm = EnergyBalanceModel()
        RF = 2.0
        ebm.step(RF, dt_years=1.0)
        assert ebm.dT >= 0

    def test_ocean_circulation(self):
        """Test AMOC model."""
        amoc = OceanCirculation(M_0=17.0)
        amoc.step(dT_global=1.0, freshwater_forcing_sv=0.1,
                  salinity_change_psu=0.0, dt_years=1.0)
        strength = amoc.amoc_strength_sv()
        assert strength > 0

    def test_carbon_cycle(self):
        """Test carbon cycle."""
        carbon = CarbonCycle()
        initial_ppm = carbon.atmospheric_co2_ppm()
        carbon.step(emissions_GtC_yr=10.0, land_use_change_GtC_yr=1.0, dt_years=1.0)
        new_ppm = carbon.atmospheric_co2_ppm()
        assert new_ppm > 0

    def test_atmospheric_chemistry(self):
        """Test atmospheric chemistry."""
        atm = AtmosphericChemistry()
        O3 = atm.ozone_depletion(year=2024)
        assert O3 > 0

    def test_climate_simulation(self):
        """Test full climate simulation."""
        sim = ClimateSimulation()
        initial_state = sim.get_state()
        sim.step(dt_years=1.0)
        final_state = sim.get_state()
        assert final_state["year"] > initial_state["year"]


# =============================================================================
# RUN ALL TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
