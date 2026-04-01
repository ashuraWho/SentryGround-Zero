"""
Climate and Ocean Simulation Module for SentryGround-Zero.

Implements:
- Energy balance climate model (EBM)
- Ocean circulation (AMOC, thermohaline conveyor)
- Carbon cycle (atmosphere, ocean, biosphere)
- Atmospheric chemistry (O3, CO, CH4, aerosols)
- Ice sheet dynamics (Greenland, Antarctica)
- Climate feedback mechanisms
- Paleoclimate reconstruction

References:
- IPCC AR6 methodology
- NACCO/OCMIP ocean models
- BOX models (e.g., Joos et al. 1996)
- GLAC1D ice sheet simulations
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Callable
from enum import Enum
import numpy as np


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

G = 6.67430e-11
R_EARTH = 6.371e6
M_EARTH = 5.972e24
AU = 1.495978707e11
C_P = 1004.7
R_AIR = 287.05
G_GRAV = 9.81
SIGMA_SB = 5.670374419e-8
EPS_O3 = 0.35
DEBYE = 3.33564e-30
N_A = 6.02214076e23
KB = 1.380649e-23
ATM_PA = 101325.0
YEAR_S = 365.25 * 86400.0


# =============================================================================
# CLIMATE PARAMETERS
# =============================================================================

@dataclass(frozen=True)
class ClimateParams:
    """Standard climate parameters."""
    CO2_ppm: float = 415.0
    CH4_ppb: float = 1920.0
    N2O_ppb: float = 332.0
    forcing_CO2_wm2: float = 2.16
    forcing_CH4_wm2: float = 0.54
    forcing_N2O_wm2: float = 0.21
    aerosol_forcing_wm2: float = -1.3
    solar_constant_wm2: float = 1361.0
    albedo_surface: float = 0.30
    ocean_fraction: float = 0.71
    climate_sensitivity_k_per_wm2: float = 0.8
    equilibrium_climate_sensitivity_k: float = 3.0


@dataclass(frozen=True)
class OceanParams:
    """Ocean circulation parameters."""
    amoc_strength_sv: float = 17.0
    thermohaline_strength_sv: float = 15.0
    deep_water_formation_north: float = 15.0
    deep_water_formation_south: float = 8.0
    mixed_layer_depth_m: float = 50.0
    thermocline_depth_m: float = 1000.0
    deep_ocean_depth_m: float = 4000.0
    atlantic_fraction: float = 0.30
    pacific_fraction: float = 0.50


@dataclass(frozen=True)
class IceSheetParams:
    """Ice sheet parameters."""
    greenland_area_km2: float = 1.71e6
    greenland_volume_km3: float = 2.85e6
    antarctica_area_km2: float = 14.0e6
    antarctica_volume_km3: float = 26.5e6
    greenland_melt_mm_yr: float = 280.0
    antarctica_melt_mm_yr: float = 40.0
    sea_level_contribution_m_yr: float = 0.0


# =============================================================================
# RADIATIVE FORCING
# =============================================================================

def solar_radiative_input(S0: float = 1361.0, eccentricity: float = 0.0167) -> float:
    """Solar constant adjusted for orbital parameters."""
    return S0 * (1 - eccentricity**2) / (1 + eccentricity * math.cos(0))


def insolation(lat_deg: float, day_of_year: int, S0: float = 1361.0) -> float:
    """Insolation at surface (W/m^2)."""
    lat = math.radians(lat_deg)
    decl = 23.45 * math.sin(2 * math.pi * (284 + day_of_year) / 365.25)
    decl_rad = math.radians(decl)
    
    hour_angle = math.acos(-math.tan(lat) * math.tan(decl_rad))
    
    cos_zenith = math.sin(lat) * math.sin(decl_rad) + \
                  math.cos(lat) * math.cos(decl_rad) * math.cos(hour_angle)
    
    daily_insolation = (S0 / math.pi) * (1 - 0.3 * 0.7) * \
                       (hour_angle * math.sin(lat) * math.sin(decl_rad) + 
                        math.cos(lat) * math.cos(decl_rad) * math.sin(hour_angle))
    
    return max(daily_insolation, 0)


def planck_function(T_k: float, wavelength_um: float) -> float:
    """Blackbody radiation at wavelength (W/m^2/μm)."""
    h = 6.626e-34
    c = 3e8
    k = 1.381e-23
    
    wl_m = wavelength_um * 1e-6
    exp_term = (h * c) / (wl_m * k * T_k)
    
    if exp_term > 700:
        return 0.0
    
    B = (2 * h * c**2) / (wl_m**5) / (math.exp(exp_term) - 1)
    return B * 1e-6


def radiative_forcing_CO2(ppm_current: float, ppm_preindustrial: float = 280.0) -> float:
    """Radiative forcing from CO2 (W/m^2)."""
    if ppm_current <= 0:
        return 0.0
    ratio = ppm_current / ppm_preindustrial
    return 5.35 * math.log(ratio)


def radiative_forcing_CH4(ppb_current: float, ppb_preindustrial: float = 700.0) -> float:
    """Radiative forcing from CH4 (W/m^2)."""
    if ppb_current <= 0:
        return 0.0
    ratio = ppb_current / ppb_preindustrial
    return 0.036 * (math.sqrt(ratio) - 1)


def radiative_forcing_aerosol(
    SO2_emissions_tg_yr: float,
    BC_emissions_tg_yr: float,
    albedo_forcing: float = -0.1
) -> float:
    """Aerosol radiative forcing (W/m^2)."""
    sulfate_forcing = -0.4 * (SO2_emissions_tg_yr / 100)
    BC_forcing = 0.4 * (BC_emissions_tg_yr / 10)
    return sulfate_forcing + BC_forcing + albedo_forcing


def effective_radiative_forcing(
    CO2_ppm: float,
    CH4_ppb: float,
    N2O_ppb: float,
    aerosol_forcing: float,
    S0: float = 1361.0,
    eccentricity: float = 0.0167
) -> float:
    """Total effective radiative forcing (W/m^2)."""
    RF_CO2 = radiative_forcing_CO2(CO2_ppm)
    RF_CH4 = radiative_forcing_CH4(CH4_ppb)
    RF_N2O = radiative_forcing_N2O(N2O_ppb)
    
    S = solar_radiative_input(S0, eccentricity)
    RF_solar = 0.5 * (S - S0) / S0 * 3.71
    
    return RF_CO2 + RF_CH4 + RF_N2O + aerosol_forcing + RF_solar


def radiative_forcing_N2O(ppb_current: float, ppb_preindustrial: float = 270.0) -> float:
    """Radiative forcing from N2O (W/m^2)."""
    if ppb_current <= 0:
        return 0.0
    ratio = ppb_current / ppb_preindustrial
    return 0.12 * (math.sqrt(ratio) - 1)


def temperature_response(
    RF: float,
    params: ClimateParams,
    ocean_fraction: float = 0.71
) -> float:
    """Global mean temperature anomaly from radiative forcing (K)."""
    lambda_0 = params.climate_sensitivity_k_per_wm2
    ECS = params.equilibrium_climate_sensitivity_k
    
    f_ocean = 0.73
    f_land = 0.27
    
    lambda_ocean = lambda_0 / (1 + lambda_0 / 7.3)
    lambda_land = lambda_0 / (1 + lambda_0 / 2.0)
    
    lambda_eff = ocean_fraction * lambda_ocean + (1 - ocean_fraction) * lambda_land
    
    dT = lambda_eff * RF
    return dT


# =============================================================================
# ENERGY BALANCE MODEL
# =============================================================================

class EnergyBalanceModel:
    """Simple 2-layer energy balance model."""
    
    def __init__(
        self,
        C_atm: float = 7.3,
        C_ocn: float = 109.0,
        lambda_0: float = 0.8,
        gamma: float = 0.67
    ):
        self.C_atm = C_atm
        self.C_ocn = C_ocn
        self.lambda_0 = lambda_0
        self.gamma = gamma
        self.dT = 0.0
        self.dT_ocean = 0.0
    
    def step(self, RF: float, dt_years: float = 1.0):
        """Advance EBM by dt_years."""
        dT_eq = RF / self.lambda_0
        
        dT_dt = (RF - self.lambda_0 * self.dT - self.gamma * (self.dT - self.dT_ocean)) / self.C_atm
        dT_ocean_dt = self.gamma * (self.dT - self.dT_ocean) / self.C_ocn
        
        self.dT += dT_dt * dt_years
        self.dT_ocean += dT_ocean_dt * dt_years
    
    def radiative_imbalance(self) -> float:
        """Top-of-atmosphere radiative imbalance (W/m^2)."""
        return self.lambda_0 * self.dT


# =============================================================================
# OCEAN CIRCULATION (AMOC)
# =============================================================================

class OceanCirculation:
    """Atlantic Meridional Overturning Circulation model."""
    
    def __init__(
        self,
        M_0: float = 17.0,
        k: float = 0.3,
        alpha: float = 0.1,
        beta: float = 0.3
    ):
        self.M_0 = M_0
        self.M = M_0
        self.k = k
        self.alpha = alpha
        self.beta = beta
    
    def freshwater_forcing(
        self,
        Greenland_melt_sv: float,
        Antarctic_melt_sv: float,
        precipitation_change: float = 0.0
    ) -> float:
        """Freshwater forcing on AMOC (Sv)."""
        return Greenland_melt_sv / 1000 + Antarctic_melt_sv / 1000 + precipitation_change
    
    def step(
        self,
        dT_global: float,
        freshwater_forcing_sv: float,
        salinity_change_psu: float,
        dt_years: float = 1.0
    ):
        """Advance AMOC by dt_years."""
        dM_dt = (
            self.k * dT_global -
            self.alpha * freshwater_forcing_sv -
            self.beta * salinity_change_psu
        ) / 1000
        
        self.M = max(2.0, self.M + dM_dt * dt_years)
    
    def amoc_strength_sv(self) -> float:
        """Return current AMOC strength (Sv)."""
        return self.M
    
    def amoc_collapse_risk(self) -> float:
        """Probability of AMOC collapse (0-1)."""
        if self.M > 12:
            return 0.0
        elif self.M < 5:
            return 1.0
        else:
            return (12 - self.M) / 7


class ThermohalineConveyor:
    """Global thermohaline conveyor belt model."""
    
    def __init__(
        self,
        conveyor_strength_sv: float = 15.0,
        cold_water_formation_sv: float = 15.0
    ):
        self.strength = conveyor_strength_sv
        self.cold_water_formation = cold_water_formation_sv
        self.north_atlantic_temp_anomaly = 0.0
        self.deep_ocean_temp_anomaly = 0.0
    
    def conveyor_strength(
        self,
        dT_surface: float,
        dT_deep: float,
        salinity_anomaly_psu: float
    ) -> float:
        """Calculate conveyor strength (Sv)."""
        T_factor = 0.3 * (self.north_atlantic_temp_anomaly - dT_surface)
        S_factor = -0.2 * salinity_anomaly_psu
        D_factor = 0.1 * (dT_deep - self.deep_ocean_temp_anomaly)
        
        return max(5.0, self.strength + T_factor + S_factor + D_factor)
    
    def heat_transport(
        self,
        latitude_deg: float,
        strength_sv: float = 17.0
    ) -> float:
        """Meridional heat transport (PW)."""
        lat = abs(latitude_deg)
        max_transport = 1.3
        
        if lat < 20:
            return max_transport * (lat / 20)
        elif lat < 50:
            return max_transport * (1 - (lat - 20) / 80)
        else:
            return max_transport * 0.5 * (1 - (lat - 50) / 40)


# =============================================================================
# CARBON CYCLE
# =============================================================================

@dataclass
class CarbonReservoir:
    """Carbon reservoir in GtC."""
    atmosphere: float = 590.0
    land_biosphere: float = 2300.0
    surface_ocean: float = 1000.0
    deep_ocean: float = 38000.0


class CarbonCycle:
    """Simplified carbon cycle model (BOX model)."""
    
    def __init__(
        self,
        initial_C_atm: float = 590.0,
        initial_C_land: float = 2300.0,
        initial_C_ocean: float = 39000.0
    ):
        self.C_atm = initial_C_atm
        self.C_land = initial_C_land
        self.C_ocean = initial_C_ocean
        
        self.k_air_to_land = 0.20
        self.k_land_to_air = 0.18
        self.k_air_to_ocean = 0.10
        self.k_ocean_to_air = 0.08
        self.k_ocean_circulation = 0.02
    
    def atmospheric_co2_ppm(self) -> float:
        """Current atmospheric CO2 (ppm)."""
        preindustrial_ppm = 280.0
        preindustrial_GtC = 590.0
        return preindustrial_ppm * self.C_atm / preindustrial_GtC
    
    def airborne_fraction(self, emissions_GtC: float) -> float:
        """Airborne fraction of emissions."""
        return (self.k_air_to_land + self.k_air_to_ocean) * self.C_atm / 590.0
    
    def step(
        self,
        emissions_GtC_yr: float,
        land_use_change_GtC_yr: float,
        dt_years: float = 1.0
    ):
        """Advance carbon cycle by dt_years."""
        f_air_to_land = self.k_air_to_land * (self.C_atm / 590.0)
        f_land_to_air = self.k_land_to_air * (self.C_land / 2300.0)
        f_air_to_ocean = self.k_air_to_ocean * (self.C_atm / 590.0)
        f_ocean_to_air = self.k_ocean_to_air * (self.C_ocean / 39000.0)
        
        dC_atm = (f_land_to_air - f_air_to_land +
                  f_ocean_to_air - f_air_to_ocean +
                  emissions_GtC_yr + land_use_change_GtC_yr) * dt_years
        
        dC_land = (f_air_to_land - f_land_to_air - land_use_change_GtC_yr) * dt_years
        dC_ocean = (f_air_to_ocean - f_ocean_to_air) * dt_years
        
        self.C_atm = max(400.0, self.C_atm + dC_atm)
        self.C_land = max(1000.0, self.C_land + dC_land)
        self.C_ocean = max(35000.0, self.C_ocean + dC_ocean)
    
    def ocean_acidification(self, pH: float = 8.1, dCO2: float = 50.0) -> float:
        """Ocean pH change from CO2 uptake."""
        return -0.0004 * dCO2
    
    def carbon_sequestration(
        self,
        temperature_anomaly_k: float,
        vegetation_index: float = 0.5
    ) -> float:
        """Carbon sequestration feedback (GtC/yr)."""
        CO2_fertilization = 0.05 * (self.atmospheric_co2_ppm() - 280) / 280
        warming_released = -0.5 * temperature_anomaly_k
        dieback_factor = 0.3 if temperature_anomaly_k > 2.0 else 0.0
        
        return CO2_fertilization + warming_released - dieback_factor


# =============================================================================
# ATMOSPHERIC CHEMISTRY
# =============================================================================

@dataclass
class AtmosphericComposition:
    """Atmospheric composition."""
    CO2_ppm: float = 415.0
    CH4_ppb: float = 1920.0
    N2O_ppb: float = 332.0
    O3_du: float = 300.0
    CO_ppb: float = 100.0
    SO2_tg: float = 15.0
    BC_tg: float = 5.0
    PM25_ug_m3: float = 15.0


class AtmosphericChemistry:
    """Atmospheric chemistry and composition model."""
    
    def __init__(self):
        self.composition = AtmosphericComposition()
    
    def ozone_depletion(
        self,
        year: int,
        Cl_ppt: float = 530.0,
        bromine_ppt: float = 19.0
    ) -> float:
        """Stratospheric ozone depletion (Dobson Units)."""
        ODS_effect = (Cl_ppt / 530 + 2 * bromine_ppt / 19) * 0.3
        
        recovery_year = 2050
        if year > recovery_year:
            recovery_factor = min(1.0, (year - recovery_year) / 50)
        else:
            recovery_factor = 0.0
        
        return 300.0 * (1 - ODS_effect * (1 - recovery_factor))
    
    def methane_lifetime(
        self,
        temperature_k: float = 288.0,
        OH_concentration: float = 1.0
    ) -> float:
        """Methane atmospheric lifetime (years)."""
        base_lifetime = 9.1
        T_factor = 1 + 0.02 * (temperature_k - 288)
        OH_factor = 1 / OH_concentration
        
        return base_lifetime * T_factor * OH_factor
    
    def radiative_forcing_all(
        self,
        CO2_ppm: float,
        CH4_ppb: float,
        N2O_ppb: float,
        O3_du: float
    ) -> float:
        """Total radiative forcing from all species (W/m^2)."""
        RF_CO2 = radiative_forcing_CO2(CO2_ppm)
        RF_CH4 = radiative_forcing_CH4(CH4_ppb)
        RF_N2O = radiative_forcing_N2O(N2O_ppb)
        
        RF_O3 = 0.05 * (O3_du - 300) / 100
        
        return RF_CO2 + RF_CH4 + RF_N2O + RF_O3
    
    def aerosol_radiative_effect(
        self,
        SO2_tg: float,
        BC_tg: float,
        PM25_ug_m3: float = 15.0
    ) -> Dict[str, float]:
        """Aerosol direct and indirect effects (W/m^2)."""
        RF_sulfate = -0.4 * (SO2_tg / 100)
        RF_BC = 0.4 * (BC_tg / 10)
        RF_PM = -0.1 * (PM25_ug_m3 / 15)
        
        indirect_effect = -0.3 * (SO2_tg / 100)
        
        return {
            "direct": RF_sulfate + RF_BC + RF_PM,
            "indirect_cloud": indirect_effect,
            "total": RF_sulfate + RF_BC + RF_PM + indirect_effect
        }


# =============================================================================
# ICE SHEET DYNAMICS
# =============================================================================

class IceSheetModel:
    """Simplified ice sheet dynamics model."""
    
    def __init__(
        self,
        greenland_area_km2: float = 1.71e6,
        greenland_volume_km3: float = 2.85e6,
        antarctica_area_km2: float = 14.0e6,
        antarctica_volume_km3: float = 26.5e6
    ):
        self.greenland = {
            "area": greenland_area_km2,
            "volume": greenland_volume_km3,
            "basal_melt_m_yr": 0.0,
            "surface_melt_m_yr": 0.0,
            "accumulation_m_yr": 0.6,
            "flow_speed_m_yr": 100.0
        }
        
        self.antarctica = {
            "area": antarctica_area_km2,
            "volume": antarctica_volume_km3,
            "basal_melt_m_yr": 40.0,
            "surface_melt_m_yr": 0.0,
            "accumulation_m_yr": 0.15,
            "flow_speed_m_yr": 10.0,
            "WAIS_mass": 3.0e6
        }
    
    def sea_level_contribution(
        self,
        dT_k: float,
        ocean_warming_k: float = 0.0
    ) -> float:
        """Sea level contribution (m/yr)."""
        Greenland_sl = self.greenland_mass_balance(dT_k) / 3600
        Antarctica_sl = self.antarctica_mass_balance(dT_k, ocean_warming_k) / 3600
        
        return Greenland_sl + Antarctica_sl
    
    def greenland_mass_balance(self, dT_k: float) -> float:
        """Greenland mass balance (Gt/yr)."""
        melt_sensitivity = 28.0
        
        surface_balance = (
            self.greenland["accumulation_m_yr"] -
            self.greenland["surface_melt_m_yr"] -
            melt_sensitivity * max(0, dT_k)
        )
        
        calving_loss = self.greenland["flow_speed_m_yr"] * self.greenland["area"] * 1e-6
        
        return surface_balance * self.greenland["area"] * 1e-3 - calving_loss
    
    def antarctica_mass_balance(
        self,
        dT_k: float,
        ocean_warming_k: float
    ) -> float:
        """Antarctica mass balance (Gt/yr)."""
        melt_sensitivity = 4.0
        
        accumulation = self.antarctica["accumulation_m_yr"]
        basal_melt = self.antarctica["basal_melt_m_yr"] + melt_sensitivity * ocean_warming_k
        
        instability_factor = 1.0
        if ocean_warming_k > 1.0 and self.antarctica["WAIS_mass"] > 1e6:
            instability_factor = 1.5
        
        calving = self.antarctica["flow_speed_m_yr"] * instability_factor * self.antarctica["area"] * 1e-6
        
        return (accumulation - basal_melt) * self.antarctica["area"] * 1e-3 - calving
    
    def total_sea_level_rise_m(self, years: float) -> float:
        """Total committed sea level rise over years (m)."""
        rate_m_yr = self.sea_level_contribution(0.0, 0.0)
        return rate_m_yr * years


# =============================================================================
# CLIMATE FEEDBACKS
# =============================================================================

class ClimateFeedbacks:
    """Climate feedback mechanisms."""
    
    def __init__(self):
        self.feedbacks = {
            "water_vapor": 1.8,
            "lapse_rate": -0.8,
            "albedo": 0.3,
            "cloud": 0.7,
            "CO2_biogeochemical": -0.2,
            "CH4_permafrost": 0.3,
            "AMOC": -0.3,
            "ice_sheet": 0.3
        }
    
    def total_feedback_parameter(self, dT_k: float) -> float:
        """Total climate feedback parameter (W/m^2/K)."""
        water_vapor = self.feedbacks["water_vapor"] * (1 + 0.05 * dT_k)
        albedo = self.feedbacks["albedo"] * (1 - 0.1 * dT_k)
        
        permafrost = self.feedbacks["CH4_permafrost"] if dT_k > 2.0 else 0.0
        
        total = (water_vapor + self.feedbacks["lapse_rate"] +
                albedo + self.feedbacks["cloud"] +
                self.feedbacks["CO2_biogeochemical"] +
                permafrost + self.feedbacks["AMOC"] +
                self.feedbacks["ice_sheet"])
        
        return total
    
    def climate_sensitivity_parameter(self, dT_k: float) -> float:
        """Climate sensitivity parameter λ (K/(W/m^2))."""
        f = self.total_feedback_parameter(dT_k)
        return 1.0 / (3.71 - f)
    
    def effective_climate_sensitivity(self, dT_k: float) -> float:
        """Effective climate sensitivity (K)."""
        lambda_eff = self.climate_sensitivity_parameter(dT_k)
        return lambda_eff * 3.71


# =============================================================================
# CLIMATE SCENARIOS
# =============================================================================

class RCPScenario:
    """Representative Concentration Pathway scenarios."""
    
    RCP26 = {
        "name": "RCP 2.6",
        "description": "Strong mitigation",
        "CO2_2100_ppm": 490,
        "radiative_forcing_2100": 2.6,
        "temperature_change_2100": 1.5,
        "sea_level_rise_2100": 0.4
    }
    
    RCP45 = {
        "name": "RCP 4.5",
        "description": "Medium mitigation",
        "CO2_2100_ppm": 650,
        "radiative_forcing_2100": 4.5,
        "temperature_change_2100": 2.0,
        "sea_level_rise_2100": 0.5
    }
    
    RCP60 = {
        "name": "RCP 6.0",
        "description": "Stabilization",
        "CO2_2100_ppm": 850,
        "radiative_forcing_2100": 6.0,
        "temperature_change_2100": 2.5,
        "sea_level_rise_2100": 0.55
    }
    
    RCP85 = {
        "name": "RCP 8.5",
        "description": "High emissions",
        "CO2_2100_ppm": 1370,
        "radiative_forcing_2100": 8.5,
        "temperature_change_2100": 4.0,
        "sea_level_rise_2100": 0.75
    }


# =============================================================================
# CLIMATE SIMULATION
# =============================================================================

class ClimateSimulation:
    """Full climate simulation model."""
    
    def __init__(
        self,
        climate_params: ClimateParams = None,
        ocean_params: OceanParams = None,
        ice_params: IceSheetParams = None
    ):
        self.climate = climate_params or ClimateParams()
        self.ocean = ocean_params or OceanParams()
        self.ice = ice_params or IceSheetParams()
        
        self.ebm = EnergyBalanceModel()
        self.amoc = OceanCirculation(M_0=self.ocean.amoc_strength_sv)
        self.carbon = CarbonCycle()
        self.atmospheric_chem = AtmosphericChemistry()
        self.ice_model = IceSheetModel()
        self.feedbacks = ClimateFeedbacks()
        
        self.year = 2024
        self.dT_global = 0.0
        self.dT_ocean = 0.0
        self.sea_level_m = 0.0
        self.ph_ocean = 8.1
    
    def step(self, dt_years: float = 1.0):
        """Advance simulation by dt_years."""
        CO2_ppm = self.carbon.atmospheric_co2_ppm()
        
        CH4_ppb = self.climate.CH4_ppb + 10 * (self.year - 2020) / 10
        CH4_ppb = min(CH4_ppb, 3000)
        
        RF = effective_radiative_forcing(
            CO2_ppm,
            CH4_ppb,
            self.climate.N2O_ppb,
            self.climate.aerosol_forcing_wm2,
            self.climate.solar_constant_wm2
        )
        
        self.ebm.step(RF, dt_years)
        self.dT_global = self.ebm.dT
        self.dT_ocean = self.ebm.dT_ocean
        
        freshwater = self.ice_model.sea_level_contribution(self.dT_global)
        self.amoc.step(
            self.dT_global,
            freshwater * 1000,
            -0.05 * self.dT_global,
            dt_years
        )
        
        emissions = self._scenario_emissions()
        self.carbon.step(emissions, 0, dt_years)
        
        self.ph_ocean = self.carbon.ocean_acidification(
            self.ph_ocean,
            (CO2_ppm - 415) * 2
        )
        
        sl_rate = self.ice_model.sea_level_contribution(self.dT_global, self.dT_ocean)
        self.sea_level_m += sl_rate * dt_years
        
        self.year += dt_years
    
    def _scenario_emissions(self) -> float:
        """Get emissions for current scenario (GtC/yr)."""
        if self.year <= 2020:
            return 10.0
        elif self.year <= 2050:
            return 10.0 * (1 - (self.year - 2020) / 30)
        elif self.year <= 2100:
            return 3.0 * (1 - (self.year - 2050) / 50)
        else:
            return 1.0
    
    def get_state(self) -> Dict[str, float]:
        """Get current climate state."""
        return {
            "year": self.year,
            "CO2_ppm": self.carbon.atmospheric_co2_ppm(),
            "CH4_ppb": self.climate.CH4_ppb + 10 * (self.year - 2020) / 10,
            "dT_global": self.dT_global,
            "dT_ocean": self.dT_ocean,
            "AMOC_sv": self.amoc.amoc_strength_sv(),
            "sea_level_m": self.sea_level_m,
            "pH_ocean": self.ph_ocean,
            "RF_total": self.ebm.lambda_0 * self.dT_global
        }
