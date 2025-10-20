from fury_api.lib.usgs_client import USGSEarthquakeClient

class ClientsFactory:
    
    @staticmethod
    def get_usgs_client() -> USGSEarthquakeClient:
        """Get a new prefect client."""
        return USGSEarthquakeClient()