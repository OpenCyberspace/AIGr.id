import asyncio
import websockets
import logging
import os
import json

# Configure logging
logging.basicConfig(level=logging.INFO)


class WebSocketClient:
    def __init__(self, uri):
        self.uri = uri
        self.websocket = None

    async def connect(self):

        try:
            self.websocket = await websockets.connect(self.uri)
            logging.info(f"Connected to server at {self.uri}")
        except Exception as e:
            logging.error(f"Failed to connect to server: {e}")

    async def send_message(self, message):

        if not self.websocket:
            logging.error("Cannot send message: Not connected to the server.")
            return

        try:
            await self.websocket.send(json.dumps(message))
            logging.info(f"Sent message: {message}")
        except Exception as e:
            logging.error(f"Failed to send message: {e}")

    async def receive_message(self):

        if not self.websocket:
            logging.error(
                "Cannot receive message: Not connected to the server.")
            return

        try:
            response = await self.websocket.recv()
            logging.info(f"Received response: {response}")
            return json.loads(response)
        except Exception as e:
            logging.error(f"Failed to receive message: {e}")

    async def close(self):

        if self.websocket:
            try:
                await self.websocket.close()
                logging.info("Connection closed.")
            except Exception as e:
                logging.error(f"Failed to close connection: {e}")


def do_online_allocation(input_data: dict):
    client = WebSocketClient(os.getenv("RESOURCE_ALLOCATOR_URL", "ws://localhost:8765"))

    def run(input_data: dict):
        async def wrapper():
            await client.connect()

            try:
                await client.send_message(input_data)
                response = await client.receive_message()
                logging.info(f"Response from server: {response}")
                return response
            finally:
                await client.close()

        return asyncio.run(wrapper())

    return run(input_data)
