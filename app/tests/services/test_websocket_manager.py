"""
Tests for WebSocket Connection Manager.

These tests verify the core functionality of the WebSocketConnectionManager class:
- Connection registration and cleanup
- Subscription management with auto-detection
- Broadcasting to subscribed clients
- Dead connection handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from starlette.websockets import WebSocketDisconnect

from services.websocket_manager import WebSocketConnectionManager
from models.call import Call, CallStatus


@pytest.fixture
def manager():
    """Create a fresh WebSocketConnectionManager instance for each test."""
    return WebSocketConnectionManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket object."""
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()
    return websocket


@pytest.fixture
def mock_user():
    """Create a mock user dict."""
    return {
        "user_id": "user123",
        "username": "test@example.com"
    }


@pytest.fixture
def mock_call():
    """Create a mock Call object."""
    call = MagicMock(spec=Call)
    call.id = 1
    call.call_sid = "EL_driver123_1732199700"
    call.conversation_id = "abc123xyz"
    call.status = CallStatus.IN_PROGRESS
    call.driver_id = "driver123"
    call.call_start_time = datetime.now(timezone.utc)
    return call


@pytest.mark.asyncio
async def test_connection_registration(manager, mock_websocket, mock_user):
    """Test that connections are registered correctly with metadata."""
    # Connect WebSocket
    connection_id = await manager.connect(mock_websocket, mock_user)

    # Verify connection registered
    assert connection_id in manager.connections
    assert manager.connections[connection_id] == mock_websocket

    # Verify metadata stored
    assert connection_id in manager.connection_metadata
    metadata = manager.connection_metadata[connection_id]
    assert metadata["user_id"] == "user123"
    assert metadata["username"] == "test@example.com"
    assert "connected_at" in metadata
    assert metadata["subscribed_calls"] == set()

    # Verify WebSocket accepted
    mock_websocket.accept.assert_called_once()


@pytest.mark.asyncio
async def test_disconnection_cleanup(manager, mock_websocket, mock_user, mock_call):
    """Test that disconnection removes connection and all subscriptions."""
    # Connect and subscribe
    connection_id = await manager.connect(mock_websocket, mock_user)

    with patch.object(Call, 'get_by_call_sid', return_value=mock_call):
        await manager.subscribe(connection_id, "EL_driver123_1732199700")

    # Verify subscription exists
    assert "EL_driver123_1732199700" in manager.subscriptions
    assert connection_id in manager.subscriptions["EL_driver123_1732199700"]

    # Disconnect
    await manager.disconnect(connection_id)

    # Verify connection removed
    assert connection_id not in manager.connections
    assert connection_id not in manager.connection_metadata

    # Verify subscriptions cleaned up
    assert "EL_driver123_1732199700" not in manager.subscriptions or \
           connection_id not in manager.subscriptions.get("EL_driver123_1732199700", set())


@pytest.mark.asyncio
async def test_subscription_with_call_sid(manager, mock_websocket, mock_user, mock_call):
    """Test subscription using call_sid identifier."""
    # Connect
    connection_id = await manager.connect(mock_websocket, mock_user)

    # Subscribe using call_sid
    with patch.object(Call, 'get_by_call_sid', return_value=mock_call):
        call = await manager.subscribe(connection_id, "EL_driver123_1732199700")

    # Verify Call returned
    assert call == mock_call

    # Verify subscription stored under call_sid
    assert "EL_driver123_1732199700" in manager.subscriptions
    assert connection_id in manager.subscriptions["EL_driver123_1732199700"]

    # Verify subscription stored under conversation_id
    assert "abc123xyz" in manager.subscriptions
    assert connection_id in manager.subscriptions["abc123xyz"]

    # Verify metadata updated
    assert "EL_driver123_1732199700" in manager.connection_metadata[connection_id]["subscribed_calls"]


@pytest.mark.asyncio
async def test_subscription_with_conversation_id(manager, mock_websocket, mock_user, mock_call):
    """Test subscription using conversation_id identifier."""
    # Connect
    connection_id = await manager.connect(mock_websocket, mock_user)

    # Subscribe using conversation_id (auto-detection fallback)
    with patch.object(Call, 'get_by_call_sid', return_value=None), \
         patch.object(Call, 'get_by_conversation_id', return_value=mock_call):
        call = await manager.subscribe(connection_id, "abc123xyz")

    # Verify Call returned
    assert call == mock_call

    # Verify subscription stored under both identifiers
    assert "EL_driver123_1732199700" in manager.subscriptions
    assert connection_id in manager.subscriptions["EL_driver123_1732199700"]
    assert "abc123xyz" in manager.subscriptions
    assert connection_id in manager.subscriptions["abc123xyz"]


