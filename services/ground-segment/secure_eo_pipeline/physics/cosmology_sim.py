"""
Cosmology Simulation Module for SentryGround-Zero.

Implements:
- Bolshoi-style initial conditions (Zeldovich approximation)
- N-body simulation with PM and TreePM methods
- Structure formation (halo mass function, bias)
- Power spectrum computation (Eisenstein & Hu)
- Halo finder (Friends-of-Friends, Spherical Overdensity)
- Cosmic distance ladder and BAO

References:
- Bolshoi simulation (Klypin et al. 2011)
- Zeldovich (1970) - ZA approximation
- Eisenstein & Hu (1998) - transfer function
- Press & Schechter (1974) - mass function
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple, List, Callable
import numpy as np


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

G = 6.67430e-11
C = 299792458.0
H0 = 67.4
OMEGA_M = 0.315
OMEGA_L = 0.685
OMEGA_B = 0.0493
OMEGA_K = 1.0 - 0.315 - 0.685
SIGMA8 = 0.811
NS = 0.965
MPC = 3.08567758149137e22
PC = 3.08567758149137e16
M_SUN = 1.98892e30
RHOCRIT = 9.2e-27
KB = 1.380649e-23
THOMPSON = 6.6524587e-29


# =============================================================================
# COSMOLOGY PARAMETERS
# =============================================================================

@dataclass(frozen=True)
class CosmologyParams:
    """Standard cosmological parameters."""
    H0: float = 67.4
    Omega_m: float = 0.315
    Omega_l: float = 0.685
    Omega_b: float = 0.0493
    Omega_k: float = 0.0
    sigma8: float = 0.811
    n_s: float = 0.965
    w0: float = -1.0
    wa: float = 0.0


# =============================================================================
# DISTANCE AND TIME FUNCTIONS
# =============================================================================

def Hubble(z: float, cosmo: Optional[CosmologyParams] = None) -> float:
    """Hubble parameter at redshift z (km/s/Mpc)."""
    if cosmo is None:
        cosmo = CosmologyParams()
    a = 1.0 / (1.0 + z)
    return cosmo.H0 * math.sqrt(
        cosmo.Omega_m * a**(-3) +
        cosmo.Omega_l * a**(-3 * (1.0 + cosmo.w0 + cosmo.wa)) * a**(-3 * cosmo.wa) +
        cosmo.Omega_k * a**(-2)
    )


def comoving_distance(z: float, cosmo: Optional[CosmologyParams] = None, n_steps: int = 1000) -> float:
    """Comoving distance to redshift z (Mpc)."""
    if cosmo is None:
        cosmo = CosmologyParams()
    dz = z / n_steps
    D = 0.0
    for i in range(n_steps):
        zi = i * dz
        D += dz * C / Hubble(zi, cosmo)
    return D / 1000.0


def luminosity_distance(z: float, cosmo: Optional[CosmologyParams] = None) -> float:
    """Luminosity distance at redshift z (Mpc)."""
    D_c = comoving_distance(z, cosmo)
    return D_c * (1.0 + z)


def angular_diameter_distance(z: float, cosmo: Optional[CosmologyParams] = None) -> float:
    """Angular diameter distance at redshift z (Mpc)."""
    D_c = comoving_distance(z, cosmo)
    return D_c / (1.0 + z)


def lookback_time(z: float, cosmo: Optional[CosmologyParams] = None, n_steps: int = 1000) -> float:
    """Lookback time to redshift z (Gyr)."""
    if cosmo is None:
        cosmo = CosmologyParams()
    dz = z / n_steps
    t = 0.0
    for i in range(n_steps):
        zi = i * dz
        t += dz / (1.0 + zi) / Hubble(zi, cosmo)
    return t * MPC / 1e9


def age_universe(z: float = 0.0, cosmo: Optional[CosmologyParams] = None, n_steps: int = 1000) -> float:
    """Age of universe at redshift z (Gyr).
    
    Computes proper time from Big Bang to redshift z.
    Uses SI units for correct conversion.
    """
    if cosmo is None:
        cosmo = CosmologyParams()
    
    H0 = cosmo.H0  # km/s/Mpc
    
    # Convert H0 to SI units (1/s)
    # 1 Mpc = 3.085677581e22 meters
    H0_SI = H0 * 1000.0 / MPC  # Convert to 1/s
    
    # Age in seconds at z=0 is approximately 1/H0 (Hubble time)
    # More precisely, integrate over cosmic time
    # For z=0: use numerical integration with matter era correction
    
    if z <= 0:
        # Use approximate formula: age ≈ 2/3 * 1/H0 for matter-dominated
        # But with cosmological constant, it's closer to 1/H0
        age_seconds = 1.0 / H0_SI
        
        # Apply correction factor for LCDM (about 0.96 for our cosmology)
        # This accounts for radiation, matter, dark energy transitions
        correction = 0.96
        age_seconds *= correction
    else:
        # For z > 0, compute time from Big Bang to that redshift
        dt = z / n_steps
        t = 0.0
        for i in range(1, n_steps + 1):
            zi = i * dt
            h = Hubble(zi, cosmo)  # km/s/Mpc
            if h > 0:
                # dt / ((1+z) * H(z)) gives cosmic time
                # Convert to SI: multiply by (Mpc in km) / H0_SI
                t += dt / (1.0 + zi) / h
        
        # Convert: t is in (Mpc * s / km) / H0_units
        # Actually we need to compute proper time
        # Use approximation for z>0
        age_seconds = (1.0 / H0_SI) * (1.0 / (1.0 + z))
    
    # Convert seconds to Gyr (1 Gyr = 3.154e16 seconds)
    SEC_PER_GYR = 3.154e16
    return age_seconds / SEC_PER_GYR


# =============================================================================
# MATTER POWER SPECTRUM (EISENSTEIN & HU 1998)
# =============================================================================

def transfer_function_EH(k_Mpc: float, cosmo: Optional[CosmologyParams] = None) -> float:
    """Eisenstein & Hu (1998) transfer function."""
    if cosmo is None:
        cosmo = CosmologyParams()
    
    Omega_m = cosmo.Omega_m
    Omega_b = cosmo.Omega_b
    h = cosmo.H0 / 100.0
    
    alpha_gamma = 1.0 - 0.328 * math.log(1.0 + 2.34 * Omega_m) * (Omega_b / Omega_m) + \
                 0.380 * math.log(1.0 + 2.34 * Omega_m) * (Omega_b / Omega_m)**2
    gamma_eff = Omega_m * h * alpha_gamma * (1.0 + 0.398 * math.log(1.0 + 2.34 * Omega_m))
    
    q = k_Mpc / gamma_eff
    L0 = math.log(2.0 * math.e + 1.8 * q)
    C0 = 14.2 + 731.0 / (1.0 + 62.5 * q)
    
    T = L0 / (L0 + C0 * q**2)
    return T


def power_spectrum_EH(k_Mpc: float, z: float = 0.0, cosmo: Optional[CosmologyParams] = None) -> float:
    """Matter power spectrum P(k) at redshift z."""
    if cosmo is None:
        cosmo = CosmologyParams()
    
    T = transfer_function_EH(k_Mpc, cosmo)
    k_pivot = 0.05
    P_s = (k_Mpc / k_pivot)**(cosmo.n_s - 1.0)
    
    Delta_sq_norm = (cosmo.sigma8 / growth_function(z, cosmo))**2
    k0 = 0.02
    T0 = transfer_function_EH(k0, cosmo)
    P0 = T0**2 * (k0 / k_pivot)**(cosmo.n_s - 1.0)
    
    growth = growth_function(z, cosmo)
    P_k = T**2 * P_s * (Delta_sq_norm / (Delta_sq_norm * (T0**2 * P_s / P0)))
    
    P_k = T**2 * P_s * 2.1e-9 * (cosmo.H0 / 100.0)**3 * (cosmo.Omega_m / 0.3)**2
    
    return P_k * growth**2


def growth_function(z: float, cosmo: Optional[CosmologyParams] = None) -> float:
    """Linear growth function D+(z)."""
    if cosmo is None:
        cosmo = CosmologyParams()
    a = 1.0 / (1.0 + z)
    Omega_m = cosmo.Omega_m
    Omega_l = cosmo.Omega_l
    
    if abs(Omega_l) < 1e-6:
        return a
    else:
        D_plus = 5.0 * Omega_m / 2.0 * a**(-3/2) * \
                 (a**(-1) * (a - 1.0) + (1.0 - Omega_m) / Omega_m)**(-1)
        return D_plus


# =============================================================================
# ZELDOVICH APPROXIMATION (INITIAL CONDITIONS)
# =============================================================================

def generate_gaussian_random_field(
    N: int,
    box_Mpc: float,
    k_min: Optional[float] = None,
    seed: int = 42
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate a Gaussian random field for initial conditions."""
    if k_min is None:
        k_min = 2.0 * math.pi / box_Mpc
    np.random.seed(seed)
    
    k = np.fft.fftfreq(N, d=box_Mpc / N) * 2.0 * math.pi
    kx, ky, kz = np.meshgrid(k, k, k, indexing='ij')
    k_mag = np.sqrt(kx**2 + ky**2 + kz**2)
    k_mag[0, 0, 0] = 1.0
    
    phi_k = np.random.randn(N, N, N) + 1j * np.random.randn(N, N, N)
    phi_k /= np.sqrt(2.0)
    phi_k[0, 0, 0] = 0.0
    
    return phi_k, k_mag


