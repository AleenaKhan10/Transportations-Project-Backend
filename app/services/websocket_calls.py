"""
WebSocket endpoint for real-time call transcription updates.

This module provides a WebSocket endpoint for clients to subscribe to call updates
and receive real-time transcription messages and call completion notifications.

Endpoint: /ws/calls/transcriptions
Authentication: JWT token via query parameter
Protocol: JSON messages for subscribe/unsubscribe and server notifications

Reference: agent-os/specs/2025-11-21-elevenlabs-completion-webhook-websocket/spec.md
"""

import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from fastapi.responses import JSONResponse
from jose import jwt, JWTError

from config import settings
from models.websocket_messages import (
    SubscriptionConfirmedMessage,
    UnsubscribeConfirmedMessage,
    ErrorMessage
)
from services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws/calls", tags=["websockets"])


async def validate_jwt_token(token: str) -> dict:
    """
    Validate JWT token and return user information.

    Args:
        token: JWT token string to validate

    Returns:
        dict: User information with user_id and username

    Raises:
        ValueError: If token is invalid or expired

    Pattern follows get_current_user() from logic/auth/security.py but adapted for WebSocket
    """
    try:
        # Decode JWT token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        jti: str = payload.get("jti")  # JWT ID

        if username is None:
            raise ValueError("Token missing username")

        # Check token status (same pattern as get_current_user)
        if jti:
            from logic.auth.service import TokenStatusService
            token_status = TokenStatusService.get_token_status(jti)

            if token_status == "revoked":
                raise ValueError("Token has been revoked")
            elif token_status == "expired":
                raise ValueError("Token has expired")
            elif token_status == "not_found":
                raise ValueError("Invalid token")

        # Look up user from database
        from models.user import User
        from db.database import engine
        from sqlmodel import Session, select

        with Session(engine) as session:
            statement = select(User).where(User.username == username)
            user = session.exec(statement).first()

            if not user:
                raise ValueError(f"User not found: {username}")

            return {
                "user_id": str(user.id),
                "username": user.username
            }

    except JWTError as e:
        raise ValueError(f"JWT decode error: {str(e)}")
    except Exception as e:
        raise ValueError(f"Authentication error: {str(e)}")


@router.websocket("/transcriptions")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token")
):
    """
    WebSocket endpoint for real-time call transcription updates.

    This endpoint accepts WebSocket connections after JWT authentication and allows
    clients to subscribe to call updates. Clients receive real-time transcription
    messages and call completion notifications.

    Query Parameters:
        token: JWT authentication token (required)

    Message Protocol:
        Client -> Server:
            - {"subscribe": "call_sid_or_conversation_id"}
            - {"unsubscribe": "call_sid_or_conversation_id"}

        Server -> Client:
            - {"type": "subscription_confirmed", ...}
            - {"type": "unsubscribe_confirmed", ...}
            - {"type": "transcription", ...}
            - {"type": "call_status", ...}
            - {"type": "call_completed", ...}
            - {"type": "error", ...}

    Example:
        const ws = new WebSocket('ws://localhost:8000/ws/calls/transcriptions?token=<jwt_token>');
        ws.onopen = () => ws.send(JSON.stringify({"subscribe": "EL_driver123_1732199700"}));
        ws.onmessage = (event) => console.log(JSON.parse(event.data));

    Reference: Spec lines 456-497, tasks.md lines 452-562
    """
    connection_id = None

    try:
        # Validate JWT token before accepting connection
        logger.info("=" * 80)
        logger.info("WebSocket connection attempt - validating JWT token")

        try:
            user = await validate_jwt_token(token)
            logger.info(f"JWT validation successful - user: {user['username']}")
        except ValueError as e:
            logger.warning(f"JWT validation failed: {str(e)}")
            # Reject connection with 403 Forbidden
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
            return

        # Accept connection and register with manager
        logger.info(f"Accepting WebSocket connection for user: {user['username']}")
        connection_id = await websocket_manager.connect(websocket, user)
        logger.info(f"WebSocket connection established - connection_id: {connection_id}")

        # Message receive loop
        while True:
            try:
                # Receive JSON message from client
                data = await websocket.receive_json()
                logger.debug(f"Received message from {connection_id}: {data}")

                # Route message based on type
                if "subscribe" in data:
                    # Handle subscription request
                    identifier = data["subscribe"]
                    logger.info(f"Processing subscribe request - identifier: {identifier}, connection: {connection_id}")

                    try:
                        call = await websocket_manager.subscribe(connection_id, identifier)

                        # Send subscription confirmation
                        confirmation = SubscriptionConfirmedMessage(
                            identifier=identifier,
                            call_sid=call.call_sid,
                            conversation_id=call.conversation_id,
                            status=call.status.value if call.status else "unknown",
                            message="Successfully subscribed to call updates"
                        )
                        await websocket.send_json(confirmation.model_dump())
                        logger.info(
                            f"Subscription confirmed - identifier: {identifier}, "
                            f"call_sid: {call.call_sid}, connection: {connection_id}"
                        )

                    except ValueError as e:
                        # Call not found or invalid identifier
                        error_msg = ErrorMessage(
                            message=str(e),
                            code="CALL_NOT_FOUND"
                        )
                        await websocket.send_json(error_msg.model_dump())
                        logger.warning(f"Subscription failed - {str(e)}, connection: {connection_id}")

                elif "unsubscribe" in data:
                    # Handle unsubscribe request
                    identifier = data["unsubscribe"]
                    logger.info(f"Processing unsubscribe request - identifier: {identifier}, connection: {connection_id}")

                    await websocket_manager.unsubscribe(connection_id, identifier)

                    # Send unsubscribe confirmation
                    confirmation = UnsubscribeConfirmedMessage(
                        identifier=identifier,
                        message="Successfully unsubscribed from call updates"
                    )
                    await websocket.send_json(confirmation.model_dump())
                    logger.info(f"Unsubscribe confirmed - identifier: {identifier}, connection: {connection_id}")

                else:
                    # Invalid message format
                    error_msg = ErrorMessage(
                        message="Invalid message format. Expected 'subscribe' or 'unsubscribe' key.",
                        code="INVALID_MESSAGE_FORMAT"
                    )
                    await websocket.send_json(error_msg.model_dump())
                    logger.warning(f"Invalid message format from connection: {connection_id}, data: {data}")

            except json.JSONDecodeError as e:
                # Invalid JSON
                error_msg = ErrorMessage(
                    message=f"Invalid JSON format: {str(e)}",
                    code="INVALID_MESSAGE_FORMAT"
                )
                await websocket.send_json(error_msg.model_dump())
                logger.warning(f"JSON decode error from connection: {connection_id}, error: {str(e)}")

            except ValueError as e:
                # ValueError from message processing
                error_msg = ErrorMessage(
                    message=str(e),
                    code="SUBSCRIPTION_FAILED"
                )
                await websocket.send_json(error_msg.model_dump())
                logger.warning(f"Message processing error - connection: {connection_id}, error: {str(e)}")

    except WebSocketDisconnect:
        # Normal disconnection
        logger.info(f"WebSocket disconnected normally - connection: {connection_id}")

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error in WebSocket handler - connection: {connection_id}, error: {str(e)}", exc_info=True)

    finally:
        # Always cleanup connection
        if connection_id:
            await websocket_manager.disconnect(connection_id)
            logger.info(f"WebSocket connection cleanup complete - connection: {connection_id}")
        logger.info("=" * 80)
