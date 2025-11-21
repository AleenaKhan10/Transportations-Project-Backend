"""
WebSocket Connection Manager for managing active WebSocket connections and subscriptions.

This module provides a centralized manager for tracking WebSocket connections,
managing subscriptions to call updates, and broadcasting messages to subscribed clients.

Architecture:
- In-memory storage of connections, subscriptions, and metadata
- Auto-detection of call identifiers (call_sid vs conversation_id)
- Graceful handling of dead connections during broadcasts
- Support for multiple clients subscribing to the same call
- Support for single client subscribing to multiple calls
"""

import logging
import uuid
import json
from typing import Dict, Set, Optional
from datetime import datetime, timezone
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from models.call import Call

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """
    Manages active WebSocket connections and subscriptions.

    This class provides centralized management of WebSocket connections for real-time
    call updates. It handles connection lifecycle, subscription management, and
    message broadcasting to subscribed clients.

    Attributes:
        connections: Dict mapping connection_id (UUID) to WebSocket connection object
        subscriptions: Dict mapping call_identifier (call_sid or conversation_id) to Set of connection_ids
        connection_metadata: Dict mapping connection_id to metadata dict (user info, subscribed calls)

    Thread Safety:
        This implementation is designed for single-process deployment.
        For multi-instance deployments, use Redis Pub/Sub for distributed subscriptions.
    """

    def __init__(self):
        """Initialize the WebSocket connection manager with empty state."""
        self.connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}
        self.connection_metadata: Dict[str, dict] = {}
        logger.info("WebSocketConnectionManager initialized")

    async def connect(self, websocket: WebSocket, user: dict) -> str:
        """
        Accept WebSocket connection and register it with metadata.

        Args:
            websocket: WebSocket connection object to accept and register
            user: User dict containing user_id and username from JWT authentication

        Returns:
            str: Unique connection_id (UUID) for this connection

        Example:
            connection_id = await manager.connect(websocket, {"user_id": "123", "username": "user@example.com"})
        """
        # Generate unique connection ID
        connection_id = str(uuid.uuid4())

        # Accept the WebSocket connection
        await websocket.accept()

        # Store connection
        self.connections[connection_id] = websocket

        # Store metadata
        self.connection_metadata[connection_id] = {
            "user_id": user.get("user_id"),
            "username": user.get("username"),
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "subscribed_calls": set()
        }

        logger.info(
            f"WebSocket connection established: {connection_id} "
            f"(user: {user.get('username')}, total_connections: {len(self.connections)})"
        )

        return connection_id

    async def disconnect(self, connection_id: str):
        """
        Clean up connection and remove all subscriptions.

        This method performs complete cleanup when a client disconnects:
        - Removes connection from connections dict
        - Removes all subscriptions for this connection
        - Removes metadata for this connection

        Args:
            connection_id: UUID of the connection to disconnect

        Note:
            This method is idempotent - safe to call multiple times for same connection.
        """
        # Remove all subscriptions for this connection
        subscribed_calls = self.connection_metadata.get(connection_id, {}).get("subscribed_calls", set())
        for identifier in list(subscribed_calls):
            # Remove connection from subscription set
            if identifier in self.subscriptions:
                self.subscriptions[identifier].discard(connection_id)
                # Clean up empty subscription sets
                if not self.subscriptions[identifier]:
                    del self.subscriptions[identifier]

        # Remove connection
        if connection_id in self.connections:
            del self.connections[connection_id]

        # Remove metadata
        if connection_id in self.connection_metadata:
            username = self.connection_metadata[connection_id].get("username")
            del self.connection_metadata[connection_id]
            logger.info(
                f"WebSocket connection disconnected: {connection_id} "
                f"(user: {username}, remaining_connections: {len(self.connections)})"
            )

    async def subscribe(self, connection_id: str, identifier: str) -> Call:
        """
        Subscribe connection to a call's updates with auto-detection.

        This method auto-detects whether the identifier is a call_sid or conversation_id
        and subscribes the connection to receive updates for that call.

        Auto-detection logic:
        1. Try Call.get_by_call_sid() first (if identifier starts with "EL_")
        2. Try Call.get_by_conversation_id() if not found
        3. Raise ValueError if Call not found

        Dual-mapping strategy:
        - Store subscription under both call_sid AND conversation_id
        - Enables broadcasts from webhooks using either identifier
        - Transcription webhook has call_sid -> broadcasts work
        - Post-call webhook has conversation_id -> broadcasts work

        Args:
            connection_id: UUID of the connection to subscribe
            identifier: Call identifier (call_sid or conversation_id)

        Returns:
            Call: Resolved Call object

        Raises:
            ValueError: If identifier doesn't match any Call record

        Example:
            call = await manager.subscribe("conn-uuid", "EL_driver123_1732199700")
            call = await manager.subscribe("conn-uuid", "abc123xyz")
        """
        # Auto-detect identifier type and resolve to Call
        call = None

        # Try call_sid first (preferred identifier format starts with "EL_")
        if identifier.startswith("EL_"):
            call = Call.get_by_call_sid(identifier)

        # Try conversation_id if not found by call_sid
        if not call:
            call = Call.get_by_conversation_id(identifier)

        # Raise error if Call not found
        if not call:
            logger.warning(
                f"Subscription failed - Call not found: {identifier} "
                f"(connection: {connection_id})"
            )
            raise ValueError(f"Call not found for identifier: {identifier}")

        # Add subscription under call_sid (always present)
        if call.call_sid not in self.subscriptions:
            self.subscriptions[call.call_sid] = set()
        self.subscriptions[call.call_sid].add(connection_id)

        # Add subscription under conversation_id (if present)
        if call.conversation_id:
            if call.conversation_id not in self.subscriptions:
                self.subscriptions[call.conversation_id] = set()
            self.subscriptions[call.conversation_id].add(connection_id)

        # Update connection metadata
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["subscribed_calls"].add(identifier)

        logger.info(
            f"Subscription added: {identifier} -> {connection_id} "
            f"(call_sid: {call.call_sid}, conversation_id: {call.conversation_id}, "
            f"subscribers: {len(self.subscriptions.get(call.call_sid, set()))})"
        )

        return call

    async def unsubscribe(self, connection_id: str, identifier: str):
        """
        Unsubscribe connection from a call's updates.

        This method removes the subscription for a specific identifier while keeping
        other subscriptions intact. Uses same auto-detection logic as subscribe().

        Args:
            connection_id: UUID of the connection to unsubscribe
            identifier: Call identifier (call_sid or conversation_id) to unsubscribe from

        Note:
            Gracefully handles cases where subscription doesn't exist (no-op).

        Example:
            await manager.unsubscribe("conn-uuid", "EL_driver123_1732199700")
        """
        # Auto-detect identifier type and resolve to Call
        call = None

        # Try call_sid first
        if identifier.startswith("EL_"):
            call = Call.get_by_call_sid(identifier)

        # Try conversation_id if not found
        if not call:
            call = Call.get_by_conversation_id(identifier)

        # If Call not found, nothing to unsubscribe from
        if not call:
            logger.debug(f"Unsubscribe - Call not found: {identifier} (connection: {connection_id})")
            return

        # Remove subscription from call_sid
        if call.call_sid in self.subscriptions:
            self.subscriptions[call.call_sid].discard(connection_id)
            # Clean up empty subscription sets
            if not self.subscriptions[call.call_sid]:
                del self.subscriptions[call.call_sid]

        # Remove subscription from conversation_id
        if call.conversation_id and call.conversation_id in self.subscriptions:
            self.subscriptions[call.conversation_id].discard(connection_id)
            # Clean up empty subscription sets
            if not self.subscriptions[call.conversation_id]:
                del self.subscriptions[call.conversation_id]

        # Update connection metadata
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["subscribed_calls"].discard(identifier)

        logger.info(
            f"Subscription removed: {identifier} -> {connection_id} "
            f"(call_sid: {call.call_sid}, remaining_subscribers: {len(self.subscriptions.get(call.call_sid, set()))})"
        )

    async def broadcast_to_call(self, call: Call, message: dict):
        """
        Broadcast message to all connections subscribed to a call.

        This method sends a message to all WebSocket clients subscribed to updates
        for the given call. It handles broadcasts using both call_sid and conversation_id
        to support subscriptions via either identifier.

        Dead connection handling:
        - Automatically removes dead connections on send failure
        - Logs removal but doesn't raise exceptions
        - Ensures broadcast continues to other clients

        Args:
            call: Call object containing call_sid and conversation_id
            message: Dict message to send (will be JSON-serialized)

        Example:
            await manager.broadcast_to_call(
                call,
                {"type": "transcription", "message_text": "Hello"}
            )
        """
        # Collect all connection_ids subscribed to this call (via call_sid or conversation_id)
        connection_ids = set()

        # Add subscribers by call_sid
        if call.call_sid and call.call_sid in self.subscriptions:
            connection_ids.update(self.subscriptions[call.call_sid])

        # Add subscribers by conversation_id (if present)
        if call.conversation_id and call.conversation_id in self.subscriptions:
            connection_ids.update(self.subscriptions[call.conversation_id])

        if not connection_ids:
            logger.debug(
                f"No subscribers for call broadcast: call_sid={call.call_sid}, "
                f"conversation_id={call.conversation_id}"
            )
            return

        # Track successful/failed sends
        successful_sends = 0
        failed_sends = 0
        dead_connections = []

        # Send message to all subscribed connections
        for connection_id in connection_ids:
            if connection_id not in self.connections:
                # Connection already removed, skip
                dead_connections.append(connection_id)
                continue

            websocket = self.connections[connection_id]

            try:
                await websocket.send_json(message)
                successful_sends += 1
            except WebSocketDisconnect:
                # Connection died, mark for cleanup
                logger.debug(f"Dead connection detected during broadcast: {connection_id}")
                dead_connections.append(connection_id)
                failed_sends += 1
            except Exception as e:
                # Unexpected error sending message
                logger.error(f"Error broadcasting to connection {connection_id}: {e}")
                dead_connections.append(connection_id)
                failed_sends += 1

        # Clean up dead connections
        for connection_id in dead_connections:
            await self.disconnect(connection_id)

        logger.info(
            f"Broadcast completed: call_sid={call.call_sid}, "
            f"message_type={message.get('type', 'unknown')}, "
            f"successful={successful_sends}, failed={failed_sends}, "
            f"total_recipients={len(connection_ids)}"
        )

    async def broadcast_transcription(
        self,
        call_sid: str,
        transcription_id: int,
        sequence_number: int,
        speaker: str,
        message: str,
        timestamp: datetime
    ):
        """
        Broadcast new transcription to subscribed WebSocket clients.

        This method is called by the transcription webhook after successfully saving
        a new dialogue turn to the database. It builds a TranscriptionMessage and
        broadcasts it to all clients subscribed to the call.

        Integration Point:
        - Called from services/webhooks_elevenlabs.py after save_transcription()
        - Must succeed even if no clients are subscribed (graceful no-op)
        - Failures are logged but don't propagate exceptions

        Args:
            call_sid: Our generated call identifier (format: EL_{driverId}_{timestamp})
            transcription_id: Database ID of the transcription record
            sequence_number: Sequence number in the conversation
            speaker: Speaker attribution - 'agent' or 'user'
            message: The dialogue message text
            timestamp: Timezone-aware UTC datetime when message occurred

        Example:
            await manager.broadcast_transcription(
                call_sid="EL_driver123_1732199700",
                transcription_id=456,
                sequence_number=3,
                speaker="agent",
                message="Hello, how are you?",
                timestamp=datetime.now(timezone.utc)
            )

        Reference:
            - Spec lines 582-607 for TranscriptionMessage format
            - Spec lines 785-803 for integration details
        """
        # Look up Call by call_sid
        call = Call.get_by_call_sid(call_sid)
        if not call:
            logger.warning(
                f"Cannot broadcast transcription - Call not found for call_sid: {call_sid}"
            )
            return

        # Map speaker from ElevenLabs format ('agent', 'user') to our format ('agent', 'driver')
        speaker_type = "agent" if speaker == "agent" else "driver"

        # Build TranscriptionMessage
        from models.websocket_messages import TranscriptionMessage

        transcription_message = TranscriptionMessage(
            type="transcription",
            conversation_id=call.conversation_id or "",
            call_sid=call.call_sid,
            transcription_id=transcription_id,
            sequence_number=sequence_number,
            speaker_type=speaker_type,
            message_text=message,
            timestamp=timestamp
        )

        # Convert to dict for JSON serialization
        message_dict = transcription_message.dict()

        # Convert datetime to ISO string for JSON serialization
        if "timestamp" in message_dict and isinstance(message_dict["timestamp"], datetime):
            message_dict["timestamp"] = message_dict["timestamp"].isoformat()

        # Broadcast to all subscribed clients
        await self.broadcast_to_call(call, message_dict)

        logger.info(
            f"Transcription broadcast completed: call_sid={call_sid}, "
            f"transcription_id={transcription_id}, sequence={sequence_number}"
        )

    async def broadcast_call_completion(self, conversation_id: str, call: Call):
        """
        Broadcast call completion to subscribed WebSocket clients.

        This method is called by the post-call webhook after successfully updating
        the Call record with completion metadata. It sends two sequential messages:
        1. CallStatusMessage - Status update with completion timestamp
        2. CallCompletedMessage - Full call data with analysis and metadata

        Two-Message Protocol:
        - Message 1 (status): Immediate notification that call completed
        - Message 2 (data): Complete call information with analysis/metadata
        - Sequential delivery ensures clients receive status before full data

        After broadcasting, removes completed call from active subscriptions
        (clients automatically unsubscribed as call is complete).

        Integration Point:
        - Called from services/webhooks_elevenlabs.py after update_post_call_data()
        - Must succeed even if no clients are subscribed (graceful no-op)
        - Failures are logged but don't propagate exceptions

        Args:
            conversation_id: ElevenLabs conversation identifier
            call: Updated Call object with post-call metadata

        Example:
            await manager.broadcast_call_completion(
                conversation_id="abc123xyz",
                call=updated_call
            )

        Reference:
            - Spec lines 610-682 for message formats
            - Spec lines 810-826 for integration details
        """
        logger.info(
            f"Starting call completion broadcast: conversation_id={conversation_id}, "
            f"call_sid={call.call_sid}, status={call.status}"
        )

        # Build CallStatusMessage (first message)
        from models.websocket_messages import CallStatusMessage

        status_message = CallStatusMessage(
            type="call_status",
            conversation_id=conversation_id,
            call_sid=call.call_sid,
            status=call.status.value if hasattr(call.status, 'value') else str(call.status),
            call_end_time=call.call_end_time
        )

        # Convert to dict for JSON serialization
        status_dict = status_message.dict()

        # Convert datetime to ISO string for JSON serialization
        if "call_end_time" in status_dict and status_dict["call_end_time"]:
            if isinstance(status_dict["call_end_time"], datetime):
                status_dict["call_end_time"] = status_dict["call_end_time"].isoformat()

        # Broadcast status message (first message)
        await self.broadcast_to_call(call, status_dict)
        logger.info(f"Broadcasted call_status message: conversation_id={conversation_id}")

        # Build CallCompletedMessage (second message) with full call_data
        from models.websocket_messages import CallCompletedMessage

        # Parse JSON strings back to objects for call_data
        analysis_data = None
        metadata = None

        if call.analysis_data:
            try:
                analysis_data = json.loads(call.analysis_data)
            except Exception as e:
                logger.warning(f"Failed to parse analysis_data: {e}")

        if call.metadata_json:
            try:
                metadata = json.loads(call.metadata_json)
            except Exception as e:
                logger.warning(f"Failed to parse metadata_json: {e}")

        # Build call_data dict with all fields
        call_data = {
            "status": call.status.value if hasattr(call.status, 'value') else str(call.status),
            "driver_id": call.driver_id,
            "call_sid": call.call_sid,
            "conversation_id": call.conversation_id,
            "call_start_time": call.call_start_time.isoformat() if call.call_start_time else None,
            "call_end_time": call.call_end_time.isoformat() if call.call_end_time else None,
            "duration_seconds": call.call_duration_seconds,
            "transcript_summary": call.transcript_summary,
            "cost": call.cost,
            "call_successful": call.call_successful,
            "analysis_data": analysis_data,
            "metadata": metadata
        }

        completed_message = CallCompletedMessage(
            type="call_completed",
            conversation_id=conversation_id,
            call_sid=call.call_sid,
            call_data=call_data
        )

        # Convert to dict for JSON serialization
        completed_dict = completed_message.dict()

        # Broadcast completed message (second message)
        await self.broadcast_to_call(call, completed_dict)
        logger.info(f"Broadcasted call_completed message: conversation_id={conversation_id}")

        # Remove completed call from active subscriptions
        # (Cleanup subscriptions for both call_sid and conversation_id)
        if call.call_sid in self.subscriptions:
            del self.subscriptions[call.call_sid]
            logger.debug(f"Removed call_sid subscriptions: {call.call_sid}")

        if call.conversation_id and call.conversation_id in self.subscriptions:
            del self.subscriptions[call.conversation_id]
            logger.debug(f"Removed conversation_id subscriptions: {call.conversation_id}")

        logger.info(
            f"Call completion broadcast completed: conversation_id={conversation_id}, "
            f"call_sid={call.call_sid}, messages_sent=2"
        )


# Global singleton instance
websocket_manager = WebSocketConnectionManager()
