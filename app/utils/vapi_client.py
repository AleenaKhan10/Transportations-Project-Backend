import httpx
from typing import List, Dict, Any, Union, Optional
from config import settings
from helpers import logger


class VAPIClient:
    def __init__(self):
        self.base_url = "https://api.vapi.ai"
        self.api_key = settings.VAPI_API_KEY
        self.assistant_id = settings.VAPI_ASSISTANT_ID
        
    async def create_vapi_call(self, driver_data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Create a VAPI call with driver information
        Args:
            driver_data: Single driver dict or list of driver dicts
        Returns:
            VAPI call response
        """
        try:
            logger.info("VAPI AGENT SINGLE")

            # Validate required environment variables
            if not self.api_key:
                raise ValueError("VAPI_API_KEY environment variable is required")
            if not self.assistant_id:
                raise ValueError("VAPI_ASSISTANT_ID environment variable is required")

            # Ensure driver_data is a list for consistent processing
            drivers_array = driver_data if isinstance(driver_data, list) else [driver_data]

            # Validate that we have at least one driver
            if len(drivers_array) == 0:
                raise ValueError("At least one driver must be provided")

            # Map driver data to VAPI campaign format with multiple customers
            customers = []
            for driver in drivers_array:
                # Validate required driver fields
                if not all(key in driver for key in ['phoneNumber', 'firstName', 'lastName']):
                    raise ValueError("Driver must have phoneNumber, firstName, and lastName")

                # Extract vapi_data if present
                vapi_data = driver.get('vapi_data', {})
                
                # Build variable values, prioritizing vapi_data over driver data
                variable_values = {
                    "driverFirstName": driver['firstName'],
                    "driverId": driver.get('id') or driver.get('driverId') or f"driver_{hash(str(driver))}",
                    "currentLocation": vapi_data.get('currentLocation') or driver.get('currentLocation', 'Los Angeles, CA'),
                    "milesRemaining": str(vapi_data.get('milesLeft') or driver.get('milesRemaining', '100')),
                    "deliveryType": vapi_data.get('deliveryType') or driver.get('deliveryType', ''),
                }
                
                # Add all additional vapi_data fields if present
                if vapi_data:
                    additional_fields = {
                        "tripId": vapi_data.get('tripId'),
                        "driverName": vapi_data.get('driverName'),
                        "speed": vapi_data.get('speed'),
                        "eta": vapi_data.get('eta'),
                        "deliveryTime": vapi_data.get('deliveryTime'),
                        "destination": vapi_data.get('destination'),
                        "loadingLocation": vapi_data.get('loadingLocation'),
                        "onTimeStatus": vapi_data.get('onTimeStatus'),
                        "delayReason": vapi_data.get('delayReason'),
                        "loadGroup": vapi_data.get('loadGroup'),
                        "tripStatus": vapi_data.get('tripStatus'),
                        "subStatus": vapi_data.get('subStatus'),
                        "driverFeeling": vapi_data.get('driverFeeling'),
                        "pickupTime": vapi_data.get('pickupTime'),
                        "lateAfterTime": vapi_data.get('lateAfterTime'),
                        "additionalNotes": vapi_data.get('additionalNotes'),
                    }
                    # Add only non-None values
                    variable_values.update({k: v for k, v in additional_fields.items() if v is not None})
                
                customers.append({
                    "number": driver['phoneNumber'],  # Using driver's real phone number
                    "name": f"{driver['firstName']} {driver['lastName']}",
                    "assistantOverrides": {
                        "variableValues": variable_values,
                    },
                })

            # Prepare VAPI campaign request with multiple customers
            request_body = {
                "name": "Daily Driver Check-in",
                "phoneNumberId": getattr(settings, 'VAPI_PHONENUMBER_ID', ''),
                "customers": customers,
                "assistantId": self.assistant_id,
            }

            logger.info(f"📞 Initiating VAPI campaign call to {len(customers)} driver(s)")
            for i, customer in enumerate(customers):
                logger.info(f"   {i + 1}. {customer['name']} ({customer['number']})")

            # Make API call to VAPI campaign endpoint
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/campaign",
                    json=request_body,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0
                )

                if response.status_code >= 400:
                    raise Exception(f"VAPI API Error: {response.status_code} - {response.text}")

                response_data = response.json()

            logger.info(f"✅ VAPI campaign initiated successfully. Campaign ID: {response_data.get('id')}")

            return {
                "success": True,
                "campaignId": response_data.get("id"),
                "callId": response_data.get("id"),  # For backward compatibility
                "status": response_data.get("status", "initiated"),
                "customerCount": len(customers),
                "customers": [
                    {
                        "name": customer["name"],
                        "number": customer["number"],
                        "driverId": customer["assistantOverrides"]["variableValues"]["driverId"],
                    }
                    for customer in customers
                ],
            }

        except Exception as error:
            logger.error(f"❌ Error creating VAPI call: {str(error)}")

            # Handle different error types
            if "VAPI API Error" in str(error):
                raise Exception(f"VAPI API Error: {str(error)}")
            elif isinstance(error, httpx.TimeoutException):
                raise Exception("Network error: Unable to reach VAPI API")
            else:
                raise error

    async def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """
        Get call status from VAPI
        Args:
            call_id: VAPI call ID
        Returns:
            Call status information
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/call/{call_id}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=10.0
                )

                if response.status_code >= 400:
                    raise Exception(f"VAPI API Error: {response.status_code} - {response.text}")

                return response.json()

        except Exception as error:
            logger.error(f"❌ Error getting call status for {call_id}: {str(error)}")
            raise error


# Global instance
vapi_client = VAPIClient()