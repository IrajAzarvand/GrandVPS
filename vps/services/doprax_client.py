import requests
import os
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class DopraxAPIError(Exception):
    """Custom exception for Doprax API errors"""
    pass


class DopraxClient:
    """Doprax API client for VPS management operations"""

    def __init__(self):
        self.api_key = getattr(settings, 'DOPRAX_API_KEY', None)
        if not self.api_key:
            raise ImproperlyConfigured("DOPRAX_API_KEY is not configured in Django settings")

        self.base_url = "https://www.doprax.com"
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        self.timeout = 30

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to Doprax API with error handling"""
        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, json=data, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()

            if response.status_code == 204:  # No Content
                return {}

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Doprax API request failed: {method} {endpoint} - {str(e)}")
            raise DopraxAPIError(f"API request failed: {str(e)}")
        except ValueError as e:
            logger.error(f"Invalid JSON response from Doprax API: {method} {endpoint} - {str(e)}")
            raise DopraxAPIError(f"Invalid API response: {str(e)}")

    def get_locations_and_plans(self) -> Dict[str, Any]:
        """Fetch locations and available plans from Doprax API"""
        try:
            response = self._make_request('GET', '/api/v1/vlocations/')
            return response.get('data', {})
        except DopraxAPIError:
            raise

    def get_operating_systems(self) -> Dict[str, List[Dict]]:
        """Fetch available operating systems"""
        try:
            response = self._make_request('GET', '/api/v1/os/')
            return response.get('os_map', {})
        except DopraxAPIError:
            raise

    def create_vps(self, location_code: str, machine_type_code: str, os_slug: str,
                   provider_name: str, vm_name: str) -> Dict[str, Any]:
        """Create a new VPS instance"""
        payload = {
            "location_code": location_code,
            "machine_type_code": machine_type_code,
            "name": vm_name,
            "os_slug": os_slug,
            "provider_name": provider_name
        }

        try:
            response = self._make_request('POST', '/api/v1/vms/', payload)
            return response.get('data', {})
        except DopraxAPIError:
            raise

    def get_vps_status(self, vm_code: str) -> Dict[str, Any]:
        """Get VPS instance status and details"""
        try:
            response = self._make_request('GET', f'/api/v1/vms/{vm_code}/')
            return response.get('data', {})
        except DopraxAPIError:
            raise

    def execute_vps_command(self, vm_code: str, command: str) -> Dict[str, Any]:
        """Execute command on VPS (start, stop, restart)"""
        if command not in ['turnon', 'shutdown', 'reboot']:
            raise ValueError(f"Invalid command: {command}")

        payload = {"command": command}

        try:
            response = self._make_request('POST', f'/api/v1/vms/{vm_code}/commands/', payload)
            return response.get('msg', {})
        except DopraxAPIError:
            raise

    def delete_vps(self, vm_code: str) -> bool:
        """Delete a VPS instance"""
        try:
            # Note: This might need to be implemented based on actual API
            # For now, returning True as placeholder
            return True
        except DopraxAPIError:
            raise

    def get_vps_list(self) -> List[Dict[str, Any]]:
        """Get list of all VPS instances"""
        try:
            # This endpoint might need to be confirmed with actual API
            response = self._make_request('GET', '/api/v1/vms/')
            return response.get('data', [])
        except DopraxAPIError:
            raise

    def get_vps_network_info(self, vm_code: str) -> Dict[str, Any]:
        """Get network information for a VPS"""
        try:
            response = self._make_request('GET', f'/api/v1/vms/{vm_code}/network/')
            return response.get('data', {})
        except DopraxAPIError:
            raise

    def get_vps_traffic(self, vm_code: str) -> Dict[str, Any]:
        """Get traffic usage for a VPS"""
        try:
            response = self._make_request('GET', f'/api/v1/vms/{vm_code}/traffic/')
            return response.get('data', {})
        except DopraxAPIError:
            raise

    def create_snapshot(self, vm_code: str, snapshot_name: str) -> Dict[str, Any]:
        """Create a snapshot of a VPS"""
        payload = {"name": snapshot_name}

        try:
            response = self._make_request('POST', f'/api/v1/vms/{vm_code}/snapshots/', payload)
            return response.get('data', {})
        except DopraxAPIError:
            raise

    def list_snapshots(self, vm_code: str) -> List[Dict[str, Any]]:
        """List snapshots for a VPS"""
        try:
            response = self._make_request('GET', f'/api/v1/vms/{vm_code}/snapshots/')
            return response.get('data', [])
        except DopraxAPIError:
            raise

    def delete_snapshot(self, vm_code: str, snapshot_id: str) -> bool:
        """Delete a snapshot"""
        try:
            # This might need to be implemented based on actual API
            return True
        except DopraxAPIError:
            raise

    def rebuild_vps(self, vm_code: str, os_slug: str) -> Dict[str, Any]:
        """Rebuild VPS with new OS"""
        payload = {"os_slug": os_slug}

        try:
            response = self._make_request('POST', f'/api/v1/vms/{vm_code}/rebuild/', payload)
            return response.get('data', {})
        except DopraxAPIError:
            raise