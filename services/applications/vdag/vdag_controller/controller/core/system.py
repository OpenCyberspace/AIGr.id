from flask import Flask, jsonify
import threading
import os

from .env import Env
from .clients import vDAGDBClient
from .schema import vDAGObject


from .adhoc_service_pb2 import BlockInferencePacket, FileInfo as BlockFileInfo
from .vdag_service_pb2 import vDAGInferencePacket, vDAGFileInfo


class vDAGInitData:

    def __init__(self, env: Env) -> None:
        self.env = env
        self.vdag_uri = env.vdag_uri
        self.loader = vDAGDBClient(self.env.vdag_db_server_uri)
        response = self.loader.get_vdag(self.env.vdag_uri)

        if response.vdagURI == "":
            raise Exception(f"failed to get initial vDAG data: {response}")

        self.vdag_data: vDAGObject = response

    def get_vdag_data(self):
        return self.vdag_data


class vDAG:

    def __init__(self, env: Env) -> None:
        vdag_client = vDAGInitData(env)

        self.vdag_data = vdag_client.vdag_data

        self.vdag_client = vdag_client
        self.graph = vdag_client.vdag_data.compiled_graph_data
        self.controller = vdag_client.vdag_data.controller
        self.l3_graph = self.graph['t3_graph']
        self.l2_graph = self.graph['t2_graph']
        self.head_block_id = self.graph['head']
        self.vdag_uri = vdag_client.vdag_uri

    def get_connection_cycle_interval(self):
        return int(self.controller.get('connectionRefreshInterval', -1))

    def get_verification_audit_policy(self):
        return self.controller.get('verificationAuditPolicy', {})

    def get_verification_audit_interval(self):
        return self.controller.get('verificationAuditInterval', -1)

    def get_l3_graph(self):
        return self.l3_graph

    def get_l2_graph(self):
        return self.l2_graph

    def get_graph_format(self):
        return {
            "is_graph": True,
            "graph": self.get_l2_graph()
        }
        

    def head_block(self):
        return self.head_block_id

    def get_vdag(self):
        return self.vdag_client.vdag_data.to_dict()


class vDAGAPIServer:
    def __init__(self, vdag_instance):
        self.vdag = vdag_instance
        self.app = Flask(__name__)
        self.setup_routes()

    def setup_routes(self):
        @self.app.route("/connection_cycle_interval", methods=["GET"])
        def get_connection_cycle_interval():
            try:
                data = self.vdag.get_connection_cycle_interval()
                return jsonify({"success": True, "data": data}), 200
            except Exception as e:
                return jsonify({"success": False, "message": str(e)}), 500

        @self.app.route("/verification_audit_policy", methods=["GET"])
        def get_verification_audit_policy():
            try:
                data = self.vdag.get_verification_audit_policy()
                return jsonify({"success": True, "data": data}), 200
            except Exception as e:
                return jsonify({"success": False, "message": str(e)}), 500

        @self.app.route("/verification_audit_interval", methods=["GET"])
        def get_verification_audit_interval():
            try:
                data = self.vdag.get_verification_audit_interval()
                return jsonify({"success": True, "data": data}), 200
            except Exception as e:
                return jsonify({"success": False, "message": str(e)}), 500

        @self.app.route("/l3_graph", methods=["GET"])
        def get_l3_graph():
            try:
                data = self.vdag.get_l3_graph()
                return jsonify({"success": True, "data": data}), 200
            except Exception as e:
                return jsonify({"success": False, "message": str(e)}), 500

        @self.app.route("/head_block", methods=["GET"])
        def head_block():
            try:
                data = self.vdag.head_block()
                return jsonify({"success": True, "data": data}), 200
            except Exception as e:
                return jsonify({"success": False, "message": str(e)}), 500

        @self.app.route("/vdag", methods=["GET"])
        def get_vdag():
            try:
                data = self.vdag.get_vdag()
                return jsonify({"success": True, "data": data}), 200
            except Exception as e:
                return jsonify({"success": False, "message": str(e)}), 500

    def run(self, host="0.0.0.0", port=5000):
        self.app.run(host=host, port=port)

    def run_in_thread(self, host="0.0.0.0", port=5000):
        thread = threading.Thread(
            target=self.run, args=(host, port), daemon=True)
        thread.start()
        return thread


def vdag_to_block(vdag_packet: vDAGInferencePacket, block_id: str, graph_str: str, vdag_uri) -> BlockInferencePacket:

    session_id = "vdag::" + vdag_uri + "::" + vdag_packet.session_id

    return BlockInferencePacket(
        block_id=block_id,
        session_id=session_id,
        seq_no=vdag_packet.seq_no,
        frame_ptr=vdag_packet.frame_ptr,
        data=vdag_packet.data,
        query_parameters="",
        ts=vdag_packet.ts,
        files=[BlockFileInfo(metadata=f.metadata, file_data=f.file_data)
               for f in vdag_packet.files],
        output_ptr=graph_str
    )


def block_to_vdag(block_packet: BlockInferencePacket) -> vDAGInferencePacket:

    session_id = block_packet.session_id.split("::")
    if len(session_id) > 2:
        session_id = session_id[2]
    else:
        raise Exception("invalid session ID")

    return vDAGInferencePacket(
        session_id=session_id,
        seq_no=block_packet.seq_no,
        data=block_packet.data,
        ts=block_packet.ts,
        files=[vDAGFileInfo(metadata=f.metadata, file_data=f.file_data)
               for f in block_packet.files]
    )