@pytest.mark.asyncio
async def test_subscription_with_invalid_identifier(manager, mock_websocket, mock_user):
    """Test that subscription with invalid identifier raises ValueError."""
    # Connect
    connection_id = await manager.connect(mock_websocket, mock_user)

    # Subscribe with invalid identifier
    with patch.object(Call, 'get_by_call_sid', return_value=None), \
         patch.object(Call, 'get_by_conversation_id', return_value=None):
        with pytest.raises(ValueError, match="Call not found for identifier"):
            await manager.subscribe(connection_id, "invalid_id_123")


@pytest.mark.asyncio
async def test_broadcast_to_multiple_clients(manager, mock_call):
    """Test broadcasting message to multiple subscribed clients."""
    # Create multiple mock WebSockets and users
    websocket1 = AsyncMock()
    websocket1.accept = AsyncMock()
    websocket1.send_json = AsyncMock()

    websocket2 = AsyncMock()
    websocket2.accept = AsyncMock()
    websocket2.send_json = AsyncMock()

    websocket3 = AsyncMock()
    websocket3.accept = AsyncMock()
    websocket3.send_json = AsyncMock()

    user1 = {"user_id": "user1", "username": "user1@example.com"}
    user2 = {"user_id": "user2", "username": "user2@example.com"}
    user3 = {"user_id": "user3", "username": "user3@example.com"}

    # Connect all three clients
    conn_id1 = await manager.connect(websocket1, user1)
    conn_id2 = await manager.connect(websocket2, user2)
    conn_id3 = await manager.connect(websocket3, user3)

    # Subscribe all three to the same call
    with patch.object(Call, 'get_by_call_sid', return_value=mock_call):
        await manager.subscribe(conn_id1, "EL_driver123_1732199700")
        await manager.subscribe(conn_id2, "EL_driver123_1732199700")
        await manager.subscribe(conn_id3, "EL_driver123_1732199700")

    # Broadcast message
    message = {"type": "transcription", "message_text": "Hello"}
    await manager.broadcast_to_call(mock_call, message)

    # Verify all three clients received the message
    websocket1.send_json.assert_called_once_with(message)
    websocket2.send_json.assert_called_once_with(message)
    websocket3.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_broadcast_removes_dead_connections(manager, mock_call):
    """Test that broadcast automatically removes dead connections."""
    # Create two WebSockets - one working, one dead
    websocket_working = AsyncMock()
    websocket_working.accept = AsyncMock()
    websocket_working.send_json = AsyncMock()

    websocket_dead = AsyncMock()
    websocket_dead.accept = AsyncMock()
    websocket_dead.send_json = AsyncMock(side_effect=WebSocketDisconnect())

    user1 = {"user_id": "user1", "username": "user1@example.com"}
    user2 = {"user_id": "user2", "username": "user2@example.com"}

    # Connect both clients
    conn_id_working = await manager.connect(websocket_working, user1)
    conn_id_dead = await manager.connect(websocket_dead, user2)

    # Subscribe both to the same call
    with patch.object(Call, 'get_by_call_sid', return_value=mock_call):
        await manager.subscribe(conn_id_working, "EL_driver123_1732199700")
        await manager.subscribe(conn_id_dead, "EL_driver123_1732199700")

    # Verify both subscribed
    assert len(manager.subscriptions["EL_driver123_1732199700"]) == 2

    # Broadcast message
    message = {"type": "transcription", "message_text": "Hello"}
    await manager.broadcast_to_call(mock_call, message)

    # Verify working connection received message
    websocket_working.send_json.assert_called_once_with(message)

    # Verify dead connection was removed
    assert conn_id_dead not in manager.connections
    assert conn_id_dead not in manager.connection_metadata

    # Verify dead connection removed from subscriptions
    assert conn_id_dead not in manager.subscriptions["EL_driver123_1732199700"]

    # Verify working connection still subscribed
    assert conn_id_working in manager.subscriptions["EL_driver123_1732199700"]
