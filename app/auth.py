import json
from urllib.request import Request
from config import Config
from fastapi import Header, HTTPException, status

def verify_token(x_api_key: str = Header(..., description="Your secret API token.")):
    """
    Dependency to verify the secret token in the X-Auth-Token header.
    """
    if x_api_key != Config.DUMMY_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing API token")