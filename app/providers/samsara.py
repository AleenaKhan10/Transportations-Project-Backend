import logging
from uuid import UUID
from typing import Optional, Union, Dict, Any, List, Tuple
import requests
import pandas as pd
from helpers.utils import chunkify, run_parallel_exec_but_return_in_order


logger = logging.getLogger(__name__)


class SamsaraAPIException(Exception):
    """Custom exception for Samsara API errors."""
    pass


class SamsaraAPI:
    """A class to interact with the Samsara API for fetching sensor and trailer data."""
    
    def __init__(self, token: str, base_url: str = "https://api.samsara.com"):
        """
        Initializes the SamsaraAPI with the provided JWT token.
        
        Args:
            token: The JWT token for authenticating with the Samsara API.
            base_url: The base URL for the Samsara API. Defaults to https://api.samsara.com
        """
        self.token = token
        self.base_url = base_url.rstrip('/')  # Remove trailing slash if present
        self.headers = {
            'accept': 'application/json',
            'authorization': f'Bearer {self.token}',
            'content-type': 'application/json',
        }

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Makes an HTTP request to the Samsara API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments to pass to requests (json, params, etc.)
        
        Returns:
            dict: JSON response data
            
        Raises:
            SamsaraAPIException: If the request fails or returns an error status
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
            
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            
            if response.status_code != 200:
                error_msg = f"API request failed: {response.status_code} - {response.text}"
                logger.error(f"Error calling {method} {url}: {error_msg}")
                raise SamsaraAPIException(error_msg)
            
            return response.json()
            
        except requests.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(f"Network error calling {method} {url}: {error_msg}")
            raise SamsaraAPIException(error_msg)

    def get_all_sensors(self, remove_deactivated: bool = True) -> pd.DataFrame:
        """
        Fetches all sensors from the Samsara API and returns them as a DataFrame.
        
        Args:
            remove_deactivated: Whether to filter out deactivated sensors
            
        Returns:
            pd.DataFrame: DataFrame containing sensor data
        """
        data = self._make_request('POST', '/v1/sensors/list')
        
        if 'sensors' not in data:
            raise SamsaraAPIException("No sensors found in the response.")
        
        df = pd.DataFrame(data['sensors'])
        
        if remove_deactivated and not df.empty:
            df = df[~df['name'].str.contains("Deactivated", na=False)]
        
        return df

    def get_temperatures(self, sensor_ids: List[int]) -> pd.DataFrame:
        """
        Fetches the temperature of the sensors with the given IDs from the Samsara API.
        
        Args:
            sensor_ids: List of sensor IDs to fetch temperatures for
            
        Returns:
            pd.DataFrame: DataFrame containing temperature data
        """
        if not sensor_ids:
            raise ValueError("The list of sensor IDs cannot be empty.")
        
        payload = {'sensors': sensor_ids}
        data = self._make_request('POST', '/v1/sensors/temperature', json=payload)
        
        if 'sensors' not in data:
            raise SamsaraAPIException("No temperature data found in the response.")
        
        # Normalize the data and ensure trailerId and vehicleId are strings
        sensors_data = [
            {**d, 'trailerId': str(d.get('trailerId', '')), 'vehicleId': str(d.get('vehicleId', ''))}
            for d in data['sensors']
        ]
        
        return pd.json_normalize(sensors_data)

    def get_temperatures_batched(self, sensor_ids: List[int], batch_size: int = 40) -> pd.DataFrame:
        """
        Fetches the temperature of sensors in batches to avoid hitting API limits.
        
        Args:
            sensor_ids: List of sensor IDs to fetch temperatures for
            batch_size: Number of sensors to fetch per batch
            
        Returns:
            pd.DataFrame: DataFrame containing temperature data for all sensors
        """
        if not sensor_ids:
            raise ValueError("The list of sensor IDs cannot be empty.")
        
        all_data = run_parallel_exec_but_return_in_order(
            self.get_temperatures,
            chunkify(sensor_ids, batch_size),
            max_workers=10,
        )
        
        # Filter out non-DataFrame results and empty DataFrames
        valid_data = [data for data in all_data if isinstance(data, pd.DataFrame) and not data.empty]
        
        return pd.concat(valid_data, ignore_index=True) if valid_data else pd.DataFrame()

    def get_trailers(
        self, 
        tag_ids: Optional[List[int]] = None, 
        after: Optional[Union[str, UUID]] = None, 
        limit: int = 512,
        json_normalize: bool = False,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Fetches trailers from the Samsara API and returns them as a DataFrame.
        
        Args:
            tag_ids: Optional list of tag IDs to filter trailers
            after: Optional cursor for pagination
            limit: Maximum number of trailers to return
            json_normalize: Whether to normalize the JSON data
        
        Returns:
            tuple: (DataFrame of trailers, pagination dictionary)
        """
        params = {'limit': limit}
        
        if after:
            params['after'] = str(after)
        if tag_ids:
            params['tagIds'] = ",".join(map(str, tag_ids))
        
        data = self._make_request('GET', '/fleet/trailers', params=params)
        
        if 'data' not in data:
            raise SamsaraAPIException(f"No trailers found in the response. Response: {data}")
        
        df = pd.json_normalize(data['data']) if json_normalize else pd.DataFrame(data['data'])
        return df, data.get('pagination', {})

    def get_all_trailers(self, tag_ids: Optional[List[int]] = None, limit: int = 512, json_normalize: bool = False) -> pd.DataFrame:
        """
        Fetches all trailers from the Samsara API, handling pagination automatically.
        
        Args:
            tag_ids: Optional list of tag IDs to filter trailers
            limit: Maximum number of trailers to return per request
            json_normalize: Whether to normalize the JSON data
        
        Returns:
            pd.DataFrame: DataFrame containing all trailers
        """
        all_trailers = []
        after = None
        
        while True:
            df, pagination = self.get_trailers(tag_ids=tag_ids, after=after, limit=limit, json_normalize=json_normalize)
            
            if not df.empty:
                all_trailers.append(df)
            
            if not pagination.get('hasNextPage'):
                break
            
            after = pagination.get('endCursor')
        
        return pd.concat(all_trailers, ignore_index=True) if all_trailers else pd.DataFrame()

    def get_stats(
        self,
        tag_ids: Optional[List[int]] = None,
        types: Optional[List[str]] = [
            "reeferRunMode",
            "reeferSetPointTemperatureMilliCZone1",
        ],
        after: Optional[Union[str, UUID]] = None,
        json_normalize: bool = False,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Fetches trailer statistics from the Samsara API and returns them as a DataFrame.

        Args:
            tag_ids: Optional list of tag IDs to filter the statistics.
            types: Optional list of types of statistics to fetch.
            after: Optional cursor for pagination.
            json_normalize: Whether to normalize the JSON data.

        Returns:
            tuple: (DataFrame of trailer statistics, pagination dictionary)

        Raises:
            SamsaraAPIException: If no data is found in the response.
        
        Reference:
            https://developers.samsara.com/reference/gettrailerstatsfeed
        """
        params = {}
        if after:
            params["after"] = str(after)
        if types:
            params["types"] = ",".join(types)
        if tag_ids:
            params["tagIds"] = ",".join(map(str, tag_ids))

        data = self._make_request("GET", "/beta/fleet/trailers/stats/feed", params=params)
        if "data" not in data:
            raise SamsaraAPIException(
                f"No trailers found in the response. Response: {data}"
            )

        df = (
            pd.json_normalize(data["data"])
            if json_normalize
            else pd.DataFrame(data["data"])
        )
        
        # Explode the "types" columns if they are in `list` format
        try:
            df = df.explode(types)
        except Exception:
            pass
        
        return df, data.get("pagination", {})

    def get_all_stats(
        self,
        tag_ids: Optional[List[int]] = None,
        types: Optional[List[str]] = [
            "reeferRunMode",
            "reeferSetPointTemperatureMilliCZone1",
        ],
        json_normalize: bool = False,
    ):
        """
        Fetches all trailer statistics from the Samsara API, handling pagination automatically.

        Args:
            tag_ids: Optional list of tag IDs to filter trailers
            types: Optional list of types of statistics to fetch
            json_normalize: Whether to normalize the JSON data

        Returns:
            pd.DataFrame: DataFrame containing all trailer statistics
        
        Reference:
            https://developers.samsara.com/reference/gettrailerstatsfeed
        """
        all_stats = []
        after = None

        while True:
            df, pagination = self.get_stats(
                tag_ids=tag_ids, types=types, after=after, json_normalize=json_normalize
            )

            if not df.empty:
                all_stats.append(df)

            if not pagination.get("hasNextPage"):
                break

            after = pagination.get("endCursor")

        return pd.concat(all_stats, ignore_index=True) if all_stats else pd.DataFrame()
