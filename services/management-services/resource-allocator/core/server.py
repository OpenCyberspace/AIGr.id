import asyncio
import websockets
import logging
import json
from core.adhoc_policy_evaluator import start_server_in_thread

from .cluster_allocator import BlockCreator
from .adhoc_policy_evaluator import allocate_resources_ws

# Configure logging
logging.basicConfig(level=logging.INFO)


async def handle_client(websocket, path):

    client_address = websocket.remote_address
    logging.info(f"New connection from {client_address}")

    try:
        while True:
            message = await websocket.recv()
            logging.info(f"Received message from {client_address}: {message}")

            message = json.loads(message)

            if 'adhoc' in message and message['adhoc']:
                response = allocate_resources_ws(message)
                await websocket.send(json.dumps(response))
                continue


            block_creator = BlockCreator(
                input_data=message['input'], mode=message.get('mode', 'dry_run'))
            response = block_creator.execute()

            response = json.dumps(response)

            # Send response back to the client
            await websocket.send(response)
            logging.info(f"Sent response to {client_address}: {response}")

    except websockets.ConnectionClosed as e:
        logging.warning(f"Connection closed by {client_address}: {e}")

    except Exception as e:
        logging.error(f"An error occurred with client {client_address}: {e}")

    finally:
        logging.info(f"Connection with {client_address} closed.")


async def main():

    server = await websockets.serve(handle_client, "0.0.0.0", 8765)
    logging.info("WebSocket server started on ws://0.0.0.0:8765")

    try:
        await server.wait_closed()
    except Exception as e:
        logging.error(f"Server error: {e}")


def run_web_server():
    try:
        start_server_in_thread()
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Failed to start the server: {e}")
