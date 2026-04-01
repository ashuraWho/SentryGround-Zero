"""
Enhanced Animation System for SentryGround-Zero Mission Control
Supports three visual styles:
- SCIENTIFIC: Detailed physics annotations, data readouts, scientific accuracy
- MISSION_CONTROL: Terminal aesthetic, HUD elements, cyberpunk colors  
- CINEMATIC: Dramatic lighting, smooth camera, movie-quality effects
"""

import os
import math
from datetime import datetime
from typing import Tuple, Optional, List
import numpy as np

os.environ['FORCE_COLOR'] = '1'

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Circle, Wedge, Rectangle, FancyBboxPatch
from matplotlib.collections import PatchCollection, LineCollection
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.lines import Line2D
from mpl_toolkits.axes_grid1 import make_axes_locatable

plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.unicode_minus'] = False


class AnimationStyle:
    """Animation style configuration"""
    SCIENTIFIC = "scientific"
    MISSION_CONTROL = "mission_control"
    CINEMATIC = "cinematic"


class EnhancedAnimator:
    """Enhanced animator with multiple visual styles"""
    
    def __init__(self, style: str = AnimationStyle.MISSION_CONTROL):
        self.style = style
        self.plot_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plots")
        os.makedirs(self.plot_dir, exist_ok=True)
        
        self.style_configs = {
            AnimationStyle.SCIENTIFIC: {
                'bg_color': '#f5f5f5',
                'text_color': '#1a1a1a',
                'accent': '#0066cc',
                'grid_alpha': 0.3,
                'font_size': 8,
                'show_data': True,
                'show_equations': True,
            },
            AnimationStyle.MISSION_CONTROL: {
                'bg_color': '#0a0a12',
                'text_color': '#00ff88',
                'accent': '#00ffcc',
                'grid_alpha': 0.15,
                'font_size': 7,
                'show_data': True,
                'show_equations': False,
                'scanlines': True,
            },
            AnimationStyle.CINEMATIC: {
                'bg_color': '#000005',
                'text_color': '#ffffff',
                'accent': '#ff6b35',
                'grid_alpha': 0.1,
                'font_size': 10,
                'show_data': False,
                'show_equations': False,
                'glow': True,
            }
        }
        
        self.config = self.style_configs.get(style, self.style_configs[AnimationStyle.MISSION_CONTROL])
    
    def _setup_figure(self, figsize: Tuple[int, int] = (12, 8), 
                     projection: Optional[str] = None) -> Tuple[plt.Figure, plt.Axes]:
        """Setup figure with style configuration"""
        fig = plt.figure(figsize=figsize, facecolor=self.config['bg_color'])
        
        if projection == '3d':
            ax = fig.add_subplot(111, projection='3d')
        else:
            ax = fig.add_subplot(111)
        
        ax.set_facecolor(self.config['bg_color'])
        
        if self.style == AnimationStyle.MISSION_CONTROL:
            ax.spines['bottom'].set_color(self.config['text_color'])
            ax.spines['top'].set_color(self.config['bg_color'])
            ax.spines['left'].set_color(self.config['text_color'])
            ax.spines['right'].set_color(self.config['bg_color'])
            ax.tick_params(colors=self.config['text_color'], labelsize=self.config['font_size'])
            ax.xaxis.label.set_color(self.config['text_color'])
            ax.yaxis.label.set_color(self.config['text_color'])
            ax.title.set_color(self.config['accent'])
        
        return fig, ax
    
    def _add_hud_elements(self, ax: plt.Axes, title: str, 
                         subtitle: Optional[str] = None) -> None:
        """Add HUD elements for mission control style"""
        if self.style != AnimationStyle.MISSION_CONTROL:
            return
        
        ax.text(0.02, 0.98, f"MISSION: SENTRY-GROUND-ZERO", transform=ax.transAxes,
                fontsize=8, color=self.config['accent'], fontfamily='monospace',
                verticalalignment='top', alpha=0.8)
        
        ax.text(0.02, 0.94, f"TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                transform=ax.transAxes, fontsize=7, color=self.config['text_color'],
                fontfamily='monospace', verticalalignment='top', alpha=0.6)
        
        ax.text(0.02, 0.90, f"MODE: {self.style.upper()}", 
                transform=ax.transAxes, fontsize=7, color=self.config['text_color'],
                fontfamily='monospace', verticalalignment='top', alpha=0.6)
        
        ax.text(0.98, 0.02, "● REC", transform=ax.transAxes,
               fontsize=8, color='#ff0044', fontfamily='monospace',
               verticalalignment='bottom', horizontalalignment='right')
    
    def _add_scientific_annotations(self, ax: plt.Axes, 
                                    equations: List[str]) -> None:
        """Add scientific equations and annotations"""
        if self.style != AnimationStyle.SCIENTIFIC:
            return
        
        for i, eq in enumerate(equations):
            ax.text(0.02, 0.08 - i*0.04, eq, transform=ax.transAxes,
                    fontsize=7, color=self.config['text_color'],
                    fontfamily='DejaVu Sans Mono', verticalalignment='bottom',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    def create_orbital_animation(self, alt_km: float = 400, frames: int = 120,
                                 style: Optional[str] = None) -> str:
        """Create detailed orbital mechanics animation"""
        style = style or self.style
        config = self.style_configs.get(style, self.style_configs[AnimationStyle.MISSION_CONTROL])
        
        fig, ax = plt.subplots(figsize=(12, 10), facecolor=config['bg_color'])
        ax.set_facecolor(config['bg_color'])
        
        R_EARTH = 6371
        GM = 3.986e14
        
        a_km = alt_km + R_EARTH
        period = 2 * math.pi * math.sqrt(a_km**3 / GM)
        v_orb = math.sqrt(GM / a_km) / 1000
        
        theta = np.linspace(0, 2*np.pi, frames)
        
        r_earth = R_EARTH
        r_orbit = a_km
        
        def update(frame):
            ax.clear()
            ax.set_xlim(-r_orbit*1.4, r_orbit*1.4)
            ax.set_ylim(-r_orbit*1.4, r_orbit*1.4)
            ax.set_aspect('equal')
            
            if style == AnimationStyle.MISSION_CONTROL:
                ax.add_patch(Circle((0, 0), r_earth, facecolor='#001122', 
                                   edgecolor='#00ff88', linewidth=2, alpha=0.8))
                
                for i in range(3):
                    ring_r = r_earth + 1000 + i * 2000
                    if ring_r < r_orbit:
                        circle = plt.Circle((0, 0), ring_r, fill=False, 
                                           color='#00ff88', alpha=0.1, linewidth=1)
                        ax.add_patch(circle)
            else:
                ax.add_patch(Circle((0, 0), r_earth, facecolor='#4488cc', 
                                   edgecolor='#88ccff', linewidth=2))
                
                theta_grid = np.linspace(0, 2*np.pi, 24)
                for lat in [0, 30, 60]:
                    r_lat = r_earth * np.cos(np.radians(lat))
                    z_lat = r_earth * np.sin(np.radians(lat))
                    ax.plot(r_lat * np.cos(theta_grid), r_lat * np.sin(theta_grid),
                           '--', color='gray', alpha=0.3, linewidth=0.5)
            
            orbit_path = plt.Circle((0, 0), r_orbit, fill=False, 
                                    color=config['accent'], linewidth=2, linestyle='--')
            ax.add_patch(orbit_path)
            
            theta_curr = theta[frame]
            sat_x = r_orbit * np.cos(theta_curr)
            sat_y = r_orbit * np.sin(theta_curr)
            
            if style == AnimationStyle.CINEMATIC:
                trail_len = 20
                for t in range(max(0, frame-trail_len), frame):
                    trail_alpha = 0.3 * (t - max(0, frame-trail_len) + 1) / trail_len
                    trail_x = r_orbit * np.cos(theta[t])
                    trail_y = r_orbit * np.sin(theta[t])
                    ax.scatter(trail_x, trail_y, c='#ff6b35', s=20, alpha=trail_alpha)
            
            ax.scatter([sat_x], [sat_y], c=config['accent'], s=150, 
                      edgecolors='white', linewidth=2, zorder=10)
            
            vel_x = -v_orb * np.sin(theta_curr)
            vel_y = v_orb * np.cos(theta_curr)
            ax.annotate('', xy=(sat_x + vel_x*50, sat_y + vel_y*50), 
                       xytext=(sat_x, sat_y),
                       arrowprops=dict(arrowstyle='->', color=config['accent'], lw=2))
            
            ax.set_title(f'Orbital Mechanics Simulation\nAltitude: {alt_km} km | '
                        f'Period: {period/60:.1f} min | Velocity: {v_orb:.2f} km/s',
                        fontsize=12, color=config['text_color'])
            ax.set_xlabel('X (km)', fontsize=10, color=config['text_color'])
            ax.set_ylabel('Y (km)', fontsize=10, color=config['text_color'])
            ax.grid(True, alpha=config['grid_alpha'], color=config['text_color'])
            ax.axis('on')
            
            if style == AnimationStyle.SCIENTIFIC:
                info_text = (f"Semi-major axis: a = {a_km:.0f} km\n"
                            f"Orbital period: T = {period:.0f} s\n"
                            f"Orbital velocity: v = {v_orb:.3f} km/s\n"
                            f"Escape velocity: v_esc = {v_orb*1.414:.3f} km/s")
                ax.text(0.98, 0.98, info_text, transform=ax.transAxes,
                        fontsize=8, color=config['text_color'], verticalalignment='top',
                        horizontalalignment='right',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
            
            self._add_hud_elements(ax, "ORBITAL SIMULATION")
        
        anim = FuncAnimation(fig, update, frames=frames, interval=50, repeat=True)
        
        filename = f"orbital_{style}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gif"
        filepath = os.path.join(self.plot_dir, filename)
        anim.save(filepath, writer='pillow', fps=20)
        plt.close(fig)
        return filepath
    
    def create_gw_animation(self, m1: float = 30, m2: float = 25, 
                           distance_mpc: float = 100, frames: int = 150,
                           style: Optional[str] = None) -> str:
        """Create detailed gravitational wave merger animation"""
        style = style or self.style
        config = self.style_configs.get(style, self.style_configs[AnimationStyle.MISSION_CONTROL])
        
        fig = plt.figure(figsize=(14, 6), facecolor=config['bg_color'])
        
        ax1 = fig.add_subplot(121, facecolor=config['bg_color'])
        ax2 = fig.add_subplot(122, facecolor=config['bg_color'])
        
        G = 6.67430e-11
        c = 299792458.0
        MSUN = 1.989e30
        MPC = 3.086e22
        
        Mc = ((m1 * m2) / (m1 + m2)**2)**0.2 * (m1 + m2)
        Mc_SI = Mc * MSUN
        D_L = distance_mpc * MPC
        
        f_start = 20.0
        f_end = 512.0
        f_coal = f_end
        
        t_coal = (5 / 256) * (G * Mc_SI / c**3) * (math.pi * G * Mc_SI * f_coal / c**3)**(-8/3)
        
        if t_coal < 0.01:
            t_coal = 0.1
        
        n_samples = min(int(t_coal * 2048), 5000)
        if n_samples < 10:
            t = np.linspace(0, 0.1, 200)
            strain = np.sin(2 * np.pi * 50 * t) * np.exp(-t * 5) * 1e-21
        else:
            t = np.linspace(0, t_coal, n_samples)
            strain = np.zeros_like(t)
            
            A = (5 * math.pi / 24)**0.2 * (G * Mc_SI / c**3)**(5/8) * (D_L / c)**(-0.5)
            
            for i, ti in enumerate(t):
                if ti < 0.001:
                    strain[i] = 0
                else:
                    f = (1 / (math.pi * Mc_SI) * (5 * G * Mc_SI / c**3 * (ti + t_coal*0.1))**(-3/8)) / 2
                    if f < f_start:
                        f = f_start
                    strain[i] = A * (f / 100)**(2/3) * np.sin(2 * math.pi * f * ti)
            
            strain = np.nan_to_num(strain, nan=0)
        
        frames_anim = min(frames, len(t))
        
        def update(frame):
            for ax in [ax1, ax2]:
                ax.clear()
                ax.set_facecolor(config['bg_color'])
            
            idx = int(frame * len(t) / frames_anim)
            idx = max(1, min(idx, len(t)-1))
            
            if style == AnimationStyle.MISSION_CONTROL:
                ax1.plot(t[:idx]*1000, strain[:idx]*1e21, '-', color=config['accent'], 
                        linewidth=2.5)
                ax1.fill_between(t[:idx]*1000, strain[:idx]*1e21, alpha=0.2, 
                                color=config['accent'])
            else:
                ax1.plot(t[:idx]*1000, strain[:idx]*1e21, '-', color=config['accent'], linewidth=2)
            
            ax1.set_xlim(0, t[-1]*1000)
            y_max = max(abs(strain.max()), abs(strain.min())) * 1e21 * 1.2
            ax1.set_ylim(-y_max, y_max)
            ax1.set_xlabel('Time to Merger (ms)', fontsize=10, color=config['text_color'])
            ax1.set_ylabel('Strain (×10⁻²¹)', fontsize=10, color=config['text_color'])
            ax1.set_title('Gravitational Wave Strain', fontsize=12, color=config['text_color'])
            ax1.grid(True, alpha=config['grid_alpha'], color=config['text_color'])
            
            separation = r_orbit if 'r_orbit' in dir() else 50 * (1 - frame/frames_anim)
            separation = 50 * (1 - frame/frames_anim) + 5
            
            ax2.set_xlim(-60, 60)
            ax2.set_ylim(-60, 60)
            ax2.set_aspect('equal')
            
            freq = 50 + (frame / frames_anim) * 300
            phase = 2 * np.pi * freq * frame / frames_anim
            
            for i in range(2):
                angle = phase + i * np.pi
                x = separation * np.cos(angle)
                y = separation * np.sin(angle)
                
                if style == AnimationStyle.CINEMATIC:
                    for trail_i in range(10):
                        trail_angle = angle - trail_i * 0.1
                        trail_x = (separation - trail_i*2) * np.cos(trail_angle)
                        trail_y = (separation - trail_i*2) * np.sin(trail_angle)
                        ax2.scatter(trail_x, trail_y, c='#ff6b35', s=30, alpha=0.2)
                
                mass_color = ['#ff6b35', '#00ccff'][i]
                ax2.scatter([x], [y], c=mass_color, s=200, edgecolors='white', 
                           linewidth=2, zorder=10)
            
            gw_circle = plt.Circle((0, 0), separation*1.5, fill=False, 
                                   color=config['accent'], linewidth=1, alpha=0.3)
            ax2.add_patch(gw_circle)
            
            for gw_r in [separation*2, separation*3]:
                gw = plt.Circle((0, 0), gw_r, fill=False, 
                               color=config['accent'], linewidth=0.5, alpha=0.15)
                ax2.add_patch(gw)
            
            ax2.set_title(f'Binary System Evolution\nf = {freq:.0f} Hz', 
                         fontsize=12, color=config['text_color'])
            ax2.axis('off')
            
            info = f"M₁ = {m1} M☉\nM₂ = {m2} M☉\nMc = {Mc:.2f} M☉\nD = {distance_mpc} Mpc"
            ax2.text(0.98, 0.98, info, transform=ax2.transAxes,
                    fontsize=8, color=config['text_color'], verticalalignment='top',
                    horizontalalignment='right')
            
            for ax in [ax1, ax2]:
                self._add_hud_elements(ax, "GW SIMULATION")
        
        anim = FuncAnimation(fig, update, frames=frames_anim, interval=50, repeat=True)
        
        filename = f"gw_{style}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gif"
        filepath = os.path.join(self.plot_dir, filename)
        anim.save(filepath, writer='pillow', fps=20)
        plt.close(fig)
        return filepath
    
    def create_blackhole_animation(self, mass_msun: float = 10, frames: int = 120,
                                   style: Optional[str] = None) -> str:
        """Create detailed black hole accretion disk animation"""
        style = style or self.style
        config = self.style_configs.get(style, self.style_configs[AnimationStyle.MISSION_CONTROL])
        
        fig, ax = self._setup_figure(figsize=(12, 10))
        
        G = 6.67430e-11
        c = 299792458.0
        MSUN = 1.989e30
        
        rs = 2 * G * mass_msun * MSUN / c**2
        
        rs_km = rs / 1000
        isco = 3 * rs
        disk_inner = 1.5 * rs
        disk_outer = 15 * rs
        
        theta = np.linspace(0, 2*np.pi, frames)
        
        custom_cmap = LinearSegmentedColormap.from_list('hot_cool', 
            ['#000022', '#220044', '#660033', '#ff4400', '#ffaa00', '#ffffff'])
        
        def update(frame):
            ax.clear()
            ax.set_xlim(-disk_outer*1.3, disk_outer*1.3)
            ax.set_ylim(-disk_outer*1.3, disk_outer*1.3)
            ax.set_aspect('equal')
            ax.set_facecolor(config['bg_color'])
            
            for r_i in np.linspace(disk_inner, disk_outer, 20):
                temp = 1 - (r_i - disk_inner) / (disk_outer - disk_inner)
                color = custom_cmap(temp)
                
                angle = theta[frame] * (disk_outer / r_i)
                
                x = r_i * np.cos(angle + np.linspace(0, 2*np.pi, 30))
                y = r_i * np.sin(angle + np.linspace(0, 2*np.pi, 30))
                ax.plot(x, y, '-', color=color, linewidth=3, alpha=0.6 + 0.4*temp)
            
            event_horizon = plt.Circle((0, 0), rs_km, facecolor='#000000', 
                                      edgecolor='#ff0044', linewidth=3)
            ax.add_patch(event_horizon)
            
            photon_ring = plt.Circle((0, 0), 1.5*rs_km, fill=False, 
                                     color='#ff6b35', linewidth=2, linestyle='--')
            ax.add_patch(photon_ring)
            
            isco_ring = plt.Circle((0, 0), isco/1000, fill=False, 
                                  color='#00ccff', linewidth=1, linestyle=':', alpha=0.5)
            ax.add_patch(isco_ring)
            
            jet_angle = theta[frame]
            jet_length = 8 * rs_km
            
            for sign in [-1, 1]:
                jet_x = [0, sign * jet_length * np.cos(jet_angle + sign*0.2)]
                jet_y = [0, sign * jet_length * np.sin(jet_angle + sign*0.2)]
                ax.plot(jet_x, jet_y, '-', color='#ff0044', linewidth=2, alpha=0.7)
                
                for j in range(5):
                    j_pos = (j + 1) / 5
                    ax.scatter([sign * j_pos * jet_length * np.cos(jet_angle)], 
                              [sign * j_pos * jet_length * np.sin(jet_angle)],
                              c='#ff0044', s=20, alpha=0.5)
            
            ax.set_title(f'Black Hole Accretion Disk\nMass: {mass_msun} M☉ | '
                        f'Rs: {rs_km:.1f} km | ISCO: {isco/1000:.1f} km',
                        fontsize=12, color=config['text_color'])
            ax.axis('off')
            
            if style == AnimationStyle.SCIENTIFIC:
                info = (f"Schwarzschild radius: R_s = {rs_km:.2f} km\n"
                       f"Inner stable orbit: r_ISCO = {isco/1000:.2f} km\n"
                       f"Photon sphere: r = 1.5 R_s\n"
                       f"Disk temperature: T ~ 10⁶ K")
                ax.text(0.98, 0.98, info, transform=ax.transAxes,
                        fontsize=8, color=config['text_color'], verticalalignment='top',
                        horizontalalignment='right',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
            
            self._add_hud_elements(ax, "BLACK HOLE SIMULATION")
        
        anim = FuncAnimation(fig, update, frames=frames, interval=50, repeat=True)
        
        filename = f"blackhole_{style}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gif"
        filepath = os.path.join(self.plot_dir, filename)
        anim.save(filepath, writer='pillow', fps=20)
        plt.close(fig)
        return filepath
    
    def create_exoplanet_animation(self, Rp_Rs: float = 0.1, a_Rs: float = 10,
                                   inclination: float = 90, frames: int = 100,
                                   style: Optional[str] = None) -> str:
        """Create detailed exoplanet transit animation"""
        style = style or self.style
        config = self.style_configs.get(style, self.style_configs[AnimationStyle.MISSION_CONTROL])
        
        fig = plt.figure(figsize=(14, 6), facecolor=config['bg_color'])
        
        ax1 = fig.add_subplot(121, facecolor=config['bg_color'])
        ax2 = fig.add_subplot(122, facecolor=config['bg_color'])
        
        z = np.linspace(-2, 2, 200)
        
        def transit_model(z_vals, Rp_Rs, inclination):
            flux = np.ones_like(z_vals)
            b = np.abs(z_vals) * np.cos(np.radians(inclination))
            
            for i, b_i in enumerate(b):
                if b_i < 1 + Rp_Rs:
                    if b_i < 1 - Rp_Rs:
                        flux[i] = 1 - Rp_Rs**2
                    elif b_i < 1 + Rp_Rs:
                        overlap = np.pi * Rp_Rs**2 * (1 - ((b_i**2 + Rp_Rs**2 - 1) / (2*b_i*Rp_Rs))**2)
                        flux[i] = 1 - overlap / np.pi
            
            return np.clip(flux, 0, 1)
        
        flux_full = transit_model(z, Rp_Rs, inclination)
        
        planet_positions = np.linspace(-1.5, 1.5, frames)
        
        def update(frame):
            for ax in [ax1, ax2]:
                ax.clear()
                ax.set_facecolor(config['bg_color'])
            
            ax1.set_xlim(-2, 2)
            ax1.set_ylim(-1.2, 1.2)
            ax1.set_aspect('equal')
            
            star_r = 1.0
            
            if style == AnimationStyle.CINEMATIC:
                for r_i in np.linspace(0.1, star_r, 20):
                    circle = plt.Circle((0, 0), r_i, 
                                       color=plt.cm.YlOrRd(1 - r_i/star_r), 
                                       alpha=0.3 + 0.7*(1 - r_i/star_r))
                    ax1.add_patch(circle)
            
            star = plt.Circle((0, 0), star_r, facecolor='#ffdd00', 
                             edgecolor='#ff8800', linewidth=2)
            ax1.add_patch(star)
            
            planet_pos = planet_positions[frame]
            
            if style == AnimationStyle.MISSION_CONTROL:
                planet_color = '#00ff88'
            else:
                planet_color = '#6644aa'
            
            planet = plt.Circle((planet_pos, 0), Rp_Rs, facecolor=planet_color,
                               edgecolor='white', linewidth=1)
            ax1.add_patch(planet)
            
            if abs(planet_pos) < 1 + Rp_Rs:
                ax1.add_patch(Circle((0, 0), star_r, facecolor='gray', alpha=0.3))
            
            ax1.set_title('Exoplanet Transit', fontsize=12, color=config['text_color'])
            ax1.axis('off')
            
            ax2.set_xlim(-2, 2)
            ax2.set_ylim(0.85, 1.02)
            
            in_transit = abs(planet_positions[frame]) < 1 + Rp_Rs
            current_flux = transit_model([planet_positions[frame]], Rp_Rs, inclination)[0]
            
            ax2.plot(z, flux_full, '-', color=config['accent'], linewidth=2)
            ax2.axhline(1, color='gray', linestyle=':', alpha=0.5)
            ax2.axvline(planet_positions[frame], color=planet_color, 
                       linestyle='--', linewidth=1.5, alpha=0.8)
            
            if in_transit:
                ax2.scatter([planet_positions[frame]], [current_flux], 
                          c='#ff0044', s=100, zorder=10)
            
            ax2.set_xlabel('Orbital Position (R★)', fontsize=10, color=config['text_color'])
            ax2.set_ylabel('Normalized Flux', fontsize=10, color=config['text_color'])
            ax2.set_title('Light Curve', fontsize=12, color=config['text_color'])
            ax2.grid(True, alpha=config['grid_alpha'], color=config['text_color'])
            
            info = (f"Planet/Star radius: {Rp_Rs:.3f}\n"
                   f"Transit depth: {(1-flux_full.min())*100:.3f}%\n"
                   f"Inclination: {inclination}°")
            ax2.text(0.98, 0.98, info, transform=ax2.transAxes,
                    fontsize=8, color=config['text_color'], verticalalignment='top',
                    horizontalalignment='right')
        
        anim = FuncAnimation(fig, update, frames=frames, interval=50, repeat=True)
        
        filename = f"exoplanet_{style}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gif"
        filepath = os.path.join(self.plot_dir, filename)
        anim.save(filepath, writer='pillow', fps=15)
        plt.close(fig)
        return filepath
    
    def create_stellar_evolution_animation(self, mass_solar: float = 1.0,
                                          frames: int = 100,
                                          style: Optional[str] = None) -> str:
        """Create detailed stellar evolution HR diagram animation"""
        style = style or self.style
        config = self.style_configs.get(style, self.style_configs[AnimationStyle.MISSION_CONTROL])
        
        fig, ax = self._setup_figure(figsize=(12, 8))
        
        masses = np.linspace(0.08, 100, 500)
        
        L_solar = masses**3.5
        R_solar = masses**0.8
        T_eff = 5778 * (L_solar / R_solar**2)**0.25
        
        spectral_types = []
        for m in masses:
            if m < 0.08:
                spectral_types.append('M')
            elif m < 0.5:
                spectral_types.append('K')
            elif m < 0.8:
                spectral_types.append('G')
            elif m < 1.2:
                spectral_types.append('F')
            elif m < 1.5:
                spectral_types.append('A')
            elif m < 2.5:
                spectral_types.append('B')
            else:
                spectral_types.append('O')
        
        colors = {'M': '#ff4444', 'K': '#ff6644', 'G': '#ffdd44', 
                  'F': '#aaffff', 'A': '#aaaaff', 'B': '#6666ff', 'O': '#4444ff'}
        
        mass_evolution = np.linspace(0.1, mass_solar, frames) if mass_solar > 0.1 else np.linspace(0.1, 0.5, frames)
        
        def update(frame):
            ax.clear()
            ax.set_xscale('log')
            ax.set_yscale('log')
            ax.set_xlim(1e-4, 1e7)
            ax.set_ylim(0.05, 200)
            ax.set_facecolor(config['bg_color'])
            
            for sp_type, color in colors.items():
                mask = [s == sp_type for s in spectral_types]
                ax.scatter(L_solar[mask], R_solar[mask], c=color, s=3, alpha=0.4,
                          label=sp_type)
            
            m_curr = mass_evolution[frame]
            L_curr = m_curr**3.5
            R_curr = m_curr**0.8
            
            if style == AnimationStyle.CINEMATIC:
                for trail_i in range(min(frame, 20)):
                    m_trail = mass_evolution[max(0, frame - trail_i)]
                    L_trail = m_trail**3.5
                    R_trail = m_trail**0.8
                    ax.scatter([L_trail], [R_trail], c='#ff6b35', s=30, 
                              alpha=0.3, zorder=5)
            
            if style == AnimationStyle.MISSION_CONTROL:
                marker_color = '#00ffcc'
            else:
                marker_color = '#ffdd00'
            
            ax.scatter([L_curr], [R_curr], c=marker_color, s=300, 
                      edgecolors='white', linewidth=3, zorder=10)
            
            if m_curr < 0.08:
                spec = 'M'
            elif m_curr < 0.5:
                spec = 'K'
            elif m_curr < 0.8:
                spec = 'G'
            elif m_curr < 1.2:
                spec = 'F'
            elif m_curr < 1.5:
                spec = 'A'
            elif m_curr < 2.5:
                spec = 'B'
            else:
                spec = 'O'
            
            ax.annotate(f'{m_curr:.2f} M☉ ({spec})', 
                       xy=(L_curr*1.3, R_curr*1.3), fontsize=10, 
                       color=config['text_color'])
            
            ax.set_xlabel('Luminosity (L☉)', fontsize=12, color=config['text_color'])
            ax.set_ylabel('Radius (R☉)', fontsize=12, color=config['text_color'])
            ax.set_title('Stellar Evolution - Main Sequence Track', 
                       fontsize=14, color=config['text_color'])
            ax.grid(True, alpha=config['grid_alpha'], color=config['text_color'])
            
            if style == AnimationStyle.SCIENTIFIC:
                info = (f"Mass: {m_curr:.2f} M☉\n"
                       f"Luminosity: {L_curr:.2f} L☉\n"
                       f"Radius: {R_curr:.2f} R☉\n"
                       f"Main sequence lifetime: {10/m_curr:.1f} Gyr")
                ax.text(0.98, 0.98, info, transform=ax.transAxes,
                        fontsize=8, color=config['text_color'], verticalalignment='top',
                        horizontalalignment='right',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
            
            self._add_hud_elements(ax, "STELLAR EVOLUTION")
        
        anim = FuncAnimation(fig, update, frames=frames, interval=80, repeat=True)
        
        filename = f"stellar_{style}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gif"
        filepath = os.path.join(self.plot_dir, filename)
        anim.save(filepath, writer='pillow', fps=15)
        plt.close(fig)
        return filepath
    
    def create_climate_animation(self, start_year: int = 2020, end_year: int = 2100,
                                frames: int = 80, style: Optional[str] = None) -> str:
        """Create detailed climate projection animation"""
        style = style or self.style
        config = self.style_configs.get(style, self.style_configs[AnimationStyle.MISSION_CONTROL])
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), 
                                       facecolor=config['bg_color'])
        
        years = np.arange(start_year, end_year + 1)
        n_years = len(years)
        
        co2_scenarios = {
            'low': [400 + (y - 2020) * 1.5 for y in years],
            'medium': [400 + (y - 2020) * 2.5 for y in years],
            'high': [400 + (y - 2020) * 4 for y in years],
        }
        
        def calculate_temp(co2_ppm, scenario='medium'):
            baseline = 1.1
            co2_sensitivity = 0.8
            rf_co2 = 5.35 * np.log(co2_ppm / 280) / np.log(2)
            
            scenario_factors = {'low': 0.7, 'medium': 1.0, 'high': 1.4}
            return baseline + co2_sensitivity * rf_co2 * scenario_factors[scenario]
        
        temp_anomalies = {s: [calculate_temp(c, s) for c in co2_scenarios[s]] 
                         for s in co2_scenarios}
        
        def update(frame):
            for ax in [ax1, ax2]:
                ax.clear()
                ax.set_facecolor(config['bg_color'])
            
            year_idx = int(frame * n_years / frames)
            current_year = years[year_idx]
            
            for scenario, color in [('low', '#00cc66'), ('medium', '#ffaa00'), ('high', '#ff4444')]:
                ax1.plot(years[:year_idx+1], temp_anomalies[scenario][:year_idx+1], 
                        '-', color=color, linewidth=2, label=scenario.capitalize())
                if year_idx > 0:
                    ax1.fill_between(years[:year_idx+1], temp_anomalies[scenario][:year_idx+1], 
                                    alpha=0.1, color=color)
            
            ax1.axhline(1.5, color='orange', linestyle='--', linewidth=1.5, alpha=0.7,
                       label='Paris Agreement 1.5°C')
            ax1.axhline(2.0, color='red', linestyle='--', linewidth=1.5, alpha=0.7,
                       label='Paris Agreement 2.0°C')
            
            ax1.set_xlim(start_year, end_year)
            ax1.set_ylim(-0.5, 5)
            ax1.set_xlabel('Year', fontsize=10, color=config['text_color'])
            ax1.set_ylabel('Temperature Anomaly (°C)', fontsize=10, color=config['text_color'])
            ax1.set_title('Global Temperature Projection', fontsize=12, color=config['text_color'])
            ax1.grid(True, alpha=config['grid_alpha'], color=config['text_color'])
            ax1.legend(loc='upper left', fontsize=8)
            
            current_co2 = co2_scenarios['medium'][year_idx]
            current_temp = temp_anomalies['medium'][year_idx]
            
            ax2.bar(['CO₂'], [current_co2 - 280], bottom=280, 
                   color=config['accent'], alpha=0.7)
            ax2.axhline(450, color='orange', linestyle='--', label='450 ppm threshold')
            
            ax2.set_xlim(-1, 1)
            ax2.set_ylim(300, 800)
            ax2.set_ylabel('CO₂ Concentration (ppm)', fontsize=10, color=config['text_color'])
            ax2.set_title(f'CO₂ Levels - {current_year}', fontsize=12, color=config['text_color'])
            ax2.set_xticks([])
            
            for ax in [ax1, ax2]:
                ax.tick_params(colors=config['text_color'])
                ax.xaxis.label.set_color(config['text_color'])
                ax.yaxis.label.set_color(config['text_color'])
                ax.title.set_color(config['text_color'])
        
        anim = FuncAnimation(fig, update, frames=frames, interval=50, repeat=True)
        
        filename = f"climate_{style}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gif"
        filepath = os.path.join(self.plot_dir, filename)
        anim.save(filepath, writer='pillow', fps=15)
        plt.close(fig)
        return filepath
    
    def create_darkmatter_animation(self, mass_factor: float = 1.0,
                                   frames: int = 80, style: Optional[str] = None) -> str:
        """Create detailed dark matter halo evolution animation"""
        style = style or self.style
        config = self.style_configs.get(style, self.style_configs[AnimationStyle.MISSION_CONTROL])
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6),
                                       facecolor=config['bg_color'])
        
        r_vals = np.logspace(-2, 3, 100)
        
        rho_s_base = 0.001
        r_s_base = 30
        
        def nfw_density(r, rho_s, r_s):
            return rho_s / ((r / r_s) * (1 + r / r_s)**2)
        
        def einasto_density(r, rho_s, r_s, alpha=0.17):
            return rho_s * np.exp(-2 / alpha * ((r / r_s)**alpha - 1))
        
        def burkert_density(r, rho_s, r_s):
            return rho_s / ((1 + r / r_s) * (1 + (r / r_s)**2))
        
        def update(frame):
            for ax in [ax1, ax2]:
                ax.clear()
                ax.set_facecolor(config['bg_color'])
            
            scale = 0.5 + frame / frames * 1.5
            
            rho_s = rho_s_base * scale
            r_s = r_s_base * scale
            
            rho_nfw = [nfw_density(r, rho_s, r_s) for r in r_vals]
            rho_ein = [einasto_density(r, rho_s * 2, r_s * 0.8) for r in r_vals]
            rho_bur = [burkert_density(r, rho_s * 3, r_s * 0.5) for r in r_vals]
            
            ax1.plot(r_vals, rho_nfw, '-', color='#00ccff', linewidth=2, label='NFW')
            ax1.plot(r_vals, rho_ein, '--', color='#ff00cc', linewidth=2, label='Einasto')
            ax1.plot(r_vals, rho_bur, ':', color='#ffaa00', linewidth=2, label='Burkert')
            
            ax1.set_xscale('log')
            ax1.set_yscale('log')
            ax1.set_xlim(0.01, 1000)
            ax1.set_ylim(1e-30, 1e-18)
            ax1.set_xlabel('Radius (kpc)', fontsize=10, color=config['text_color'])
            ax1.set_ylabel('Density (M☉/kpc³)', fontsize=10, color=config['text_color'])
            ax1.set_title('Dark Matter Halo Profiles', fontsize=12, color=config['text_color'])
            ax1.grid(True, alpha=config['grid_alpha'], color=config['text_color'])
            ax1.legend(loc='upper right', fontsize=8)
            
            y, x = np.mgrid[-100:100:100j, -100:100:100j]
            r_grid = np.sqrt(x**2 + y**2)
            
            density = np.array([nfw_density(r, rho_s, r_s) for r in r_grid.ravel()]).reshape(100, 100)
            density = np.log10(density + 1e-35)
            
            im = ax2.imshow(density, extent=[-100, 100, -100, 100], 
                           origin='lower', cmap='magma', vmin=-30, vmax=-20)
            
            ax2.set_xlabel('X (kpc)', fontsize=10, color=config['text_color'])
            ax2.set_ylabel('Y (kpc)', fontsize=10, color=config['text_color'])
            ax2.set_title(f'DM Density Map (z=0, scale={scale:.2f})', 
                         fontsize=12, color=config['text_color'])
            
            divider = make_axes_locatable(ax2)
            cax = divider.append_axes("right", size="5%", pad=0.1)
            cbar = plt.colorbar(im, cax=cax)
            cbar.set_label('log₁₀(ρ)', fontsize=8)
            
            for ax in [ax1, ax2]:
                ax.tick_params(colors=config['text_color'])
                ax.xaxis.label.set_color(config['text_color'])
                ax.yaxis.label.set_color(config['text_color'])
                ax.title.set_color(config['text_color'])
        
        anim = FuncAnimation(fig, update, frames=frames, interval=80, repeat=True)
        
        filename = f"darkmatter_{style}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gif"
        filepath = os.path.join(self.plot_dir, filename)
        anim.save(filepath, writer='pillow', fps=15)
        plt.close(fig)
        return filepath
    
    def create_impact_animation(self, velocities: List[float] = [15, 20, 25, 30, 45],
                               angles: List[float] = [30, 45, 60, 75, 90],
                               frames: int = 80, style: Optional[str] = None) -> str:
        """Create detailed asteroid impact simulation animation"""
        style = style or self.style
        config = self.style_configs.get(style, self.style_configs[AnimationStyle.MISSION_CONTROL])
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6),
                                       facecolor=config['bg_color'])
        
        diameters = [50, 100, 200, 400, 800]
        
        def impact_energy(diameter_km, velocity_km_s, density_kg_m3=2500):
            volume = (4/3) * np.pi * (diameter_km * 1000 / 2)**3
            mass = volume * density_kg_m3
            energy = 0.5 * mass * (velocity_km_s * 1000)**2
            return energy / 4.184e15
        
        def crater_size(energy_mt):
            return 0.2 * (energy_mt)**0.3
        
        energies = [[impact_energy(d, v) for v in velocities] for d in diameters]
        
        def update(frame):
            for ax in [ax1, ax2]:
                ax.clear()
                ax.set_facecolor(config['bg_color'])
            
            progress = frame / frames
            
            for i, (d, e_row) in enumerate(zip(diameters, energies)):
                colors = plt.cm.Reds(0.3 + 0.7 * i / len(diameters))
                
                x_base = (i + 0.5) * 150
                for j, (v, e) in enumerate(zip(velocities, e_row)):
                    x = x_base + j * 25 + progress * 50
                    y = 20 + progress * 40
                    
                    if style == AnimationStyle.MISSION_CONTROL:
                        marker_color = '#00ff88'
                    else:
                        marker_color = colors
                    
                    ax1.scatter(x, y, s=(d/5)**2, c=[marker_color], alpha=0.7,
                               edgecolors='white', linewidth=1)
                    
                    if frame == frames - 1 or frame % 10 == 0:
                        ax1.annotate(f'{d}m\n{e:.0f}Mt', (x + 15, y), 
                                   fontsize=6, color=config['text_color'])
            
            ax1.set_xlim(0, 800)
            ax1.set_ylim(0, 100)
            ax1.set_xlabel('Diameter / Velocity', fontsize=10, color=config['text_color'])
            ax1.set_ylabel('Simulation Progress', fontsize=10, color=config['text_color'])
            ax1.set_title('Asteroid Impact Energy Scaling', 
                        fontsize=12, color=config['text_color'])
            ax1.set_yticks([])
            
            energy_bar = energies[-1][-1] * progress
            crater = crater_size(energy_bar)
            
            ax2.bar(['Impact Energy'], [energy_bar], color=config['accent'], alpha=0.7)
            ax2.bar(['Crater Diameter'], [crater], color='#ff6b35', alpha=0.7)
            
            ax2.set_ylabel('Energy (Mt) / Diameter (km)', fontsize=10, 
                         color=config['text_color'])
            ax2.set_title(f'Impact Analysis (Energy: {energy_bar:.0f} Mt, '
                        f'Crater: {crater:.1f} km)', fontsize=12, 
                        color=config['text_color'])
            ax2.set_xticks([])
            
            for ax in [ax1, ax2]:
                ax.tick_params(colors=config['text_color'])
                ax.xaxis.label.set_color(config['text_color'])
                ax.yaxis.label.set_color(config['text_color'])
                ax.title.set_color(config['text_color'])
        
        anim = FuncAnimation(fig, update, frames=frames, interval=50, repeat=True)
        
        filename = f"impact_{style}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gif"
        filepath = os.path.join(self.plot_dir, filename)
        anim.save(filepath, writer='pillow', fps=15)
        plt.close(fig)
        return filepath


def generate_all_styles(anim_type: str, **kwargs) -> List[str]:
    """Generate animation in all three styles"""
    styles = [
        AnimationStyle.SCIENTIFIC,
        AnimationStyle.MISSION_CONTROL,
        AnimationStyle.CINEMATIC
    ]
    
    animator = EnhancedAnimator()
    results = []
    
    for style in styles:
        animator.style = style
        animator.config = animator.style_configs.get(style, animator.style_configs[AnimationStyle.MISSION_CONTROL])
        
        method_name = f"create_{anim_type}_animation"
        if hasattr(animator, method_name):
            method = getattr(animator, method_name)
            filepath = method(style=style, **kwargs)
            results.append(filepath)
            print(f"Created {anim_type} ({style}): {filepath}")
    
    return results
