"""
Stellar Evolution and Nucleosynthesis Module for SentryGround-Zero.

Implements:
- Stellar structure equations
- Main sequence evolution
- Post-main sequence evolution
- Nucleosynthesis (BBN, stellar)
- Type Ia and Type II supernovae
- Chemical enrichment history

References:
- Kippenhahn & Weigert - Stellar Structure and Evolution
- Woosley et al. - Supernova nucleosynthesis
- Pagel - Nucleosynthesis and Chemical Evolution
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict
import numpy as np


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

G = 6.67430e-11
M_SUN = 1.989e30
R_SUN = 6.96e8
L_SUN = 3.828e26
T_SUN = 5778.0
SIGMA_SB = 5.670374419e-8
KB = 1.380649e-23
HBAR = 1.054571817e-34
C = 299792458.0
MP = 1.67262192369e-27
MN = 1.67492749804e-27
ME = 9.1093837015e-31
ALPHA = 7.2973525693e-3
AU = 1.495978707e11
YEAR_S = 3.154e7


# =============================================================================
# STELLAR STRUCTURE
# =============================================================================

@dataclass
class StellarModel:
    """Stellar model parameters."""
    mass_msun: float
    radius_rsun: float
    luminosity_lsun: float
    temperature_k: float
    age_yr: float
    composition_x: float
    composition_y: float
    composition_z: float
    stage: str


@dataclass
class StellarTrack:
    """Evolutionary track."""
    masses: List[float]
    tracks: Dict[float, List[StellarModel]]


def opacity_electron_scattering(X: float) -> float:
    """Electron scattering opacity (cm^2/g)."""
    return 0.2 * (1 + X)


def opacity_Kramers(T: float, rho: float, kappa_0: float = 1e25) -> float:
    """Kramers opacity (bound-free + free-free)."""
    return kappa_0 * rho * T**(-3.5)


def opacity_COX(T: float, rho: float, X: float, Z: float) -> float:
    """Cox & Stewart opacity approximation."""
    kappa_es = 0.2 * (1 + X)
    
    kappa_bf = 4e25 * Z * (1 + X) * rho * T**(-3.5)
    
    kappa_ff = 1e24 * Z * (1 - Z) * rho * T**(-3.5)
    
    return kappa_es + kappa_bf + kappa_ff


def opacity_total(T: float, rho: float, X: float, Z: float) -> float:
    """Total opacity (cm^2/g)."""
    return opacity_COX(T, rho, X, Z)


def radiative_gradient(
    T: float,
    P: float,
    L: float,
    M: float,
    X: float,
    Z: float,
    mu: float = 0.6
) -> float:
    """Radiative temperature gradient."""
    kappa = opacity_total(T, P / (KB * T / (MP * mu)) / 1e3, X, Z)
    
    nabla_rad = 3 * kappa * L * L_SUN * P / \
                 (64 * math.pi * G * M * M_SUN * SIGMA_SB * T**4)
    return nabla_rad


def schmidt_criterion(T: float, P: float) -> float:
    """Schmidt criterion for convection."""
    delta = 1.0
    chi_T = 1.0
    chi_rho = 1.0
    nabla_ad = 2/5
    
    nabla_rad = radiative_gradient(T, P, 1.0, 1.0, 0.7, 0.02)
    
    return nabla_rad > nabla_ad


# =============================================================================
# MAIN SEQUENCE
# =============================================================================

def zero_age_main_sequence(mass_msun: float) -> Tuple[float, float, float]:
    """ZAMS properties from mass (polynomial fits)."""
    if mass_msun < 0.5:
        L = 0.23 * mass_msun**2.3
        R = 0.97 * mass_msun**0.8
        T = T_SUN * (L / R**2)**0.25
    elif mass_msun < 2.0:
        L = mass_msun**4.0
        R = mass_msun**0.8
        T = T_SUN * (L / R**2)**0.25
    elif mass_msun < 20:
        L = 1.4 * mass_msun**3.5
        R = 1.15 * mass_msun**0.75
        T = T_SUN * (L / R**2)**0.25
    else:
        L = 2.5 * mass_msun**3.0
        R = 1.5 * mass_msun**0.6
        T = T_SUN * (L / R**2)**0.25
    
    return L, R, T


def main_sequence_lifetime(
    mass_msun: float,
    L_lsun: float = None
) -> float:
    """Main sequence lifetime (years)."""
    if L_lsun is None:
        L_lsun, _, _ = zero_age_main_sequence(mass_msun)
    
    return 1e10 * mass_msun / L_lsun


def schonberg_chandrasekhar_limit(X: float = 0.7) -> float:
    """Schonberg-Chandrasekhar limit (solar masses)."""
    mu = 2.0 / (1 + 3 * X + 0.5)
    return 3.3 * mu**2


def opacity_limit_mass(X: float = 0.7) -> float:
    """Mass at which opacity dominates (solar masses)."""
    return 1.2 / (X + 0.001)


# =============================================================================
# POST-MAIN SEQUENCE
# =============================================================================

def hook_turnoff(mass_msun: float, Z: float = 0.02) -> float:
    """Hook effect turnoff mass (solar masses)."""
    return 1.1 + 0.5 * (Z / 0.02)


def helium_flash(M_He: float) -> float:
    """Helium ignition mass for degenerate core."""
    if M_He < 0.45:
        return 0.0
    return 0.46


def rgb_asymptotic_giant_branch(mass_msun: float) -> str:
    """Determine RGB or AGB."""
    if mass_msun < 0.5:
        return "He-WD"
    elif mass_msun < 2.0:
        return "RGB"
    elif mass_msun < 8.0:
        return "AGB"
    else:
        return "Super-AGB"


def tip_red_giant_branch(T_eff: float, L: float, M: float) -> float:
    """Luminosity at the tip of RGB (L_sun)."""
    return 2.5e4 * (M / 1.0)**(-0.3) * (T_eff / 3800)**(-2.5)


def horizontal_branch_luminosity(M_core: float, Z: float) -> float:
    """Horizontal branch luminosity (L_sun)."""
    return 50 * (M_core / 0.5)**1.5 * (Z / 0.02)**0.3


def agb_core_mass(mass_msun: float, Z: float) -> float:
    """Maximum core mass on AGB."""
    if mass_msun < 4.0:
        return 0.6 + 0.001 * Z / 0.02
    elif mass_msun < 8.0:
        return 0.8 + 0.003 * mass_msun + 0.001 * Z / 0.02
    else:
        return 1.05 + 0.002 * mass_msun


def carbon_ignition_mass(Z: float = 0.02) -> float:
    """Carbon ignition mass (solar masses)."""
    return 8.5 + 2.0 * (Z / 0.02)


# =============================================================================
# NUCLEOSYNTHESIS
# =============================================================================

def nuclear_reaction_rate(
    T9: float,
    sigma_v0: float = 1e-16,
    E_a_keV: float = 10.0
) -> float:
    """Thermonuclear reaction rate (cm^3/s/mol)."""
    kT = T9 * 1.15e7
    return sigma_v0 * (1 + E_a_keV / kT) * math.exp(-E_a_keV / kT)


def pp_chain_rate(T9: float) -> float:
    """PP-I chain rate (dominates below 1.5e7 K)."""
    psi = 1.0 + 0.1 * T9
    return 4.0e-25 * psi * T9**(-2/3) * math.exp(-3.38 / T9**(1/3))


def CNO_cycle_rate(T9: float) -> float:
    """CNO cycle rate (dominates above 1.5e7 K)."""
    return 4.0e-20 * T9**(-2/3) * math.exp(-15.2 / T9**(1/3))


def triple_alpha_rate(T9: float) -> float:
    """Triple-alpha reaction rate."""
    return 5.0e8 * T9**(-3) * math.exp(-4.4 / T9) * (1 + 0.05 * T9)


def alpha_capture_rate(T9: float, A: int) -> float:
    """Alpha capture rate on nucleus with mass number A."""
    return 1e18 * (A / 12.0)**2 * T9**(-2/3) * math.exp(-30.0 / T9**(1/3))


def radioactive_lifetime(A: int, Z: int) -> float:
    """Radioactive lifetime (seconds)."""
    lifetimes = {
        8: 122.0,
        12: 2.0,
        14: 7.0,
        20: 0.15,
        22: 0.35,
        26: 9.0e5,
        56: 6.5e6,
        57: 1.3e6,
        60: 2.2e5,
        138: 4.5e10,
        235: 2.2e16,
        238: 1.5e17
    }
    return lifetimes.get(A, 1e20) * YEAR_S


def big_bang_nucleosynthesis(
    eta: float = 6.1e-10,
    N_nu: float = 3.0
) -> Dict[str, float]:
    """BBN abundances as function of baryon-to-photon ratio."""
    Y_p = 0.2485 + 0.0016 * (eta / 6.1e-10 - 1) - 0.0014 * (N_nu - 3)
    
    D_H = 2.6 * (eta / 6.1e-10)**1.6 * 10**(-5 + 0.1 * (N_nu - 3))
    
    He3_D = D_H * 0.9
    
    Li7 = 4.3 * (eta / 6.1e-10)**2.0 * 10**(-10 - 0.1 * (N_nu - 3))
    
    return {
        "Y_p": Y_p,
        "D_H": D_H,
        "He3_D": He3_D,
        "Li7": Li7
    }


def supernova_yield_metal_poor(
    mass_msun: float,
    Z: float = 0.0
) -> Dict[str, float]:
    """Supernova yields for metal-poor stars (M_sun)."""
    M_rem = 1.4 if mass_msun < 25 else 2.0
    
    He = 0.1 * mass_msun
    C = 0.002 * mass_msun * (1 + 10 * Z)
    O = 0.05 * mass_msun * (1 + 5 * Z)
    Mg = 0.004 * mass_msun * (1 + 2 * Z)
    Si = 0.007 * mass_msun * (1 + Z)
    Fe = 0.0007 * mass_msun * (1 + 0.5 * Z)
    
    return {
        "He": He,
        "C": C,
        "O": O,
        "Mg": Mg,
        "Si": Si,
        "Fe": Fe,
        "mass_remnant": M_rem
    }


def supernova_yield_solar(
    mass_msun: float
) -> Dict[str, float]:
    """Supernova yields for solar metallicity (M_sun)."""
    if mass_msun < 12:
        return supernova_yield_metal_poor(mass_msun, Z=0.02)
    
    M_ej = mass_msun - 1.4
    
    yields = {
        "He": 0.15 * M_ej,
        "C": 0.01 * M_ej,
        "O": 0.15 * M_ej,
        "Ne": 0.04 * M_ej,
        "Mg": 0.02 * M_ej,
        "Si": 0.03 * M_ej,
        "Fe": 0.002 * M_ej + 0.07,
    }
    
    return yields


def type_ia_supernova_yield(
    mass_CO: float = 0.6,
    Z: float = 0.02
) -> Dict[str, float]:
    """Type Ia SN yields (M_sun)."""
    M_total = mass_CO + 0.3
    
    Fe_total = 0.6 * M_total
    Si_group = 0.15 * M_total
    intermediate = 0.15 * M_total
    unburned = 0.05 * M_total
    
    return {
        "Fe56": Fe_total,
        "Si": 0.6 * Si_group,
        "S": 0.25 * Si_group,
        "Ca": 0.15 * Si_group,
        "O": 0.5 * intermediate,
        "Mg": 0.3 * intermediate,
        "C": 0.2 * unburned,
        "He": unburned * 0.5
    }


# =============================================================================
# CHEMICAL EVOLUTION
# =============================================================================

class GalacticChemicalEvolution:
    """Simple Galactic chemical evolution model."""
    
    def __init__(
        self,
        infall_timescale: float = 8.0,
        star_formation_timescale: float = 4.0,
        outflow_factor: float = 0.3,
        effective_yield: float = 0.4
    ):
        self.tau_infall = infall_timescale * 1e9
        self.tau_star = star_formation_timescale * 1e9
        self.lambda_out = outflow_factor
        self.p_eff = effective_yield
        
        self.time = 0.0
        self.M_gas = 1e10
        self.M_stars = 0.0
        self.Z = 0.001
        self.age = 0.0
    
    def infall_rate(self, t_gyr: float) -> float:
        """Gas infall rate (M_sun/yr)."""
        return 5.0 * math.exp(-t_gyr / self.tau_infall * 1e9)
    
    def star_formation_rate(self) -> float:
        """SFR (M_sun/yr)."""
        return self.M_gas / self.tau_star
    
    def metallicity(self) -> float:
        """Gas phase metallicity Z."""
        if self.M_stars < 1e6:
            return 0.001
        return self.p_eff * self.M_stars / self.M_gas
    
    def step(self, dt_yr: float):
        """Advance by dt years."""
        t_gyr = self.age / 1e9
        
        infall = self.infall_rate(t_gyr) * dt_yr
        
        sfr = self.star_formation_rate() * dt_yr
        sfr = min(sfr, 0.5 * self.M_gas)
        
        mass_returned = 0.3 * sfr
        metals_ejected = self.Z * mass_returned
        
        outflow = self.lambda_out * sfr
        
        self.M_gas += infall - sfr + mass_returned - outflow
        self.M_gas = max(self.M_gas, 1e6)
        
        self.M_stars += sfr - mass_returned
        
        metals_added = 0.02 * sfr + metals_ejected - self.Z * outflow
        self.Z = max(1e-5, (self.M_gas * self.Z + metals_added) / self.M_gas)
        
        self.age += dt_yr
    
    def get_state(self) -> Dict[str, float]:
        """Get current state."""
        return {
            "age_gyr": self.age / 1e9,
            "M_gas": self.M_gas,
            "M_stars": self.M_stars,
            "Z": self.Z,
            "sfr": self.star_formation_rate(),
            "feh": math.log10(self.Z / 0.02)
        }


# =============================================================================
# STELLAR POPULATIONS
# =============================================================================

@dataclass
class StellarPopulation:
    """Stellar population properties."""
    name: str
    age_gyr: float
    metallicity_z: float
    alpha_enhancement: float = 0.0
    fraction_thin_disk: float = 0.0
    fraction_thick_disk: float = 0.0
    fraction_bulge: float = 0.0
    fraction_halo: float = 0.0


THIN_DISK = StellarPopulation(
    name="Thin Disk",
    age_gyr=5.0,
    metallicity_z=0.02,
    fraction_thin_disk=1.0
)

THICK_DISK = StellarPopulation(
    name="Thick Disk",
    age_gyr=10.0,
    metallicity_z=0.005,
    alpha_enhancement=0.3,
    fraction_thick_disk=1.0
)

HALO = StellarPopulation(
    name="Stellar Halo",
    age_gyr=12.0,
    metallicity_z=0.001,
    alpha_enhancement=0.4,
    fraction_halo=1.0
)

BULGE = StellarPopulation(
    name="Galactic Bulge",
    age_gyr=10.0,
    metallicity_z=0.03,
    alpha_enhancement=0.2,
    fraction_bulge=1.0
)


def population_feh_distribution(
    Z: float,
    population: StellarPopulation
) -> float:
    """Metallicity distribution function (G-dwarf problem)."""
    tau = population.age_gyr / 10.0
    
    sigma_z = 0.1 + 0.05 * tau
    mu_z = math.log10(population.metallicity_z / 0.02)
    
    return math.exp(-0.5 * ((Z - mu_z) / sigma_z)**2)


def isochrone_age_estimator(
    L: float,
    T_eff: float,
    Z: float
) -> float:
    """Estimate stellar age from position on HR diagram (Gyr)."""
    L_sun = L_SUN
    T_sun = T_SUN
    
    if T_eff < 5000:
        return 10.0
    elif L > 100 * L_sun:
        return 0.1
    elif L < 0.1 * L_sun and T_eff > 6000:
        return 12.0
    else:
        t_ref = 5.0
        dL = abs(math.log10(L / L_sun))
        dT = abs(math.log10(T_eff / T_sun))
        return t_ref * (1 + 0.5 * dL + 0.3 * dT)
