from . import proxy_pb2_grpc
from . import proxy_pb2
import os
import copy
import redis
import threading
import json
import grpc

from .muti_workers import ThreadJobExecutor, ProcessJobExecutor
from .block import BlocksDB
from .utils import SessionsManager
from .ws import WebsocketStreamingManager
from .policy_sandbox import LocalPolicyEvaluator
from .metrics import AIOSMetrics
from .aios_packet_pb2 import AIOSPacket
from .tools import Muxer
from .vdag_process import vDAGProcessor
from .side_cars import BlockSideCars
from .events import BlockEvents

from .default_policies import DefaultPostprocessingPolicy, DefaultPreprocessingPolicy


from flask import Flask, request, jsonify

import logging
import time

logging.basicConfig(level=logging.DEBUG)
logging = logging.getLogger(__name__)


class InferenceProxyClient:
    def __init__(self, block_id, url):
        self.channel = grpc.insecure_channel(url)
        self.header = [('x-service-name', block_id)]
        self.stub = proxy_pb2_grpc.InferenceProxyStub(self.channel)

    def infer(self, rpc_data):
        request = proxy_pb2.InferenceMessage(rpc_data=rpc_data)
        response = self.stub.infer(request, metadata=self.header)
        return response.message

    def lpush(self, queue_name, rpc_data):
        self.infer(rpc_data)


class Context:

    def __init__(self, metrics_obj, block_data, block_init_data, block_init_settings, block_init_parameters, sessions, events, side_cars) -> None:
        self.metrics = metrics_obj
        self.block_data = block_data
        self.block_init_data = block_init_data
        self.block_init_settings = block_init_settings
        self.block_init_parameters = block_init_parameters
        self.sessions = sessions
        self.events = events
        self.side_cars = side_cars
        self.block_path = f'/{os.getenv("BLOCK_ID")}'
        self.instance_path = f'/{os.getenv("INSTANCE_ID")}'
        self.common_path = '/common'
        self.write_ws = None



