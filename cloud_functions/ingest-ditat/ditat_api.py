from typing import Optional, Dict, Any
import logging

import requests
import pandas as pd


logger = logging.getLogger(__name__)


class DitatAPIException(Exception):
    """Custom exception for Ditat API errors."""
    pass


class DitatAPI:
    """A class to interact with the Ditat API for fetching dispatch and TMS data."""
    
    def __init__(
        self, 
        token: str,
        account_id: str = "agylogistics",
        application_role: str = "Login to TMS",
        base_url: str = "https://api01.ditat.net/api/tms"
    ):
        """
        Initializes the DitatAPI with the provided configuration.
        
        Args:
            account_id: The Ditat account ID
            application_role: The application role for authentication
            base_url: The base URL for the Ditat API
        """
        self.account_id = account_id
        self.application_role = application_role
        self.base_url = base_url.rstrip('/')
        self._access_token: Optional[str] = None
        
        # Base headers for authentication
        self._auth_headers = {
            'accept': 'application/json',
            'authorization': f'Basic {token}',
            'ditat-account-id': self.account_id,
            'ditat-application-role': self.application_role
        }

    def _make_request(self, method: str, endpoint: str, use_token: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Makes an HTTP request to the Ditat API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            use_token: Whether to use token authentication
            **kwargs: Additional arguments to pass to requests
        
        Returns:
            dict: JSON response data
            
        Raises:
            DitatAPIException: If the request fails or returns an error status
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
            
        url = f"{self.base_url}{endpoint}"
        
        # Set up headers
        if use_token:
            if not self._access_token:
                raise DitatAPIException("Token is required but not available. Please authenticate first.")
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/json'
            }
            # Add token to URL if required
            if '?' in url:
                url += f"&ditat-token={self._access_token}"
            else:
                url += f"?ditat-token={self._access_token}"
        else:
            headers = self._auth_headers.copy()
        
        # Merge with any additional headers
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))
        
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            
            if response.status_code not in [200, 201]:
                error_msg = f"API request failed: {response.status_code} - {response.text}"
                logger.error(f"Error calling {method} {url}: {error_msg}")
                raise DitatAPIException(error_msg)
            
            return response.json()
            
        except requests.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(f"Network error calling {method} {url}: {error_msg}")
            raise DitatAPIException(error_msg)
        except ValueError as e:
            # Handle JSON decode errors
            error_msg = f"Failed to decode JSON response: {str(e)}"
            logger.error(f"JSON error from {method} {url}: {error_msg}")
            raise DitatAPIException(error_msg)

    def authenticate(self) -> str:
        """
        Authenticates with the Ditat API and retrieves a token.
        
        Returns:
            str: The authentication token
            
        Raises:
            DitatAPIException: If authentication fails
        """
        try:
            # Make raw request for authentication since we need the raw content
            url = f"{self.base_url}/auth/login"
            response = requests.post(url, headers=self._auth_headers)
            
            if response.status_code != 200:
                error_msg = f"Authentication failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise DitatAPIException(error_msg)
            
            self._access_token = response.content.decode()
            logger.info("Successfully authenticated with Ditat API")
            return self._access_token
            
        except requests.RequestException as e:
            error_msg = f"Authentication request failed: {str(e)}"
            logger.error(error_msg)
            raise DitatAPIException(error_msg)

    def get_token(self) -> str:
        """
        Gets the current token, authenticating if necessary.
        
        Returns:
            str: The authentication token
        """
        if not self._access_token:
            self.authenticate()
        return self._access_token

    def get_dispatch_board(
        self, 
        filter_config: Optional[Dict[str, Any]] = None,
        update_counter: int = 0,
        json_normalize: bool = False,
    ) -> pd.DataFrame:
        """
        Fetches dispatch board data from the Ditat API.
        
        Args:
            filter_config: Optional filter configuration. If None, uses default filter.
            update_counter: Update counter for the request
            json_normalize: Whether to normalize the JSON to DataFrame
            
        Returns:
            pd.DataFrame: DataFrame containing dispatch board trips data
        """
        # Ensure we have a token
        if not self._access_token:
            self.authenticate()
        
        # Default filter configuration
        default_filter = {
            "showFilterPanel": True,
            "truckCustomGroupKeys": [],
            "driverCustomGroupKeys": [],
            "customerCustomGroupKeys": [],
            "pickupZoneKeys": [],
            "deliveryZoneKeys": [],
            "currentLegZoneKeys": [],
            "truckSideBrokerage": 0,
            "hazmat": 0,
            "status": 0,
            "hasAgentAssignment": 0,
            "fromPickupDate": 9,
            "toPickupDate": 10,
            "fromDeliveryDate": 10,
            "toDeliveryDate": 10,
            "fromCurrentLegDate": 10,
            "toCurrentLegDate": 10
        }
        
        # Use provided filter or default
        filter_to_use = filter_config if filter_config is not None else default_filter
        
        body = {
            "Filter": filter_to_use,
            "UpdateCounter": update_counter
        }
        
        data = self._make_request('POST', '/dispatch-board', use_token=True, json=body)
        
        # Extract trips data
        trips = data.get("data", {}).get("trips", [])
        
        if not trips:
            logger.warning("No trips found in dispatch board response")
            return pd.DataFrame()
        
        # Normalize and return as DataFrame
        df = pd.json_normalize(trips) if json_normalize else pd.DataFrame(trips)
        return df

    def refresh_token(self) -> str:
        """
        Refreshes the authentication token.
        
        Returns:
            str: The new authentication token
        """
        self._access_token = None
        return self.authenticate()

    @property
    def is_authenticated(self) -> bool:
        """
        Checks if the API client is currently authenticated.
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        return self._access_token is not None
