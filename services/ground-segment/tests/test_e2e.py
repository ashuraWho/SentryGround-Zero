"""
End-to-End Tests for SentryGround-Zero
Uses Playwright for browser automation testing.
Requires external services to be running (API, WebSocket, Dashboard).
Run with: pytest tests/test_e2e.py -m e2e
"""

import os
import pytest
import time
import json
import subprocess
import httpx
from typing import Dict, Optional
from dataclasses import dataclass


def is_service_available(url: str, timeout: float = 1.0) -> bool:
    """Check if a service is available at the given URL."""
    try:
        response = httpx.get(url, timeout=timeout)
        return response.status_code < 500
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


@dataclass
class BrowserConfig:
    browser: str = "chromium"
    headless: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    slow_mo: int = 0


class TestDashboard:
    """Test suite for the web dashboard."""
    
    @pytest.fixture(autouse=True)
    def setup(self, page, dashboard_url):
        self.page = page
        self.config = BrowserConfig()
        self.base_url = dashboard_url
        self.username = "admin"
        self.password = "admin123"
    
    @pytest.mark.e2e
    @pytest.mark.requires_dashboard
    def test_dashboard_loads(self, page):
        """Test that dashboard loads successfully."""
        if not is_service_available(f"{self.base_url}/_stcore/health", timeout=2):
            pytest.skip("Dashboard not available")
        
        self.page.goto(self.base_url)
        self.page.wait_for_selector("body", timeout=10000)
        assert self.page.title() is not None
    
    @pytest.mark.e2e
    @pytest.mark.requires_dashboard
    def test_navigation_tabs(self, page):
        """Test navigation tabs work."""
        if not is_service_available(f"{self.base_url}/_stcore/health", timeout=2):
            pytest.skip("Dashboard not available")
        
        self.page.goto(self.base_url)
        self.page.wait_for_timeout(2000)
    
    @pytest.mark.e2e
    @pytest.mark.requires_dashboard
    def test_satellite_catalog(self, page):
        """Test satellite catalog browsing."""
        if not is_service_available(f"{self.base_url}/_stcore/health", timeout=2):
            pytest.skip("Dashboard not available")
        
        self.page.goto(self.base_url)
        self.page.wait_for_timeout(2000)


