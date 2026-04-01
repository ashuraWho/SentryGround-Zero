"""
WebGL/3D Visualization Module for SentryGround-Zero.

Generates:
- Interactive 3D orbit visualization (Three.js compatible)
- Ground track maps
- Constellation maps
- Data dashboards

Output: HTML/JavaScript files that can be served or embedded.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple
import numpy as np


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class OrbitalPosition:
    """3D position in space."""
    x: float
    y: float
    z: float
    time: float


@dataclass
class SatelliteOrbit:
    """Satellite orbit data for visualization."""
    name: str
    color: str
    positions: List[OrbitalPosition]
    semimajor_axis: float
    eccentricity: float
    inclination: float


@dataclass
class GroundStation:
    """Ground station for pass visualization."""
    name: str
    lat: float
    lon: float
    color: str = "#FF6B6B"


@dataclass
class PassArc:
    """Visible pass arc."""
    satellite: str
    station: str
    aos_time: float
    los_time: float
    max_elevation: float


# =============================================================================
# ORBIT GEOMETRY
# =============================================================================

GM_EARTH = 3.986004418e14
R_EARTH = 6.378137e6


def generate_orbit_ellipse(
    semimajor_axis_km: float,
    eccentricity: float,
    inclination_deg: float,
    raan_deg: float,
    arg_perigee_deg: float,
    n_points: int = 100
) -> List[OrbitalPosition]:
    """Generate 3D orbit ellipse points."""
    positions = []
    
    inc = math.radians(inclination_deg)
    raan = math.radians(raan_deg)
    omega = math.radians(arg_perigee_deg)
    
    cos_i = math.cos(inc)
    sin_i = math.sin(inc)
    cos_O = math.cos(raan)
    sin_O = math.sin(raan)
    cos_o = math.cos(omega)
    sin_o = math.sin(omega)
    
    for i in range(n_points):
        nu = 2 * math.pi * i / n_points
        r = semimajor_axis_km * (1 - eccentricity**2) / (1 + eccentricity * math.cos(nu))
        
        x_perif = r * math.cos(nu)
        y_perif = r * math.sin(nu)
        
        x = (cos_o * cos_O - sin_o * sin_O * cos_i) * x_perif + (-sin_o * cos_O - cos_o * sin_O * cos_i) * y_perif
        y = (cos_o * sin_O + sin_o * cos_O * cos_i) * x_perif + (-sin_o * sin_O + cos_o * cos_O * cos_i) * y_perif
        z = (sin_o * sin_i) * x_perif + (cos_o * sin_i) * y_perif
        
        positions.append(OrbitalPosition(x=x, y=y, z=z, time=float(i) / n_points))
    
    return positions


def generate_earth_sphere(n_segments: int = 32) -> dict:
    """Generate Earth sphere geometry for WebGL."""
    vertices = []
    normals = []
    indices = []
    
    for i in range(n_segments + 1):
        theta = i * math.pi / n_segments
        for j in range(n_segments + 1):
            phi = j * 2 * math.pi / n_segments
            
            x = math.sin(theta) * math.cos(phi)
            y = math.sin(theta) * math.sin(phi)
            z = math.cos(theta)
            
            vertices.extend([x * R_EARTH / 1000, y * R_EARTH / 1000, z * R_EARTH / 1000])
            normals.extend([x, y, z])
    
    for i in range(n_segments):
        for j in range(n_segments):
            first = i * (n_segments + 1) + j
            second = first + n_segments + 1
            
            indices.extend([first, second, first + 1])
            indices.extend([second, second + 1, first + 1])
    
    return {
        'vertices': vertices,
        'normals': normals,
        'indices': indices
    }


# =============================================================================
# HTML/JS GENERATION
# =============================================================================

ORBIT_VIEWER_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #0a0a0f; color: white; overflow: hidden; }}
        #container {{ width: 100vw; height: 100vh; }}
        #controls {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(20, 20, 30, 0.9);
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #333;
            max-width: 300px;
        }}
        #controls h2 {{ margin-bottom: 15px; color: #00d4ff; }}
        .control-group {{ margin-bottom: 15px; }}
        .control-group label {{ display: block; margin-bottom: 5px; color: #888; }}
        .control-group input {{ width: 100%; background: #1a1a2e; border: 1px solid #333; color: white; padding: 8px; border-radius: 4px; }}
        button {{ background: #00d4ff; color: #000; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-top: 10px; }}
        button:hover {{ background: #00a8cc; }}
        #info {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: rgba(20, 20, 30, 0.9);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #333;
        }}
        #satellite-list {{
            max-height: 200px;
            overflow-y: auto;
        }}
        .sat-item {{
            padding: 8px;
            margin: 4px 0;
            border-radius: 4px;
            cursor: pointer;
            display: flex;
            align-items: center;
        }}
        .sat-dot {{ width: 12px; height: 12px; border-radius: 50%; margin-right: 10px; }}
    </style>
</head>
<body>
    <div id="container"></div>
    
    <div id="controls">
        <h2>{title}</h2>
        <div class="control-group">
            <label>Camera Distance (km)</label>
            <input type="range" id="cameraDistance" min="10000" max="100000" value="40000">
        </div>
        <div class="control-group">
            <label>Orbit Opacity</label>
            <input type="range" id="orbitOpacity" min="0" max="100" value="80">
        </div>
        <div class="control-group">
            <label>Time Speed</label>
            <input type="range" id="timeSpeed" min="1" max="100" value="10">
        </div>
        <button onclick="toggleAnimation()">Play/Pause</button>
        <button onclick="resetView()">Reset View</button>
        
        <div class="control-group">
            <label>Satellites</label>
            <div id="satellite-list"></div>
        </div>
    </div>
    
    <div id="info">
        <div id="time-display">Time: 0.00 s</div>
        <div id="selected-sat">Selected: None</div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script>
        // Scene setup
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000000);
        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        document.getElementById('container').appendChild(renderer.domElement);
        
        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
        scene.add(ambientLight);
        
        const sunLight = new THREE.DirectionalLight(0xffffff, 1.5);
        sunLight.position.set(100, 50, 100);
        scene.add(sunLight);
        
        // Earth sphere
        const earthGeometry = new THREE.SphereGeometry({earth_radius_km}, 64, 64);
        const earthMaterial = new THREE.MeshPhongMaterial({{
            map: null,
            color: 0x1a4d7c,
            specular: 0x333333,
            shininess: 25
        }});
        const earth = new THREE.Mesh(earthGeometry, earthMaterial);
        scene.add(earth);
        
        // Atmosphere glow
        const atmosphereGeometry = new THREE.SphereGeometry({earth_radius_km} * 1.01, 64, 64);
        const atmosphereMaterial = new THREE.MeshPhongMaterial({{
            color: 0x4a90d9,
            transparent: true,
            opacity: 0.1,
            side: THREE.BackSide
        }});
        const atmosphere = new THREE.Mesh(atmosphereGeometry, atmosphereMaterial);
        scene.add(atmosphere);
        
        // Orbit lines
        const orbits = [];
        const satellites = [];
        {orbit_code}
        
        // Ground stations
        {groundstation_code}
        
        // Camera controls (simplified)
        let isAnimating = true;
        let timeSpeed = 10;
        let currentTime = 0;
        camera.position.set(0, 40000, 60000);
        camera.lookAt(0, 0, 0);
        
        function toggleAnimation() {{
            isAnimating = !isAnimating;
        }}
        
        function resetView() {{
            camera.position.set(0, 40000, 60000);
            camera.lookAt(0, 0, 0);
        }}
        
        // Animation loop
        function animate() {{
            requestAnimationFrame(animate);
            
            if (isAnimating) {{
                currentTime += timeSpeed * 0.001;
                
                satellites.forEach((sat, i) => {{
                    const t = (currentTime * {orbital_scale}) % 1;
                    const pos = sat.userData.positions[Math.floor(t * sat.userData.positions.length)];
                    if (pos) {{
                        sat.position.set(pos.x, pos.y, pos.z);
                    }}
                }});
                
                document.getElementById('time-display').textContent = 'Time: ' + currentTime.toFixed(2) + ' s';
            }}
            
            renderer.render(scene, camera);
        }}
        
        animate();
        
        // Resize handler
        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});
        
        // Control bindings
        document.getElementById('cameraDistance').addEventListener('input', (e) => {{
            const dist = parseFloat(e.target.value);
            camera.position.set(dist * 0.5, dist * 0.7, dist);
        }});
        
        document.getElementById('orbitOpacity').addEventListener('input', (e) => {{
            const opacity = parseFloat(e.target.value) / 100;
            orbits.forEach(o => o.material.opacity = opacity);
        }});
        
        document.getElementById('timeSpeed').addEventListener('input', (e) => {{
            timeSpeed = parseFloat(e.target.value);
        }});
    </script>
</body>
</html>
"""


