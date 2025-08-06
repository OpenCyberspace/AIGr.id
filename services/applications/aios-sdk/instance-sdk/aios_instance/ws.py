import asyncio
import json
import logging
import uuid
import threading
import websockets
from websockets.exceptions import ConnectionClosed
import time
import socket
from .aios_packet_pb2 import AIOSPacket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebsocketStreamingManager:
    def __init__(self, handler_function, port=18002):
        self.handler_function = handler_function
        self.port = port
        self.session_map = {}  # session_id -> websocket
        self.server = None
        self.loop = None

    def websocket_handler(self, session_id, data: dict):
        try:
            packet = AIOSPacket()
            packet.session_id = session_id
            packet.seq_no = int(data.get("seq_no", 0))
            packet.data = data.get("data", "")
            packet.ts = data.get("ts", time.time())

            self.handler_function((packet, packet.ts),
                                  serialized=True, is_ws=True)

        except Exception as e:
            print(f"Failed to handle websocket message from {session_id}: {e}")

    async def _handle_connection(self, websocket, path):
        # Set TCP_NODELAY to disable buffering
        try:
            transport = websocket.transport
            sock = transport.get_extra_info("socket")
            if sock:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                logger.info("TCP_NODELAY set for websocket socket")
        except Exception as e:
            logger.warning(f"Failed to set TCP_NODELAY: {e}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    session_id = data.get('session_id')

                    self.session_map[session_id] = websocket
                    logger.info(f"New WebSocket session started: {session_id}")

                    if 'connect' in data and data['connect']:
                        return

                    self.websocket_handler(session_id, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"error": "Invalid JSON"}))
                except Exception as e:
                    await websocket.send(json.dumps({"error": str(e)}))
        except ConnectionClosed:
            logger.info(f"WebSocket session closed")

    async def _start_server(self):
        self.server = await websockets.serve(
            self._handle_connection, "0.0.0.0", self.port
        )
        logger.info(f"WebSocket server started on port {self.port}")
        await self.server.wait_closed()

    def start(self):
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self._start_server())

    def start_as_thread(self):
        def run():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._start_server())

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        logger.info("WebSocket server started in background thread")

    def write_data(self, session_id, data: dict):
        websocket = self.session_map.get(session_id)
        if not websocket:
            logger.warning(f"Session {session_id} not found for write")
            return

        message = json.dumps(data)

        async def _send_message(ws, msg):
            try:
                await ws.send(msg)
            except Exception as e:
                logger.error(
                    f"Error sending data to session {session_id}: {e}")

        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                _send_message(websocket, message), self.loop
            )
        else:
            logger.error("Async loop is not running. Cannot send data.")
