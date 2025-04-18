from . import IR
from .paths import create_cluster_path, similarity_search_path, filter_path
from .paths import similarity_search_executor_path
from .paths import block_action_path
from .paths import create_llm_vdag
from .paths import create_vdag
from .paths import add_node_to_cluster_path
from .paths import execute_mgmt_command_path


def create_cluster(input: dict):
    try:

        # 1. create IR
        cluster_ir = IR.cluster_create_IR(input)

        # 2. choose path
        ret, cluster_id = create_cluster_path(cluster_ir)

        if not ret:
            raise Exception(str(cluster_id))

        return cluster_id

    except Exception as e:
        raise e


def add_node(input: dict):
    try:
        # create IR
        node_ir = IR.node_add_IR(input)

        # 2. choose path:
        data = add_node_to_cluster_path(node_ir)
        return data
    except Exception as e:
        raise e


def filter_data(input: dict):
    try:

        filter_ir = IR.filter_IR(input)
        return filter_path(filter_ir)

    except Exception as e:
        raise e


def similarity_search(input: dict):
    try:

        search_ir = IR.search_IR(input)
        print(search_ir['rankingPolicyRule'])
        if search_ir['rankingPolicyRule'].get('executionMode', 'local') == "code":
            return similarity_search_executor_path(search_ir)
        else:
            return similarity_search_path(search_ir)

    except Exception as e:
        raise e


def execute_block_action(input: dict):
    try:

        block_ir = IR.block_create_IR(input)

        return block_action_path(block_ir)

    except Exception as e:
        raise e


def execute_create_llm_vdag(input: dict):
    try:
        llm_vdag_ir = IR.create_llm_vdag_IR(input)

        return create_llm_vdag(llm_vdag_ir)

    except Exception as e:
        raise e


def execute_vdag_validate(input: dict):
    try:

        vdag_ir = IR.create_vdag_IR(input)
        vdag_ir['mode'] = 'validateGraph'
        return create_vdag(vdag_ir)

    except Exception as e:
        raise e


def execute_vdag_create(input: dict):
    try:

        vdag_ir = IR.create_vdag_IR(input)
        return create_vdag(vdag_ir)

    except Exception as e:
        raise e


def execute_mgmt_command(input: dict):
    try:

        ir = IR.mgmt_function_IR(input)
        return execute_mgmt_command_path(ir)

    except Exception as e:
        raise e