def generate_orbit_viewer_html(
    satellites: List[SatelliteOrbit],
    ground_stations: Optional[List[GroundStation]] = None,
    title: str = "SentryGround-Zero Orbit Viewer"
) -> str:
    """Generate complete HTML for 3D orbit visualization."""
    
    orbit_code_parts = []
    sat_code_parts = []
    
    colors = ['#00ff00', '#ff6600', '#00ffff', '#ff00ff', '#ffff00', '#ff0066']
    
    for i, sat in enumerate(satellites):
        color = sat.color or colors[i % len(colors)]
        
        positions_json = [
            {'x': p.x, 'y': p.y, 'z': p.z} 
            for p in sat.positions
        ]
        positions_str = json.dumps(positions_json)
        
        orbit_code_parts.append(f"""
        const positions_{i} = {positions_str};
        const orbitCurve_{i} = new THREE.CatmullRomCurve3(
            positions_{i}.map(p => new THREE.Vector3(p.x, p.y, p.z))
        );
        const orbitGeometry_{i} = new THREE.TubeGeometry(orbitCurve_{i}, 100, 1, 8, false);
        const orbitMaterial_{i} = new THREE.MeshBasicMaterial({{
            color: 0x{color.lstrip('#')},
            transparent: true,
            opacity: 0.8
        }});
        const orbit_{i} = new THREE.Mesh(orbitGeometry_{i}, orbitMaterial_{i});
        scene.add(orbit_{i});
        orbits.push(orbit_{i});
        """)
        
        sat_code_parts.append(f"""
        const satGeo_{i} = new THREE.SphereGeometry(50, 16, 16);
        const satMat_{i} = new THREE.MeshBasicMaterial({{ color: 0x{color.lstrip('#')} }});
        const sat_{i} = new THREE.Mesh(satGeo_{i}, satMat_{i});
        sat_{i}.userData.positions = positions_{i};
        scene.add(sat_{i});
        satellites.push(sat_{i});
        """)
    
    orbit_code = ''.join(orbit_code_parts)
    sat_code = ''.join(sat_code_parts)
    
    groundstation_code = ""
    if ground_stations:
        gs_parts = []
        for i, gs in enumerate(ground_stations):
            lat, lon = gs.lat, gs.lon
            x = R_EARTH / 1000 * math.cos(math.radians(lat)) * math.cos(math.radians(lon))
            y = R_EARTH / 1000 * math.sin(math.radians(lat))
            z = R_EARTH / 1000 * math.cos(math.radians(lat)) * math.sin(math.radians(lon))
            
            gs_parts.append(f"""
            const gsGeo_{i} = new THREE.SphereGeometry(30, 16, 16);
            const gsMat_{i} = new THREE.MeshBasicMaterial({{ color: 0x{gs.color.lstrip('#')} }});
            const gs_{i} = new THREE.Mesh(gsGeo_{i}, gsMat_{i});
            gs_{i}.position.set({x:.1f}, {y:.1f}, {z:.1f});
            scene.add(gs_{i});
            """)
        groundstation_code = ''.join(gs_parts)
    
    html = ORBIT_VIEWER_TEMPLATE.format(
        title=title,
        earth_radius_km=R_EARTH / 1000,
        orbit_code=orbit_code + sat_code,
        groundstation_code=groundstation_code,
        orbital_scale=100
    )
    
    return html