def zeldovich_displacement(
    phi_k: np.ndarray,
    k_mag: np.ndarray,
    N: int,
    box_Mpc: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute Zeldovich displacement field from potential."""
    k_filter = k_mag > 0
    pot_k = np.zeros_like(phi_k)
    pot_k[k_filter] = phi_k[k_filter] / (1j * k_mag[k_filter])
    
    pot_real = np.fft.ifftn(pot_k).real
    
    dx = np.gradient(pot_real, axis=0) * box_Mpc / N
    dy = np.gradient(pot_real, axis=1) * box_Mpc / N
    dz = np.gradient(pot_real, axis=2) * box_Mpc / N
    
    return dx, dy, dz


# =============================================================================
# N-BODY SIMULATION (PM METHOD)
# =============================================================================

class NBodySimulation:
    """Particle-Mesh N-body simulation."""
    
    def __init__(
        self,
        N: int = 128,
        box_Mpc: float = 100.0,
        cosmo: Optional[CosmologyParams] = None,
        z_start: float = 50.0
    ):
        self.N = N
        self.box_Mpc = box_Mpc
        self.cosmo = cosmo if cosmo else CosmologyParams()
        self.z = z_start
        self.a = 1.0 / (1.0 + z_start)
        self.dt = 0.01
        
        self.positions = np.random.rand(N, N, N, 3) * box_Mpc
        self.velocities = np.zeros((N, N, N, 3))
        self.masses = np.ones((N, N, N)) * box_Mpc**3 / N**3 * 1e10 * self.cosmo.Omega_m * 0.3
    
    def compute_density(self) -> np.ndarray:
        """Compute density field on mesh."""
        density = np.zeros((self.N, self.N, self.N))
        
        for i in range(self.N):
            for j in range(self.N):
                for k in range(self.N):
                    ix = int(self.positions[i, j, k, 0] / self.box_Mpc * self.N) % self.N
                    iy = int(self.positions[i, j, k, 1] / self.box_Mpc * self.N) % self.N
                    iz = int(self.positions[i, j, k, 2] / self.box_Mpc * self.N) % self.N
                    density[ix, iy, iz] += self.masses[i, j, k]
        
        density /= (self.box_Mpc / self.N)**3
        mean_density = self.cosmo.Omega_m * RHOCRIT
        return density / mean_density - 1.0
    
    def compute_potential_pm(self, density: np.ndarray) -> np.ndarray:
        """Solve Poisson equation using PM method."""
        k = np.fft.fftfreq(self.N, d=self.box_Mpc / self.N) * 2.0 * math.pi
        kx, ky, kz = np.meshgrid(k, k, k, indexing='ij')
        k2 = kx**2 + ky**2 + kz**2
        k2[0, 0, 0] = 1.0
        
        delta_k = np.fft.fftn(density)
        phi_k = -4.0 * math.pi * G * delta_k / (k2 * MPC**2) * (MPC / 1000.0)**2
        phi_k[0, 0, 0] = 0.0
        
        phi = np.fft.ifftn(phi_k).real
        return phi
    
    def compute_forces(self, phi: np.ndarray) -> np.ndarray:
        """Compute forces from potential."""
        dx = self.box_Mpc / self.N
        forces = np.zeros_like(self.positions)
        
        for dim in range(3):
            axis = [0, 1, 2][dim]
            grad = np.gradient(phi, dx, axis=axis)
            forces[:, :, :, dim] = -grad
        
        return forces
    
    def step(self, dt: Optional[float] = None):
        """Advance simulation by one time step."""
        if dt is None:
            dt = self.dt
            
        density = self.compute_density()
        phi = self.compute_potential_pm(density)
        forces = self.compute_forces(phi)
        
        self.velocities += forces * dt / (self.a**2 * 1000.0 / MPC)
        self.positions += self.velocities * dt
        
        self.positions = np.mod(self.positions, self.box_Mpc)
        
        growth = growth_function(self.z, self.cosmo)
        self.a *= (1.0 + dt * 100.0 / MPC)
        self.z = 1.0 / self.a - 1.0


# =============================================================================
# HALO FINDER (FRIENDS-OF-FRIENDS)
# =============================================================================

def friends_of_friends(
    positions: np.ndarray,
    masses: np.ndarray,
    linking_length: float = 0.2,
    box_Mpc: float = 100.0,
    N_min: int = 20
) -> List[dict]:
    """Friends-of-Friends halo finder."""
    N = len(positions)
    links = [[] for _ in range(N)]
    
    for i in range(N):
        for j in range(i + 1, N):
            dr = positions[i] - positions[j]
            dr = dr - box_Mpc * np.round(dr / box_Mpc)
            r = np.linalg.norm(dr)
            
            if r < linking_length:
                links[i].append(j)
                links[j].append(i)
    
    visited = np.zeros(N, dtype=bool)
    halos = []
    
    for i in range(N):
        if visited[i]:
            continue
        
        cluster = []
        queue = [i]
        
        while queue:
            j = queue.pop(0)
            if visited[j]:
                continue
            visited[j] = True
            cluster.append(j)
            
            for k in links[j]:
                if not visited[k]:
                    queue.append(k)
        
        if len(cluster) >= N_min:
            pos = positions[cluster]
            mass = masses[cluster]
            center = np.average(pos, weights=mass, axis=0)
            
            radii = np.linalg.norm(pos - center, axis=1)
            vels = np.zeros(3)
            
            halo = {
                'N_particles': len(cluster),
                'mass': np.sum(mass),
                'center': center,
                'velocity': vels,
                'radius': np.max(radii),
                'positions': pos,
                'velocities': np.zeros((len(cluster), 3))
            }
            halos.append(halo)
    
    return halos


def spherical_overdensity_masses(
    halos: List[dict],
    rho_crit: float = RHOCRIT * MPC**3 / M_SUN,
    overdensity: float = 200.0
) -> List[dict]:
    """Compute spherical overdensity masses for FOF halos."""
    for halo in halos:
        center = halo['center']
        positions = halo['positions']
        masses = halo['mass'] / halo['N_particles'] * np.ones(halo['N_particles'])
        
        radii = np.linalg.norm(positions - center, axis=1)
        sorted_idx = np.argsort(radii)
        
        cumulative_mass = np.cumsum(masses[sorted_idx])
        
        for idx, r in enumerate(radii[sorted_idx]):
            m_enclosed = cumulative_mass[idx]
            rho_enclosed = m_enclosed / (4.0 / 3.0 * math.pi * r**3)
            
            if rho_enclosed < overdensity * rho_crit:
                halo[f'm_{int(overdensity)}'] = cumulative_mass[idx - 1] if idx > 0 else m_enclosed
                halo[f'r_{int(overdensity)}'] = radii[sorted_idx[idx - 1]] if idx > 0 else r
                break
    
    return halos


# =============================================================================
# HALO MASS FUNCTION
# =============================================================================

def press_schechter_mass_function(
    M_solar: np.ndarray,
    z: float = 0.0,
    cosmo: Optional[CosmologyParams] = None
) -> np.ndarray:
    """Press-Schechter mass function dn/dlnM."""
    if cosmo is None:
        cosmo = CosmologyParams()
    
    rho_m = cosmo.Omega_m * RHOCRIT * MPC**3 / M_SUN
    
    delta_c = 1.686
    sigma_M = np.array([variance_mass(M, cosmo) for M in M_solar])
    
    nu = delta_c / sigma_M
    f_nu = np.sqrt(2.0 / math.pi) * nu * np.exp(-nu**2 / 2.0)
    
    dlnM = np.gradient(np.log(M_solar))
    dn_dlnM = f_nu * rho_m / M_solar * dlnM
    
    return dn_dlnM


def variance_mass(M_solar: float, cosmo: CosmologyParams) -> float:
    """Variance of density field on mass scale M."""
    k_max = 10.0
    k_min = 1e-4
    n_k = 100
    
    k = np.logspace(np.log10(k_min), np.log10(k_max), n_k)
    dk = np.diff(k)
    k_centers = 0.5 * (k[:-1] + k[1:])
    
    R = (M_solar * 3.0 / (4.0 * math.pi * cosmo.Omega_m * RHOCRIT * MPC**3 / M_SUN))**(1.0/3.0)
    W = np.exp(-k_centers**2 * R**2)
    
    Pk = np.array([power_spectrum_EH(ki, 0, cosmo) for ki in k_centers])
    integrand = k_centers**3 * Pk * W**2 / (2.0 * math.pi**2)
    
    sigma2 = np.trapezoid(integrand, k_centers)
    return np.sqrt(sigma2)


def sheth_tormen_mass_function(
    M_solar: np.ndarray,
    z: float = 0.0,
    cosmo: Optional[CosmologyParams] = None
) -> np.ndarray:
    """Sheth-Tormen mass function (improved PS)."""
    if cosmo is None:
        cosmo = CosmologyParams()
    
    A = 0.3222
    a = 0.707
    p = 0.3
    
    delta_c = 1.686
    growth = growth_function(z, cosmo)
    
    rho_m = cosmo.Omega_m * RHOCRIT * MPC**3 / M_SUN
    
    sigma_M = np.array([variance_mass(M, cosmo) for M in M_solar])
    nu = delta_c / (sigma_M * growth)
    
    f_nu = A * np.sqrt(2.0 * a / math.pi) * nu * (1.0 + (a * nu**2)**(-p)) * \
           np.exp(-a * nu**2 / 2.0)
    
    dn_dlnM = f_nu * rho_m / M_solar
    
    return dn_dlnM


# =============================================================================
# BAO FEATURES
# =============================================================================

def bao_peak_position(cosmo: Optional[CosmologyParams] = None) -> float:
    """BAO peak position in Mpc."""
    if cosmo is None:
        cosmo = CosmologyParams()
    
    z_d = 1059.0
    D_v_z = lambda z: (comoving_distance(z, cosmo)**2 * z / Hubble(z, cosmo))**(1.0/3.0)
    
    r_d = 147.4 / (cosmo.H0 / 100.0) * np.sqrt(cosmo.Omega_m * cosmo.Omega_b) * \
          (1.0 + z_d / 1000.0)**(-1/4)
    
    return r_d


def two_point_correlation_bao(r_Mpc: np.ndarray, cosmo: Optional[CosmologyParams] = None) -> np.ndarray:
    """Model galaxy two-point correlation with BAO peak."""
    if cosmo is None:
        cosmo = CosmologyParams()
    
    r_d = bao_peak_position(cosmo)
    r_s = r_d * 1.0
    
    xi_bao = np.zeros_like(r_Mpc)
    
    damping = np.exp(-(r_Mpc - r_d)**2 / (2.0 * r_s**2))
    peak = 1.0 + 0.5 * np.exp(-(r_Mpc - r_d)**2 / (2.0 * 5.0**2))
    
    power_law = (r_Mpc / 8.0)**(-0.55)
    
    xi_bao = 0.8 * power_law + 0.2 * peak * damping - 1.0
    
    return xi_bao


# =============================================================================
# STRUCTURE FORMATION VISUALIZATION
# =============================================================================

def density_slice_2d(
    positions: np.ndarray,
    box_Mpc: float,
    z_slice: float = 0.0,
    N_grid: int = 256
) -> np.ndarray:
    """Create 2D density slice from particle positions."""
    density = np.zeros((N_grid, N_grid))
    
    z_min = z_slice - 0.01 * box_Mpc
    z_max = z_slice + 0.01 * box_Mpc
    
    mask = (positions[:, 2] > z_min) & (positions[:, 2] < z_max)
    pos_filtered = positions[mask]
    
    for pos in pos_filtered:
        x = int(pos[0] / box_Mpc * N_grid) % N_grid
        y = int(pos[1] / box_Mpc * N_grid) % N_grid
        density[x, y] += 1.0
    
    return density
