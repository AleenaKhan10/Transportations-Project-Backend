import httpx
import asyncio
from typing import Dict, Any
from config import settings
from helpers import logger


class ElevenLabsClient:
    """
    Client for interacting with ElevenLabs Conversational AI API.

    This client handles outbound call creation with retry logic and comprehensive error handling.
    Agent ID and phone number ID are hardcoded as class variables for now.
    """

    # Hardcoded agent configuration (future: configurable from frontend)
    AGENT_ID = "agent_4801k9zn5r98ebwswz663qj0tdzn"
    AGENT_PHONE_NUMBER_ID = "phnum_5601kady6emcepp9y1tzbs86kf4q"

    # Retry configuration
    MAX_RETRIES = 3

    def __init__(self):
        """Initialize ElevenLabs client with API configuration."""
        self.base_url = "https://api.elevenlabs.io/v1/convai"
        # self.api_key = settings.ELEVENLABS_API_KEY
        self.api_key = "35740cee374db8d2c5ffec1a4f64871a"

        # Validate API key is configured
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable is required")

    async def create_outbound_call(
        self,
        to_number: str,
        prompt: str,
        transfer_to: str,
        call_sid: str,
        dispatcher_name: str,
        driver_id: str = None,
    ) -> Dict[str, Any]:
        """
        Create an outbound call via ElevenLabs API.

        Args:
            to_number: Phone number to call in E.164 format (e.g., +14155551234)
            prompt: Dynamic prompt text for the conversation
            transfer_to: Transfer destination phone number
            call_sid: Call session identifier
            dispatcher_name: Name of the dispatcher initiating the call
            driver_id: Driver identifier for the conversation context

        Returns:
            Dictionary containing API response with conversation_id and callSid

        Raises:
            Exception: If API call fails after retries or encounters unrecoverable error
        """
        # Build the request payload
        payload = {
            "agent_id": self.AGENT_ID,
            "agent_phone_number_id": self.AGENT_PHONE_NUMBER_ID,
            "to_number": to_number,
            "conversation_initiation_client_data": {
                "dynamic_variables": {
                    "prompt": prompt,
                    "transfer_to": transfer_to,
                    "call_sid": call_sid,
                    "dispatcher_name": dispatcher_name,
                    "driver_id": driver_id,
                }
            },
        }

        logger.info(f"Initiating ElevenLabs outbound call to {to_number}")
        logger.info(
            f"Call parameters: call_sid={call_sid}, dispatcher={dispatcher_name}"
        )

        # Log outgoing payload (full structure for debugging)
        logger.info("=" * 100)
        logger.info("ELEVENLABS API REQUEST PAYLOAD")
        logger.info("=" * 100)
        logger.info(f"Agent ID: {self.AGENT_ID}")
        logger.info(f"Phone Number ID: {self.AGENT_PHONE_NUMBER_ID}")
        logger.info(f"To Number: {to_number}")
        logger.info(f"Prompt Length: {len(prompt)} characters")
        logger.info("=" * 100)

        # Implement retry logic with exponential backoff
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/twilio/outbound-call",
                        json=payload,
                        headers={
                            "xi-api-key": self.api_key,
                            "Content-Type": "application/json",
                        },
                        timeout=30.0,
                    )

                    # Check for HTTP errors
                    if response.status_code >= 400:
                        error_msg = f"ElevenLabs API Error: {response.status_code} - {response.text}"
                        logger.error(error_msg)
                        raise Exception(error_msg)

                    # Parse successful response
                    response_data = response.json()

                    # Log successful response
                    logger.info("=" * 100)
                    logger.info("ELEVENLABS API RESPONSE - SUCCESS")
                    logger.info("=" * 100)
                    logger.info(
                        f"Conversation ID: {response_data.get('conversation_id', 'N/A')}"
                    )
                    logger.info(f"Call SID: {response_data.get('callSid', 'N/A')}")
                    logger.info("=" * 100)

                    return response_data

            except httpx.TimeoutException as timeout_error:
                logger.error(
                    f"Timeout on attempt {attempt}/{self.MAX_RETRIES}: Unable to reach ElevenLabs API"
                )

                if attempt < self.MAX_RETRIES:
                    # Exponential backoff: 2^attempt seconds
                    delay = 2**attempt
                    logger.info(
                        f"Retrying in {delay} seconds... (attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("All retry attempts exhausted for ElevenLabs API call")
                    raise Exception(
                        "Network error: Unable to reach ElevenLabs API after multiple retries"
                    )

            except httpx.HTTPError as http_error:
                logger.error(
                    f"HTTP error on attempt {attempt}/{self.MAX_RETRIES}: {str(http_error)}"
                )

                if attempt < self.MAX_RETRIES:
                    delay = 2**attempt
                    logger.info(
                        f"Retrying in {delay} seconds... (attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("All retry attempts exhausted for ElevenLabs API call")
                    raise Exception(f"HTTP error: {str(http_error)}")

            except Exception as error:
                # Log the error with details
                logger.error(
                    f"Error creating ElevenLabs call on attempt {attempt}/{self.MAX_RETRIES}: {str(error)}"
                )

                # Check if this is an API error (already formatted)
                if "ElevenLabs API Error" in str(error):
                    # Don't retry on API errors (4xx/5xx responses)
                    raise error

                # Retry on other errors
                if attempt < self.MAX_RETRIES:
                    delay = 2**attempt
                    logger.info(
                        f"Retrying in {delay} seconds... (attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("All retry attempts exhausted for ElevenLabs API call")
                    raise error

        # Should not reach here, but safety fallback
        raise Exception("Failed to create ElevenLabs call after all retry attempts")

    async def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Retrieve conversation details from ElevenLabs API.

        This method fetches comprehensive conversation data including:
        - Call metadata (status, duration, timestamps)
        - Full transcript with speaker attribution
        - Analysis results (summary, sentiment, etc.)
        - Recording URL

        Args:
            conversation_id: ElevenLabs conversation identifier

        Returns:
            Dictionary containing complete conversation data

        Raises:
            Exception: If API call fails or conversation not found
        """
        logger.info(f"Fetching conversation details for: {conversation_id}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/conversations/{conversation_id}",
                    headers={
                        "xi-api-key": self.api_key,
                    },
                    timeout=30.0,
                )

                # Check for HTTP errors
                if response.status_code == 404:
                    error_msg = f"Conversation not found: {conversation_id}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                elif response.status_code >= 400:
                    error_msg = f"ElevenLabs API Error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

                # Parse successful response
                conversation_data = response.json()

                # Log successful response
                logger.info("=" * 100)
                logger.info("ELEVENLABS CONVERSATION DATA - SUCCESS")
                logger.info("=" * 100)
                logger.info(
                    f"Conversation ID: {conversation_data.get('conversation_id', 'N/A')}"
                )
                logger.info(f"Status: {conversation_data.get('status', 'N/A')}")

                # Log transcript info if available
                transcript = conversation_data.get("transcript", [])
                if transcript:
                    logger.info(f"Transcript Messages: {len(transcript)}")

                # Log metadata if available
                metadata = conversation_data.get("metadata", {})
                if metadata:
                    call_duration = metadata.get("call_duration_secs", 0)
                    logger.info(f"Call Duration: {call_duration} seconds")

                logger.info("=" * 100)

                return conversation_data

        except httpx.TimeoutException as timeout_error:
            logger.error(
                f"Timeout: Unable to reach ElevenLabs API for conversation {conversation_id}"
            )
            raise Exception("Network error: Unable to reach ElevenLabs API")

        except httpx.HTTPError as http_error:
            logger.error(
                f"HTTP error fetching conversation {conversation_id}: {str(http_error)}"
            )
            raise Exception(f"HTTP error: {str(http_error)}")

        except Exception as error:
            logger.error(f"Error fetching conversation {conversation_id}: {str(error)}")
            raise error


# Global instance
elevenlabs_client = ElevenLabsClient()