# =============================================================================
# 2D GROUND TRACK VISUALIZATION
# =============================================================================

def generate_ground_track_html(
    satellites: List[SatelliteOrbit],
    ground_stations: Optional[List[GroundStation]] = None,
    title: str = "Ground Track Monitor"
) -> str:
    """Generate 2D ground track visualization HTML."""
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Courier New', monospace; 
            background: #0a0a0f; 
            color: #00ff00;
            padding: 20px;
        }}
        #map {{
            width: 100%;
            height: 500px;
            border: 2px solid #00ff00;
            border-radius: 10px;
            background: linear-gradient(180deg, #000 0%, #001a00 100%);
            position: relative;
            overflow: hidden;
        }}
        .grid {{
            position: absolute;
            inset: 0;
            background-image: 
                linear-gradient(rgba(0,255,0,0.1) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0,255,0,0.1) 1px, transparent 1px);
            background-size: 5% 3.33%;
        }}
        .sat-point {{
            position: absolute;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            transform: translate(-50%, -50%);
        }}
        .gs-marker {{
            position: absolute;
            width: 0;
            height: 0;
            border-left: 6px solid transparent;
            border-right: 6px solid transparent;
            border-bottom: 10px solid #ff6600;
            transform: translate(-50%, -50%);
        }}
        .legend {{
            margin-top: 20px;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div id="map">
        <div class="grid"></div>
        {''.join(f'<div class="sat-point" style="background:{s.color}; top:{(s.positions[0].y / R_EARTH + 1) * 50}%; left:{(s.positions[0].x / R_EARTH + 1) * 50}%" title="{s.name}"></div>' for s in satellites)}
        {''.join(f'<div class="gs-marker" style="top:{gs.lat + 90}%; left:{gs.lon + 180}%; border-bottom-color:{gs.color}" title="{gs.name}"></div>' for gs in (ground_stations or []))}
    </div>
    <div class="legend">
        {''.join(f'<div class="legend-item"><div class="dot" style="background:{s.color}"></div>{s.name}</div>' for s in satellites)}
    </div>
    <script>
        // Simplified ground track animation
        function updatePositions() {{
            // Update satellite positions based on orbital mechanics
            setTimeout(updatePositions, 1000);
        }}
        updatePositions();
    </script>
</body>
</html>
"""


# =============================================================================
# DASHBOARD HTML GENERATION
# =============================================================================

def generate_dashboard_html(
    metrics: dict,
    title: str = "Mission Control Dashboard"
) -> str:
    """Generate metrics dashboard HTML."""
    
    metric_cards = []
    for name, value in metrics.items():
        metric_cards.append(f"""
        <div class="metric-card">
            <div class="metric-name">{name}</div>
            <div class="metric-value">{value}</div>
        </div>
        """)
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #0a0a0f; color: white; }}
        .header {{ background: linear-gradient(90deg, #1a1a2e, #16213e); padding: 20px; text-align: center; }}
        .header h1 {{ color: #00d4ff; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; padding: 20px; }}
        .metric-card {{ 
            background: rgba(0, 212, 255, 0.1); 
            border: 1px solid #00d4ff;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }}
        .metric-name {{ color: #888; font-size: 0.9em; }}
        .metric-value {{ font-size: 2em; color: #00d4ff; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
    </div>
    <div class="grid">
        {''.join(metric_cards)}
    </div>
</body>
</html>
"""
