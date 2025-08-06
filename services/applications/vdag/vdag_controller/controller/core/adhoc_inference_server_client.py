import logging
import grpc
import time
from collections import defaultdict

from . import adhoc_service_pb2_grpc

class AdhocInferenceConnectionsManager:
    def __init__(self, expiry_time=300):
        self.connections = {}  # session_id -> (channel, stub)
        self.expiry_time = expiry_time
        self.last_access_time = defaultdict(lambda: 0)
        logging.info("Initialized AdhocInferenceConnectionsManager with expiry time: %s", expiry_time)

    def get_connection(self, session_id, server_address='localhost:50051', expiry_time=None):
        current_time = time.time()
        expiry_time = self.expiry_time if expiry_time is None else expiry_time

        if session_id in self.connections:
            channel, stub = self.connections[session_id]

            # Check if expired
            if expiry_time != -1 and (current_time - self.last_access_time[session_id]) > expiry_time:
                logging.info(f"Session {session_id} expired. Re-establishing connection.")
                self._close_connection(session_id)
            else:
                self.last_access_time[session_id] = current_time
                return stub

        return self._establish_connection(session_id, server_address)

    def _establish_connection(self, session_id, server_address):
        try:
            logging.info(f"Establishing new connection for session: {session_id}")

            channel = grpc.insecure_channel(server_address)
            stub = adhoc_service_pb2_grpc.BlockInferenceServiceStub(channel)

            self.connections[session_id] = (channel, stub)
            self.last_access_time[session_id] = time.time()
            return stub

        except grpc.RpcError as e:
            logging.error(f"gRPC connection error for {session_id}: {e.code()} - {e.details()}", exc_info=True)
            self._close_connection(session_id)
        except Exception as e:
            logging.error(f"Unexpected connection error for {session_id}: {str(e)}", exc_info=True)
            self._close_connection(session_id)

        return None

    def reestablish_connection(self, session_id, server_address='localhost:50051'):
        logging.info(f"Manually re-establishing connection for session: {session_id}")
        self._close_connection(session_id)
        return self._establish_connection(session_id, server_address)

    def _close_connection(self, session_id):
        if session_id in self.connections:
            channel, _ = self.connections[session_id]
            try:
                channel.close()
            except Exception as e:
                logging.warning(f"Failed to close channel for session {session_id}: {e}")
            del self.connections[session_id]
            del self.last_access_time[session_id]
            logging.info(f"Closed connection for session: {session_id}")

    def close_all(self):
        for session_id, (channel, _) in self.connections.items():
            try:
                channel.close()
            except Exception as e:
                logging.warning(f"Failed to close channel for session {session_id}: {e}")
        self.connections.clear()
        self.last_access_time.clear()
        logging.info("Closed all connections.")


class AdhocInferenceClient:
    def __init__(self, server_address='localhost:50051'):
        self.server_address = server_address
        self.connections_manager = AdhocInferenceConnectionsManager()

    def infer(self, session_id, request, timeout=10, wait_for_ready=True):
        stub = self.connections_manager.get_connection(session_id, self.server_address)
        if not stub:
            logging.error(f"No valid connection available for session {session_id}")
            return None

        try:
            response = stub.infer(request, wait_for_ready=wait_for_ready)
            return response
        except grpc.RpcError as e:
            logging.error(f"gRPC error during inference: {e.code()} - {e.details()}", exc_info=True)
            self.connections_manager.reestablish_connection(session_id, self.server_address)
        except Exception as e:
            logging.error(f"Unexpected error during inference: {str(e)}", exc_info=True)
            self.connections_manager.reestablish_connection(session_id, self.server_address)

        return None
