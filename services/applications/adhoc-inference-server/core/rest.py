import threading
import queue
import uuid
import psycopg2
import psycopg2.extras

from .search import SearchClient
from .discovery import DiscoveryCache, GraphCache, Estimator

import os

from flask import Flask, jsonify, request

graphs_cache = GraphCache()
estimator = Estimator()

app = Flask(__name__)


class DBLogsWriter(threading.Thread):
    def __init__(self):
        super().__init__()
        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.db_host = os.getenv("DB_HOST")
        self.db_name = os.getenv("DB_NAME")
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_port = int(os.getenv("DB_PORT", 5432))
        self._initialize_db()

    def _initialize_db(self):
        try:
            self.connection = psycopg2.connect(
                host=self.db_host,
                dbname=self.db_name,
                user=self.db_user,
                password=self.db_password,
                port=self.db_port
            )
            self.cursor = self.connection.cursor()
            self.create_table()
        except psycopg2.Error as e:
            print(f"Error initializing database: {e}")

    def create_table(self):
        try:
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS block_inference (
                request_id UUID PRIMARY KEY,
                session_id TEXT,
                block_id TEXT,
                seq_no INTEGER,
                ts TIMESTAMPTZ,
                frame_ptr BYTEA,
                data BYTEA,
                query_parameters BYTEA,
                output_ptr BYTEA,
            );

            SELECT create_hypertable('block_inference', 'ts', if_not_exists => TRUE);
            ''')
            self.connection.commit()
        except psycopg2.Error as e:
            print(f"Error creating table: {e}")

    def run(self):
        while not self.stop_event.is_set() or not self.log_queue.empty():
            try:
                packet = self.log_queue.get(timeout=1)
                self._log_to_db(packet)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing log queue: {e}")

    def _log_to_db(self, packet):
        try:
            request_id = uuid.uuid4()
            session_id = packet.session_id
            block_id = packet.block_id if packet.HasField('block_id') else None
            instance_id = packet.instance_id if packet.HasField(
                'instance_id') else None
            seq_no = packet.seq_no
            query_parameters = packet.query_parameters
            ts = packet.ts
            is_frame = packet.is_frame
            frame_ptr = packet.frame_ptr if is_frame else None

            self.cursor.execute('''
            INSERT INTO logs (
                request_id, session_id, block_id, instance_id, seq_no,
                query_parameters, ts, is_frame, frame_ptr
            ) VALUES (%s, %s, %s, %s, %s, %s, to_timestamp(%s), %s, %s)
            ''', (
                request_id, session_id, block_id, instance_id, seq_no,
                query_parameters, ts, is_frame, frame_ptr
            ))

            self.connection.commit()
            self.log_queue.task_done()
        except psycopg2.Error as e:
            print(f"Error logging to database: {e}")

    def log(self, packet):
        try:
            self.log_queue.put(packet)
        except Exception as e:
            print(f"Error putting packet in log queue: {e}")

    def close(self):
        self.stop_event.set()
        self.join()
        try:
            self.connection.close()
        except psycopg2.Error as e:
            print(f"Error closing database connection: {e}")

    def query(self, query, params):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except psycopg2.Error as e:
            print(f"Error executing query: {e}")
            return []


@app.route('/logs/session/<session_id>', methods=['GET'])
def get_records_by_session_id(session_id):
    try:
        query = "SELECT * FROM logs WHERE session_id = %s"
        records = DBLogsWriter().query(query, (session_id,))
        return jsonify(records), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/logs/request/<request_id>', methods=['GET'])
def get_records_by_request_id(request_id):
    try:
        query = "SELECT * FROM logs WHERE request_id = %s"
        records = DBLogsWriter().query(query, (request_id,))
        return jsonify(records), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/logs/block/<block_id>', methods=['GET'])
def get_records_by_block_id(block_id):
    try:
        query = "SELECT * FROM logs WHERE block_id = %s"
        records = DBLogsWriter().query(query, (block_id,))
        return jsonify(records), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/logs/session_block', methods=['GET'])
def get_records_by_session_id_and_block_id():
    try:
        session_id = request.args.get('session_id')
        block_id = request.args.get('block_id')
        query = "SELECT * FROM logs WHERE session_id = %s AND block_id = %s"
        records = DBLogsWriter().query(query, (session_id, block_id))
        return jsonify(records), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/discovery/search', methods=['POST'])
def discover_search():
    try:

        search = SearchClient()
        result = search.similarity_search(request.json)

        return jsonify({
            "success": True,
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route('/discovery/filter', methods=['POST'])
def discover_filter():
    try:

        search = SearchClient()
        result = search.filter_data(request.json)

        return jsonify({
            "success": True,
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route('/discovery/get_url/<block_id>', methods=['POST'])
def discover_public_url(block_id):
    try:

        discovery = DiscoveryCache()
        public_url, port = discovery.discover(block_id, instance_id="")

        return jsonify({
            "success": True,
            "queue_url": public_url,
            "port": port
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/discovery/resolve_graph", methods=['POST'])
def resolve_graph():
    try:

        graph_connections = {}
        graph_input = request.json

        for block_id, children in graph_input.items():
            connections = graphs_cache.resolve_outputs(block_id, children)
            graph_connections[block_id] = connections

        return jsonify({"success": True, "graph": graph_connections})

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/discovery/estimate", methods=['POST'])
def estimate():
    try:
        payload = request.json
        search_query = payload.get("search_query")
        block_id = payload.get("block_id")
        result = estimator.estimate(search_query, block_id)

        return jsonify({"success": True, "data": result}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/discovery/check_execute", methods=['POST'])
def check_execute():
    try:
        payload = request.json
        search_query = payload.get("search_query")
        query_params = payload.get("query_params", {})
        block_id = payload.get("block_id")
        result = estimator.check_execute(search_query, query_params, block_id)

        return jsonify({"success": True, "data": result}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def run_app():
    def run():
        app.run(host='0.0.0.0', port=20000)

    app_thread = threading.Thread(target=run)
    app_thread.start()