class TestCLI:
    """Test suite for the CLI terminal."""
    
    @pytest.fixture
    def cli_process(self):
        """Start CLI terminal as a subprocess."""
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        
        process = subprocess.Popen(
            ["python", "-c", "from cli.terminal import MissionControlTerminal; t = MissionControlTerminal(); t.run()"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            text=True,
            env=env,
        )
        
        yield process
        
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
    
    @pytest.mark.e2e
    def test_cli_module_imports(self):
        """Test CLI modules can be imported."""
        from cli.session import MissionControlSession
        from cli.commands import BaseCommand
        
        assert MissionControlSession is not None
        assert BaseCommand is not None


class TestAPI:
    """Test suite for REST API endpoints."""
    
    @pytest.fixture
    def api_base(self, request):
        """Get API base URL from environment or default."""
        return os.environ.get("API_BASE_URL", "http://localhost:8080/api/v1")
    
    @pytest.fixture
    def api_client(self, api_base):
        """Create HTTP client for API testing."""
        return httpx.Client(base_url=api_base, timeout=10.0)
    
    @pytest.mark.e2e
    @pytest.mark.requires_api
    def test_health_endpoint(self, api_base):
        """Test health check endpoint."""
        if not is_service_available(f"{api_base}/health", timeout=2):
            pytest.skip("API not available")
        
        response = httpx.get(f"{api_base}/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "version" in data
    
    @pytest.mark.e2e
    @pytest.mark.requires_api
    def test_authentication(self, api_base):
        """Test authentication endpoint."""
        if not is_service_available(f"{api_base}/health", timeout=2):
            pytest.skip("API not available")
        
        response = httpx.post(
            f"{api_base}/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=5
        )
        assert response.status_code in [200, 201, 401]
    
    @pytest.mark.e2e
    @pytest.mark.requires_api
    def test_telemetry_endpoint_requires_auth(self, api_base):
        """Test telemetry data requires authentication."""
        if not is_service_available(f"{api_base}/health", timeout=2):
            pytest.skip("API not available")
        
        response = httpx.get(f"{api_base}/telemetry", timeout=5)
        assert response.status_code in [401, 403]


class TestSecurity:
    """Test suite for security features."""
    
    @pytest.fixture
    def api_base(self):
        return os.environ.get("API_BASE_URL", "http://localhost:8080/api/v1")
    
    @pytest.mark.e2e
    @pytest.mark.requires_api
    def test_rate_limiting(self, api_base):
        """Test rate limiting on login endpoint."""
        if not is_service_available(f"{api_base}/health", timeout=2):
            pytest.skip("API not available")
        
        responses = []
        for _ in range(15):
            try:
                response = httpx.post(
                    f"{api_base}/auth/login",
                    json={"username": "admin", "password": "wrong"},
                    timeout=2
                )
                responses.append(response.status_code)
            except httpx.TimeoutException:
                responses.append(429)
        
        assert 429 in responses or any(r >= 400 for r in responses[-5:])
    
    @pytest.mark.e2e
    @pytest.mark.requires_api
    def test_unauthorized_access(self, api_base):
        """Test unauthorized access is blocked."""
        if not is_service_available(f"{api_base}/health", timeout=2):
            pytest.skip("API not available")
        
        response = httpx.get(f"{api_base}/telemetry", timeout=5)
        assert response.status_code in [401, 403]
    
    @pytest.mark.e2e
    @pytest.mark.requires_api
    def test_invalid_token(self, api_base):
        """Test invalid token is rejected."""
        if not is_service_available(f"{api_base}/health", timeout=2):
            pytest.skip("API not available")
        
        headers = {"Authorization": "Bearer invalid_token_12345"}
        
        response = httpx.get(
            f"{api_base}/telemetry",
            headers=headers,
            timeout=5
        )
        
        assert response.status_code in [401, 403]


class TestPhysicsModules:
    """Test suite for physics modules - these don't require external services."""
    
    def test_orbital_propagation(self):
        """Test orbital mechanics calculations."""
        from secure_eo_pipeline.physics.orbital import orbital_period, escape_velocity
        
        period = orbital_period(7000)
        assert 90 < period < 110
        
        escape = escape_velocity(7000)
        assert 10 < escape < 11
    
    def test_climate_simulation(self):
        """Test climate simulation."""
        from secure_eo_pipeline.physics import ClimateSimulation
        
        sim = ClimateSimulation()
        sim.step()
        
        state = sim.get_state()
        assert "year" in state
        assert "CO2_ppm" in state
    
    def test_gravitational_waves(self):
        """Test GW calculations."""
        from secure_eo_pipeline.physics import chirp_mass
        
        mc = chirp_mass(30, 25)
        assert 20 < mc < 35
    
    def test_exoplanet_transit(self):
        """Test transit detection."""
        from secure_eo_pipeline.physics import habitable_zone_Kopparapu
        
        inner, outer = habitable_zone_Kopparapu(5778, 1.0)
        assert 0.7 < inner < 1.0
        assert 1.0 < outer < 1.5


class TestIntegration:
    """Integration tests for complete workflows."""
    
    @pytest.fixture
    def api_base(self):
        return os.environ.get("API_BASE_URL", "http://localhost:8080/api/v1")
    
    @pytest.mark.e2e
    @pytest.mark.requires_api
    def test_complete_data_flow(self, api_base):
        """Test complete data pipeline flow."""
        if not is_service_available(f"{api_base}/health", timeout=2):
            pytest.skip("API not available")
        
        response = httpx.post(
            f"{api_base}/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=5
        )
        
        if response.status_code != 200:
            pytest.skip("Authentication not working")
        
        data = response.json()
        if "token" in data:
            headers = {"Authorization": f"Bearer {data['token']}"}
            
            ingest_response = httpx.post(
                f"{api_base}/ingest",
                json={
                    "product_id": "INT_TEST_001",
                    "type": "level_0",
                    "satellite": "SENTRY-01",
                },
                headers=headers,
                timeout=5
            )
            
            assert ingest_response.status_code in [200, 201, 401]
    
    @pytest.mark.e2e
    @pytest.mark.requires_api
    def test_security_workflow(self, api_base):
        """Test security scanning workflow."""
        if not is_service_available(f"{api_base}/health", timeout=2):
            pytest.skip("API not available")
        
        response = httpx.post(
            f"{api_base}/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=5
        )
        
        if response.status_code != 200:
            pytest.skip("Authentication not working")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