class RedisConnectionCache:
    def __init__(self, max_retries=5, retry_delay=5):
        self.cache = {}
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def get(self, block_id: str, host: str, port: int):
        cache_key = f"{host}:{port}"

        if cache_key in self.cache:
            conn = self.cache[cache_key]
            try:
                if port != 0:
                    conn.ping()
                return conn
            except Exception as e:
                logging.warning(f"[RedisConnectionCache] Cached connection to {cache_key} is stale: {str(e)}. Reconnecting...")
                self.remove(host, port)

        for attempt in range(1, self.max_retries + 1):
            try:
                if port == 0:
                    self.cache[cache_key] = InferenceProxyClient(block_id, host)
                    logging.info(f"[RedisConnectionCache] Created new gRPC connection: {cache_key}")
                else:
                    conn = redis.Redis(host=host, port=port)
                    conn.ping()
                    self.cache[cache_key] = conn
                    logging.info(f"[RedisConnectionCache] Created new Redis connection: {cache_key}")
                return self.cache[cache_key]
            except Exception as e:
                logging.error(f"[RedisConnectionCache] Attempt {attempt}/{self.max_retries} - Failed to connect to {cache_key}: {str(e)}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    logging.error(f"[RedisConnectionCache] Giving up after {self.max_retries} attempts to connect to {cache_key}")
                    break

        return None

    def remove(self, host: str, port: int):
        cache_key = f"{host}:{port}"
        try:
            if cache_key in self.cache:
                del self.cache[cache_key]
                logging.info(f"[RedisConnectionCache] Removed connection for {cache_key}")
        except Exception as e:
            logging.error(f"[RedisConnectionCache] Error removing connection {cache_key}: {str(e)}")
            self.cache.clear()
            raise e


def load_block_data():
    try:
        base_url = os.getenv("BLOCKS_DB_URI", "http://localhost:3001")
        if not base_url:
            raise ValueError("BLOCKS_DB_URI environment variable is not set.")

        db = BlocksDB(base_url)

        block_id = os.getenv("BLOCK_ID")
        if not block_id:
            raise ValueError("BLOCK_ID environment variable is not set.")

        success, result = db.get_block_by_id(block_id)
        if success:
            return True, result
        else:
            return False, result

    except Exception as e:
        return False, str(e)


class PreProcessResult:

    def __init__(self, packet, extra_data, session_id) -> None:
        self.session_id = session_id
        self.packet = packet
        self.extra_data = extra_data


class OnDataResult:

    def __init__(self, output) -> None:
        self.output = output


class Block:

    def __init__(self, block_class) -> None:
        try:

            block_id = os.getenv("BLOCK_ID")
            self.block_id = block_id
            instance_id = os.getenv("INSTANCE_ID")
            self.instance_id = instance_id
            self.input_queue_name = f"{block_id}_inputs"

            logging.info(
                f"booting block_id={block_id}, instance_id={instance_id}")

            ret, block_data_full = load_block_data()
            if not ret:
                raise Exception(block_data_full)

            self.block_data_full = block_data_full

            self.block_init_data = self.block_data_full.get(
                "blockInitData", {})
            self.block_init_settings = self.block_data_full.get(
                "initSettings", {})
            self.block_init_parameters = self.block_data_full.get(
                "parameters", {})
            self.block_side_cars = self.block_init_data.get("side_cars")

            logging.info(f"block_init_data: {self.block_init_data}")
            logging.info(f"block_init_settings: {self.block_init_settings}")
            logging.info(
                f"block_init_parameters: {self.block_init_parameters}")

            self.block_events = BlockEvents()

            self.side_cars = BlockSideCars(self.block_id, self.block_side_cars)

            self.frame_ptr_cache = {}

            self.sessions = SessionsManager()

            self.processors = vDAGProcessor(self.block_id, block_data_full)

            self.metrics = AIOSMetrics()
            self.metrics.start_http_server()

            # extra init data:
            extra_init_data = os.getenv("CUSTOM_INIT_DATA", None)

            if extra_init_data:
                extra_init_data = json.loads(extra_init_data)
                logging.info("[block extra init data] {}".format(extra_init_data))
                self.block_init_data.update(extra_init_data.get('blockInitData', {}))
                self.block_init_settings.update(extra_init_data.get('initSettings', {}))

            self.context = Context(
                block_init_data=self.block_init_data,
                metrics_obj=self.metrics,
                block_data=self.block_data_full,
                block_init_settings=self.block_init_settings,
                block_init_parameters=self.block_init_parameters,
                sessions=self.sessions,
                events=self.block_events,
                side_cars=self.block_side_cars
            )

            self.ws_server = WebsocketStreamingManager(self.listen_for_jobs_now)
            self.context.write_ws = self.ws_server.write_data

            self.block_module = block_class(self.context)

            self.redis_client = None
            self.reconnect_redis_client()

            self.listen_parameter_updates_thread = threading.Thread(
                target=self.listen_parameter_updates, daemon=True)
            self.listen_parameter_updates_thread.start()

            self.block_output = redis.Redis(
                host=f'{self.block_id}-executor.blocks.svc.cluster.local', port=6379, db=0)

            # register basic metrics:
            self.metrics.register_gauge(
                "on_preprocess_latency", "latency of on_preprocess function")
            self.metrics.register_gauge(
                "on_data_latency", "latency of on_data function")
            self.metrics.register_gauge(
                "end_to_end_latency", "total end-to-end processing latency")

            self.metrics.register_counter(
                "on_preprocess_count", "number of times on_preprocess is called")
            self.metrics.register_counter(
                "on_data_count", "number of times on_data is called")
            self.metrics.register_counter(
                "end_to_end_count", "total jobs processed")

            self.metrics.register_gauge(
                "on_preprocess_fps", "frames per second for on_preprocess")
            self.metrics.register_gauge(
                "on_data_fps", "frames per second for on_data")
            self.metrics.register_gauge(
                "end_to_end_fps", "frames per second for end-to-end processing")
            self.counter = 0
            self.redis_cache = RedisConnectionCache()

            # start queue length thread:
            flask_thread = threading.Thread(
                target=self.update_queue_length, daemon=True)
            flask_thread.start()

            executor_type = self.block_init_data.get(
                "thread_pool_mode", "thread")
            enable_pool = self.block_init_data.get("enable_thread_pool", False)

            # initialize block pre/post policies:
            self.post_processor = None
            self.preprocessor = None

            self._load_pre_policy_rule()
            self._load_post_policy_rule()

            if enable_pool:
                # wherever you put these
                from .muti_workers import ThreadJobExecutor, ProcessJobExecutor

                max_threads = self.block_init_data.get("max_threads", 4)
                max_queue_size = self.block_init_data.get(
                    "max_queue_size", 100)
                sticky = self.block_init_data.get("sticky_sessions", False)

                ExecutorClass = ThreadJobExecutor if executor_type == "thread" else ProcessJobExecutor

                self.job_executor = ExecutorClass(
                    worker_fn=self.listen_for_jobs_now,
                    max_threads=max_threads,
                    max_queue_size=max_queue_size,
                    sticky_sessions=sticky
                )
            else:
                self.job_executor = None

        except Exception as e:
            raise e

    
    def _load_pre_policy_rule(self, name="pre_processing"):
        try:
            logging.info("Loading policy rule")
            policies = self.block_data_full.get('policies', {})
            if name in policies:
                settings = policies[name].get(
                    'settings', {})
                parameters = policies[name].get(
                    'parameters', {})
                policy_rule_uri = policies[name].get("policyRuleURI", "")

             
                self.preprocessor = LocalPolicyEvaluator(
                    policy_rule_uri,
                    parameters=parameters,
                    settings=settings
                )

                logging.info("[Pre processing policy] Loaded")

        except Exception as e:
            logging.error(f"[Pre processing policy] Error loading policy rule: {e}")
            self.preprocessor = None
    

    def _load_post_policy_rule(self, name="post_processing"):
        try:
            logging.info("Loading policy rule")
            policies = self.block_data_full.get('policies', {})
            if name in policies:
                settings = policies[name].get(
                    'settings', {})
                parameters = policies[name].get(
                    'parameters', {})
                policy_rule_uri = policies[name].get(
                    "policyRuleURI", {})

             
                self.post_processor = LocalPolicyEvaluator(
                    policy_rule_uri,
                    parameters=parameters,
                    settings=settings
                )

                logging.info("[Post processing policy] Loaded")

        except Exception as e:
            logging.error(f"[Post processing policy] Error loading policy rule: {e}")
            self.post_processor = None


    def reconnect_redis_client(self, delay_seconds=5):
        while True:
            try:
                logging.info("[Block] Attempting to reconnect to Redis...")
                self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
                self.redis_client.ping()
                logging.info("[Block] Redis reconnected successfully.")
                break
            except Exception as e:
                logging.warning(f"[Block] Redis reconnection failed: {str(e)}. Retrying in {delay_seconds} seconds...")
                time.sleep(delay_seconds)

    def update_queue_length(self):
        while True:
            queue_length = self.redis_client.llen(self.input_queue_name)
            self.metrics.set_gauge("queue_length", queue_length)
            self.metrics.observe_rolling("queue_length", queue_length)

            time.sleep(10)

    def check_is_vdag_packet(self, session_id: str):
        try:

            if session_id.startswith('vdag::'):
                splits = session_id.split("::")
                if len(splits) < 3:
                    raise Exception(f"malformed packet: {session_id}")

                vdag_uri = splits[1]

                return True, vdag_uri
            return False, ""

        except Exception as e:
            raise e

    def listen_parameter_updates(self):

        while True:
            try:
                _, data_json = self.redis_client.brpop("PARAMETER_UPDATES")

                updated_parameters = json.loads(data_json)

                self.block_init_parameters.update(updated_parameters)

                logging.info(f"got parameter updates data={data_json}")
                logging.info(
                    f"current_block_parameters: {self.block_init_parameters}")

            except Exception as e:
                logging.error(
                    f"Error while listening for parameter updates: {str(e)}")
    

    def listen_for_jobs(self):
        logging.info("[Block] Listening for jobs")
        logging.info(f"[ProcessJobExecutor] process job executor={self.job_executor}")

        while True:
            try:
                # Blocking wait on input queue
                _, job_data = self.redis_client.brpop(self.input_queue_name)

                if self.job_executor:
                    # Extract session_id only
                    proto = AIOSPacket()
                    proto.ParseFromString(job_data)
                    session_id = proto.session_id

                    job_tuple = (job_data, time.time())

                    success = self.job_executor.assign_job(job_tuple, session_id=session_id)
                    if not success:
                        logging.warning("[Block] Dropping job due to full thread/process queue")
                else:
                    self.listen_for_jobs_now((job_data, time.time()))

            except Exception as e:
                logging.error(f"[Block] Error in listen_for_jobs: {str(e)}")
                logging.warning("[Block] Attempting to re-establish Redis connection...")

                # Retry forever with sleep
                self.reconnect_redis_client()


    def listen_for_jobs_now(self, job_tuple, session_id=None, serialized=False, is_ws=False):
        try:

            job_data_proto = None
            job_start_time = 0

            if not serialized:
                job_data_bytes, job_start_time = job_tuple

                job_data_proto = AIOSPacket()
                job_data_proto.ParseFromString(job_data_bytes)
            else:
                job_data_proto, job_start_time = job_tuple


            # check pre-processing:
            is_vdag, uri = self.check_is_vdag_packet(
                job_data_proto.session_id)
            if is_vdag:
                job_data_proto = self.processors.execute_pre_process_policy_rule_if_present(uri, job_data_proto)

            muxer: Muxer = self.block_module.get_muxer()
            if muxer:
                op = muxer.process_packet(job_data)
                if not op:
                    return
                job_data = op

            preprocess_start = time.time()

            # run block specific pre-processing
            if self.preprocessor:
                response =  self.preprocessor.execute_policy_rule({
                    "packet": job_data_proto,
                    "block_data": self.block_data_full
                })

                job_data_proto = response['packet']

            ret, data = self.block_module.on_preprocess(job_data_proto)
            preprocess_end = time.time()

            if not ret:
                logging.error(f"Error in on_preprocess: {data}")
                return

            if not data:
                return

            if type(data) != list:
                data = [data]

            self.metrics.increment_counter("on_preprocess_count")
            preprocess_latency = preprocess_end - preprocess_start
            self.metrics.set_gauge(
                "on_preprocess_latency", preprocess_latency)
            self.metrics.set_gauge(
                "on_preprocess_fps", 1 / preprocess_latency if preprocess_latency > 0 else 0)

            for entry in data:
                on_data_start = time.time()
                ret, on_data_result = self.block_module.on_data(entry, is_ws=is_ws)
                on_data_end = time.time()

                if is_ws:
                    continue

                if not ret:
                    logging.error(f"Error in on_data: {on_data_result}")
                    continue

                output = on_data_result.output

                proto = entry.packet
                proto.data = json.dumps(output)

                if self.post_processor:
                    response =  self.post_processor.execute_policy_rule({
                        "packet": proto,
                        "block_data": self.block_data_full
                    })

                    proto = response['packet']

                is_vdag, uri = self.check_is_vdag_packet(proto.session_id)
                if is_vdag:
                    proto = self.processors.execute_post_process_policy_rule_if_present(
                        uri, proto)

                output_bytes = proto.SerializeToString()

                if proto.output_ptr and proto.output_ptr != "":
                    try:
                        output_config = json.loads(proto.output_ptr)
                        if 'is_graph' in output_config and output_config['is_graph']:
                            g = output_config['graph']
                            output_config = g.get(
                                self.block_id, {"outputs": []})

                            if len(output_config['outputs']) == 0:
                                output_config = g['final']

                        if "outputs" in output_config:
                            for output in output_config["outputs"]:
                                host = output.get("host", "localhost")
                                port = output.get("port", 6379)
                                block_id = output.get('block_id', '')
                                queue_name = output.get("queue_name", "OUTPUT")

                                redis_conn = self.redis_cache.get(
                                    block_id, host, port)

                                logging.info(
                                    f"pushing output to {redis_conn}: {queue_name} -> {host}:{port}")
                                if redis_conn:
                                    logging.info(
                                        f"pushing output now: {proto.session_id}:{proto.seq_no}")
                                    redis_conn.lpush(
                                        queue_name, output_bytes)

                    except json.JSONDecodeError as e:
                        logging.error(f"Invalid output_ptr JSON: {str(e)}")
                else:
                    self.block_output.lpush("OUTPUT", output_bytes)

                self.metrics.increment_counter("on_data_count")
                on_data_latency = on_data_end - on_data_start
                self.metrics.set_gauge("on_data_latency", on_data_latency)
                self.metrics.set_gauge(
                    "on_data_fps", 1 / on_data_latency if on_data_latency > 0 else 0)

            job_end_time = time.time()
            self.metrics.increment_counter("end_to_end_count")
            end_to_end_latency = job_end_time - job_start_time

            # Prometheus
            self.metrics.set_gauge("end_to_end_latency", end_to_end_latency)
            self.metrics.increment_counter("end_to_end_count")
            self.metrics.set_gauge("end_to_end_fps", 1 / end_to_end_latency if end_to_end_latency > 0 else 0)

            # Rolling
            self.metrics.observe_rolling("latency", end_to_end_latency)
            self.metrics.observe_rolling("fps", 1 / end_to_end_latency if end_to_end_latency > 0 else 0)
            self.metrics.observe_rolling("tasks_processed", 1)

        except Exception as e:
            logging.error(f"Error when executing job: {str(e)}")
            return

    def run(self):
        self.start_parameters_server()
        self.ws_server.start_as_thread()
        self.listen_for_jobs()

    def start_parameters_server(self):
        app = Flask(__name__)

        @app.route('/health')
        def health():
            try:
                response = self.block_module.health()
                return {"success": True, "data": response}, 200
            except Exception as e:
                return {"success": False, "message": str(e)}, 500

        @app.route('/setParameters', methods=['POST'])
        def set_parameters():
            try:
                updated_parameters = request.json
                self.block_init_parameters.update(updated_parameters)
                ret, ret_vals = self.block_module.on_update(updated_parameters)
                if not ret:
                    raise Exception(str(ret_vals))
                return jsonify({"success": True, "updated_parameters": ret_vals}), 200
            except Exception as e:
                logging.error(f"Error in /setParameters: {str(e)}")
                return jsonify({"success": False, "message": str(e)}), 500

        @app.route("/mgmt", methods=["POST"])
        def handle_mgmt():
            try:
                payload = request.json
                mgmt_action = payload.get("mgmt_action")
                mgmt_data = payload.get("mgmt_data", {})

                if not mgmt_action:
                    return jsonify({"success": False, "message": "mgmt_action is required"}), 400

                logging.info(
                    f"Received management command: {mgmt_action} with data: {mgmt_data}")
                result = self.block_module.management(
                    mgmt_action, mgmt_data
                )

                return jsonify({"success": True, "data": result}), 200

            except Exception as e:
                logging.error(f"Error handling management request: {e}")
                return jsonify({"success": False, "message": str(e)}), 500

        def run_flask():
            app.run(host='0.0.0.0', port=int(os.getenv("MGMT_PORT", 18001)))

        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
