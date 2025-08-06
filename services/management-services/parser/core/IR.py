import json
import logging
import string
import random

from .webhooks.blocks import BlocksClient
from .parser_v1 import V1Parser
from .utils import get_component_details

from .webhooks.component_registry import ComponentRegistry
from .webhooks.vdag_template_store import TemplateAPIClient

import re

def is_valid_k8s_name(name: str) -> bool:
    if not name:
        return False
    if len(name) > 253:
        return False
    # Kubernetes DNS label regex: ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$
    pattern = r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
    return re.match(pattern, name) is not None


def get_component_by_uri(component_uri):
    try:

        ret, component = ComponentRegistry.GetComponentByURI(component_uri)
        if not ret:
            raise Exception(str(component))

        return component

    except Exception as e:
        raise e


def check_is_external_template(json_doc):
    try:
        header = json_doc.get('header')
        if not header:
            return False

        template_id = header.get('templateUri')
        if not template_id:
            return False

        if template_id == "Parser/V1":
            return False

        return True

    except Exception as e:
        raise e


def execute_external_IR(json_doc: dict):
    try:

        header = json_doc.get('header')
        template_id = header['templateUri']
        parameters = header.get('parameters', {})

        # execute the external IR:
        templates_api = TemplateAPIClient()
        response = templates_api.execute_template_policy(template_id, json_doc, parameters)

        return response
        
    except Exception as e:
        raise e


def generate_unique_alphanumeric_string(N):
    alphanumeric_characters = string.ascii_letters + string.digits
    return ''.join(random.choices(alphanumeric_characters, k=N)).lower()


def generate_block_id():
    block_id = "blk-" + generate_unique_alphanumeric_string(8)
    return block_id


def block_create_IR(json_doc):
    try:
        if check_is_external_template(json_doc):
            return execute_external_IR(json_doc)

        block_data = json_doc['body']['spec']['values']

        logging.info("Parsing blockComponentURI field")
        component_uri = block_data.get('blockComponentURI')
        if not component_uri:
            raise ValueError("Missing required field: blockComponentURI")

        logging.info("Getting component details")
        component = get_component_details(component_uri)

        logging.info("Parsing or generating blockId")
        block_id = block_data.get('blockId') or generate_block_id()

        if not is_valid_k8s_name(block_id):
            raise Exception("block ID must be less than 255 characters and should not contain special symbols")


        # check if block ID exists
        bd = BlocksClient().get_block_by_id(block_id)
        if 'error' not in bd:
            raise Exception("block with same ID already exists")

        logging.info("Validating minInstances and maxInstances")
        min_instances = block_data.get('minInstances')
        max_instances = block_data.get('maxInstances')
        if min_instances is None or max_instances is None:
            raise ValueError("Both minInstances and maxInstances are required")

        logging.info("Parsing blockInitData (fallback to component)")
        block_init_data = block_data.get('blockInitData', component.get('componentInitData', {}))

        logging.info("Parsing initSettings (fallback to component)")
        init_settings = block_data.get('initSettings', component.get('componentInitSettings', {}))

        logging.info("Parsing parameters (fallback to component)")
        parameters = block_data.get('parameters', component.get('componentParameters', {}))

        logging.info("Merging policies")
        # Start with policies from component
        policies = component.get("policies", {}).copy()

        # Override or add policies from block spec
        for policy in block_data.get('policyRulesSpec', []):
            try:
                policy_name = policy['values']['name']
                policy_data = {
                    "policyRuleURI": policy['values'].get('policyRuleURI', ''),
                    "parameters": policy['values'].get('parameters', {}),
                    "settings": policy['values'].get('settings', {})
                }

                # Override existing or add new
                policies[policy_name] = policy_data
                logging.info(f"Overridden or added policy: {policy_name}")
            except KeyError as e:
                logging.error(f"Missing key in policy: {e}")
            except Exception as e:
                logging.error(f"Error parsing policy: {e}")

        block_doc = {
            "id": block_id,
            "api_mode": block_data.get("mode", "dry_run"),
            "componentUri": component_uri,
            "component": component,
            "blockUri": component_uri,
            "blockMetadata": component.get("componentMetadata", {}),
            "policies": policies,
            "blockInitData": block_init_data,
            "initSettings": init_settings,
            "parameters": parameters,
            "minInstances": min_instances,
            "maxInstances": max_instances,
            "inputProtocol": component.get("componentInputProtocol", {}),
            "outputProtocol": component.get("componentOutputProtocol", {}),
            "tags": component.get("tags", []),
        }

        return block_doc

    except KeyError as e:
        logging.error(f"Missing key in JSON document: {e}")
        raise e
    except ValueError as e:
        logging.error(f"Validation error: {e}")
        raise e
    except Exception as e:
        logging.error(f"Error parsing JSON document: {e}")
        raise e



def mgmt_function_IR(json_doc):
    try:

        if check_is_external_template(json_doc):
            return execute_external_IR(json_doc)

        mgmt_data = json_doc['body']['spec']['values']

        logging.info("Parsing blockId field")
        block_id = mgmt_data.get('blockId', "")

        logging.info("Parsing service field")
        service = mgmt_data.get('service')

        cluster_id = mgmt_data.get('clusterId', "")
        instance_id = mgmt_data.get('instanceId', "")

        logging.info("Parsing mgmtCommand field")
        mgmt_command = mgmt_data.get('mgmtCommand')

        logging.info("Parsing mgmtData field")
        mgmt_payload = mgmt_data.get('mgmtData', {})

        if not block_id:
            raise ValueError("Missing blockId in the payload")

        if not service:
            raise ValueError("Missing service in the payload")

        if not mgmt_command:
            raise ValueError("Missing mgmtCommand in the payload")

        # handle pre-checks:
        if cluster_id != "" and service != "stability_checker":
            raise ValueError("only service 'stability_checker' is supported when cluster ID is specified")

        if instance_id != "" and block_id == "":
            raise ValueError("block ID has to be specified when instance ID is specified")

        mgmt_dict = {
            "clusterId": cluster_id,
            "blockId": block_id,
            "service": service,
            "mgmtCommand": mgmt_command,
            "mgmtData": mgmt_payload,
            "instanceId": instance_id
        }

        logging.info("Parsed management function request successfully")
        return mgmt_dict
    except KeyError as e:
        logging.error(f"Missing key in JSON document: {e}")
        raise e
    except ValueError as e:
        logging.error(f"Validation error: {e}")
        raise e
    except Exception as e:
        logging.error(f"Error parsing JSON document: {e}")
        raise e


def filter_IR(json_doc):
    try:

        if check_is_external_template(json_doc):
            return execute_external_IR(json_doc)

        search_data = json_doc['body']['values']

        logging.info("Parsing matchType field")
        match_type = search_data.get('matchType')

        filter_data = search_data.get('filter')

        logging.info("Parsing filter field in parameters")

        similarity_search_dict = {
            "matchType": match_type,
            "filter": filter_data
        }

        return similarity_search_dict
    except KeyError as e:
        logging.error(f"Missing key in JSON document: {e}")
        raise e
    except Exception as e:
        logging.error(f"Error parsing JSON document: {e}")
        raise e


def search_IR(json_doc):
    try:

        if check_is_external_template(json_doc):
            return execute_external_IR(json_doc)


        search_data = json_doc['body']['values']

        logging.info("Parsing matchType field")
        match_type = search_data.get('matchType')

        logging.info("Parsing rankingPolicyRule field")
        ranking_policy_rule = search_data.get(
            'rankingPolicyRule', {}).get('values', {})

        logging.info("Parsing executionMode field")
        execution_mode = ranking_policy_rule.get('executionMode')

        logging.info("Parsing policyRuleURI field")
        policy_rule_uri = ranking_policy_rule.get('policyRuleURI')

        logging.info("Parsing settings field")
        settings = ranking_policy_rule.get('settings', {})

        logging.info("Parsing parameters field")
        parameters = ranking_policy_rule.get('parameters', {})

        logging.info("Parsing filter field in parameters")

        similarity_search_dict = {
            "matchType": match_type,
            "rankingPolicyRule": {
                # "executionMode": execution_mode,
                "policyRuleURI": policy_rule_uri,
                # "policyCodePath": ranking_policy_rule.get('policyCodePath'),
                "settings": settings,
                "parameters": parameters
            }
        }

        return similarity_search_dict
    except KeyError as e:
        logging.error(f"Missing key in JSON document: {e}")
        raise e
    except Exception as e:
        logging.error(f"Error parsing JSON document: {e}")
        raise e


def create_vdag_IR(json_doc):
    try:

        if check_is_external_template(json_doc):
            return execute_external_IR(json_doc)

        vdag_data = json_doc['body']['spec']['values']

        vdag_name = vdag_data.get('vdagName')
        vdag_version = vdag_data.get('vdagVersion', {
            'version': '0.0.1', 'release-tag': 'beta'
        })

        logging.info("Parsing discoveryTags field")
        discovery_tags = vdag_data.get('discoveryTags', [])

        logging.info("Parsing controller field")
        controller = vdag_data.get('controller', {})

        logging.info("Parsing inputSources field")
        input_sources = controller.get('inputSources', [])

        logging.info("Parsing initParameters field")
        init_parameters = controller.get('initParameters', {})

        logging.info("Parsing initSettings field")
        init_settings = controller.get('initSettings', {})

        logging.info("Parsing policies field")
        policies = controller.get('policies', [])

        logging.info("Parsing nodes field")
        nodes_data = vdag_data.get('nodes', [])
        nodes = []

        for node in nodes_data:
            logging.info(
                f"Parsing node with label: {node['spec']['values'].get('nodeLabel', 'unknown')}")

            spec = node.get('spec', {}).get('values', {})
            io_map = node.get('IOMap', [])

            node_dict = {
                "nodeLabel": spec.get('nodeLabel', ''),
                "nodeType": spec.get('nodeType', ''),
                "assignmentPolicyRule": spec.get('assignmentPolicyRule', {}),
                "preprocessingPolicyRule": spec.get('preprocessingPolicyRule', {}),
                "postprocessingPolicyRule": spec.get('postprocessingPolicyRule', {}),
                "modelParameters": spec.get('modelParameters', {}),
                "outputProtocol": spec.get('outputProtocol', {}),
                "inputProtocol": spec.get('inputProtocol', {}),
                "IOMap": io_map,
                "manualBlockId": spec.get('manualBlockId', "")
            }

            nodes.append(node_dict)

        logging.info("Parsing graph field")
        graph = vdag_data.get('graph', {})

        mode = vdag_data.get('mode', 'create')

        vdag_dict = {
            "vdag_name": vdag_name,
            "vdag_version": vdag_version,
            "mode": mode,
            "discoveryTags": discovery_tags,
            "controller": {
                "inputSources": input_sources,
                "initParameters": init_parameters,
                "initSettings": init_settings,
                "policies": policies
            },
            "nodes": nodes,
            "graph": graph
        }

        return vdag_dict
    except KeyError as e:
        logging.error(f"Missing key in JSON document: {e}")
        raise e
    except Exception as e:
        logging.error(f"Error parsing JSON document: {e}")
        raise e


def cluster_create_IR(json_doc):
    try:

        if check_is_external_template(json_doc):
            return execute_external_IR(json_doc)

        cluster_data = json_doc['body']['spec']['values']

        logging.info("Parsing id field")
        cluster_id = cluster_data.get('id')

        logging.info("Parsing regionId field")
        region_id = cluster_data.get('regionId')

        logging.info("Parsing nodes field")
        nodes = {
            "count": cluster_data['nodes'].get('count'),
            "nodeData": cluster_data['nodes'].get('nodeData', [])
        }

        logging.info("Parsing gpus field")
        gpus = {
            "count": cluster_data['gpus'].get('count'),
            "memory": cluster_data['gpus'].get('memory')
        }

        logging.info("Parsing vcpus field")
        vcpus = {
            "count": cluster_data['vcpus'].get('count')
        }

        logging.info("Parsing memory field")
        memory = cluster_data.get('memory')

        logging.info("Parsing swap field")
        swap = cluster_data.get('swap')

        logging.info("Parsing storage field")
        storage = {
            "disks": cluster_data['storage'].get('disks'),
            "size": cluster_data['storage'].get('size')
        }

        logging.info("Parsing network field")
        network = {
            "interfaces": cluster_data['network'].get('interfaces'),
            "txBandwidth": cluster_data['network'].get('txBandwidth'),
            "rxBandwidth": cluster_data['network'].get('rxBandwidth')
        }

        logging.info("Parsing config field")
        config = cluster_data.get('config', {})

        logging.info("Parsing tags field")
        tags = cluster_data.get('tags', [])

        logging.info("Parsing clusterMetadata field")
        cluster_metadata = cluster_data.get('clusterMetadata', {})

        logging.info("Parsing reputation field")
        reputation = cluster_data.get('reputation')

        cluster_dict = {
            "id": cluster_id,
            "regionId": region_id,
            "nodes": nodes,
            "gpus": gpus,
            "vcpus": vcpus,
            "memory": memory,
            "swap": swap,
            "storage": storage,
            "network": network,
            "config": config,
            "tags": tags,
            "clusterMetadata": cluster_metadata,
            "reputation": reputation
        }

        return cluster_dict
    except KeyError as e:
        logging.error(f"Missing key in JSON document: {e}")
        raise e
    except Exception as e:
        logging.error(f"Error parsing JSON document: {e}")
        raise e


def node_add_IR(json_doc):
    try:

        if check_is_external_template(json_doc):
            return execute_external_IR(json_doc)

        node_data = json_doc['body']['spec']['values']

        logging.info("Parsing clusterId field")
        cluster_id = node_data.get('clusterId')

        node_data = node_data.get('nodeData')

        logging.info("Parsing id field")
        node_id = node_data.get('id')

        logging.info("Parsing gpus field")
        gpus = {
            "count": node_data['gpus'].get('count'),
            "memory": node_data['gpus'].get('memory'),
            "gpus": node_data['gpus'].get('gpus', []),
            "modelNames": node_data['gpus'].get('modelNames', []),
            "features": node_data['gpus'].get('features', [])
        }

        logging.info("Parsing vcpus field")
        vcpus = {
            "count": node_data['vcpus'].get('count')
        }

        logging.info("Parsing memory field")
        memory = node_data.get('memory')

        logging.info("Parsing swap field")
        swap = node_data.get('swap')

        logging.info("Parsing storage field")
        storage = {
            "disks": node_data['storage'].get('disks'),
            "size": node_data['storage'].get('size')
        }

        logging.info("Parsing network field")
        network = {
            "interfaces": node_data['network'].get('interfaces'),
            "txBandwidth": node_data['network'].get('txBandwidth'),
            "rxBandwidth": node_data['network'].get('rxBandwidth')
        }

        logging.info("Parsing tags field")
        tags = node_data.get('tags', [])

        logging.info("Parsing nodeMetadata field")
        node_metadata = node_data.get('nodeMetadata', {})


        node_dict = {
            "clusterId": cluster_id,
            "nodeData": {
                "id": node_id,
                "gpus": gpus,
                "vcpus": vcpus,
                "memory": memory,
                "swap": swap,
                "storage": storage,
                "network": network,
                "tags": tags,
                "nodeMetadata": node_metadata,
            }
        }

        return node_dict
    except KeyError as e:
        logging.error(f"Missing key in JSON document: {e}")
        raise e
    except Exception as e:
        logging.error(f"Error parsing JSON document: {e}")
        raise e


def add_component_IR(json_doc):
    try:

        if check_is_external_template(json_doc):
            return execute_external_IR(json_doc)

        body = json_doc['body']['spec']['values']

        logging.info("Parsing componentId")
        component_id = body['componentId']  # Required

        logging.info("Parsing componentURI")
        component_uri = body['componentURI']  # Required

        componentType = body["componentType"]

        logging.info("Parsing containerRegistryInfo")
        container_registry_info = body.get('containerRegistryInfo')  # Optional

        logging.info("Parsing componentMetadata")
        component_metadata = body.get('componentMetadata', {})

        logging.info("Parsing componentInitData")
        component_init_data = body.get('componentInitData', {})

        logging.info("Parsing componentInputProtocol")
        component_input_protocol = body.get('componentInputProtocol', {})

        logging.info("Parsing componentOutputProtocol")
        component_output_protocol = body.get('componentOutputProtocol', {})

        logging.info("Parsing policies")
        policies = body.get('policies', {})

        logging.info("Parsing componentManagementCommandsTemplate")
        management_commands_template = body.get('componentManagementCommandsTemplate', {})

        logging.info("Parsing componentInitSettings")
        component_init_settings = body.get('componentInitSettings', {})

        logging.info("Parsing componentParameters")
        component_parameters = body.get('componentParameters', {})

        logging.info("Parsing componentInitSettingsProtocol")
        component_init_settings_protocol = body.get('componentInitSettingsProtocol', {})

        logging.info("Parsing componentInitParametersProtocol")
        component_init_parameters_protocol = body.get('componentInitParametersProtocol', {})

        logging.info("Parsing tags")
        tags = body.get('tags', [])

        # Construct document for insertion
        component_doc = {
            "componentId": component_id,
            "componentURI": component_uri,
            "componentType": componentType,
            "containerRegistryInfo": container_registry_info,
            "componentMetadata": component_metadata,
            "componentInitData": component_init_data,
            "componentInputProtocol": component_input_protocol,
            "componentOutputProtocol": component_output_protocol,
            "policies": policies,
            "componentManagementCommandsTemplate": management_commands_template,
            "componentInitSettings": component_init_settings,
            "componentParameters": component_parameters,
            "componentInitSettingsProtocol": component_init_settings_protocol,
            "componentInitParametersProtocol": component_init_parameters_protocol,
            "tags": tags
        }

        # Remove any None fields (e.g., optional but missing)
        component_doc = {k: v for k, v in component_doc.items() if v is not None}

        return component_doc

    except KeyError as e:
        logging.error(f"Missing key in JSON document: {e}")
        raise e
    except Exception as e:
        logging.error(f"Error parsing component JSON document: {e}")
        raise e


def create_llm_vdag_IR(json_doc):
    try:

        if check_is_external_template(json_doc):
            return execute_external_IR(json_doc)

        logging.info("Extracting task metadata")
        task_metadata = json_doc.get('taskMetadata', {})

        logging.info("Extracting input payload")
        input_payload = json_doc.get('inputPayload', {})

        logging.info("Extracting essential parameters from input payload")
        component_uri = input_payload.get('component_uri')
        model_plan_data = input_payload.get('model_plan_data')
        service_init_data = input_payload.get('service_init_data', {})
        volumes_config = input_payload.get('volumes_config', {})
        node_selector = input_payload.get('node_selector', None)

        logging.info("Constructing IR dictionary")
        ir_dict = {
            "taskId": task_metadata.get("task_id"),
            "status": task_metadata.get("status", "pending"),
            "startTime": task_metadata.get("start_time"),
            "endTime": task_metadata.get("end_time"),
            "k8sJobId": task_metadata.get("k8s_job_id", ""),
            "inputPayload": {
                "componentUri": component_uri,
                "modelPlanData": model_plan_data,
                "serviceInitData": service_init_data,
                "volumesConfig": volumes_config,
                "nodeSelector": node_selector
            }
        }

        logging.info("IR successfully created")
        return ir_dict
    except KeyError as e:
        logging.error(f"Missing key in JSON document: {e}")
        raise e
    except Exception as e:
        logging.error(f"Error parsing JSON document: {e}")
        raise e


def llm_create_IR(json_doc):
    try:

        if check_is_external_template(json_doc):
            return execute_external_IR(json_doc)

        block_data = json_doc['body']['spec']['values']

        logging.info("Parsing componentUri field")
        component_uri = block_data.get('blockComponentURI')

        logging.info("Parsing blockId field")
        block_id = block_data.get('blockId')

        block_dict = {
            "componentUri": component_uri,
            "id": block_id,
            "policies": {},
            "blockInitData": block_data.get('blockInitData', {}),
            "customMetrics": block_data.get('enabledCustomMetrics', []),
        }

        logging.info("Parsing policyRulesSpec field")
        for policy in block_data.get('policyRulesSpec', []):
            try:
                policy_name = policy['values']['name']
                policy_data = {
                    "policyRuleURI": policy['values'].get('policyRuleURI', ''),
                    "parameters": policy['values'].get('parameters', {}),
                    "settings": policy['values'].get('settings', {}),
                    "initData": {}
                }

                block_dict["policies"][policy_name] = policy_data
                logging.info(f"Parsed policy: {policy_name}")
            except KeyError as e:
                logging.error(f"Missing key in policy: {e}")
            except Exception as e:
                logging.error(f"Error parsing policy: {e}")

        return block_dict
    except KeyError as e:
        logging.error(f"Missing key in JSON document: {e}")
        raise e
    except Exception as e:
        logging.error(f"Error parsing JSON document: {e}")
        raise e


def llm_vdag_manual_create_IR(json_doc):
    try:

        if check_is_external_template(json_doc):
            return execute_external_IR(json_doc)

        vdag_data = json_doc['body']['spec']['values']

        logging.info("Parsing discoveryTags field")
        discovery_tags = vdag_data.get('discoveryTags', [])

        logging.info("Parsing controller field")
        controller = vdag_data.get('controller', {})

        logging.info("Parsing inputSources field")
        input_sources = controller.get('inputSources', [])

        logging.info("Parsing initParameters field")
        init_parameters = controller.get('initParameters', {})

        logging.info("Parsing initSettings field")
        init_settings = controller.get('initSettings', {})

        logging.info("Parsing policies field")
        policies = controller.get('policies', [])

        logging.info("Parsing nodes field")
        nodes_data = vdag_data.get('nodes', [])
        nodes = []

        for node in nodes_data:
            logging.info(
                f"Parsing node with label: {node['spec']['values'].get('nodeLabel', 'unknown')}")

            spec = node.get('spec', {}).get('values', {})
            io_map = node.get('IOMap', [])

            node_dict = {
                "nodeLabel": spec.get('nodeLabel', ''),
                "nodeType": spec.get('nodeType', ''),
                "assignmentPolicyRule": spec.get('assignmentPolicyRule', {}),
                "preprocessingPolicyRule": spec.get('preprocessingPolicyRule', {}),
                "postprocessingPolicyRule": spec.get('postprocessingPolicyRule', {}),
                "modelParameters": spec.get('modelParameters', {}),
                "outputProtocol": spec.get('outputProtocol', {}),
                "inputProtocol": spec.get('inputProtocol', {}),
                "IOMap": io_map
            }

            nodes.append(node_dict)

        logging.info("Parsing graph field")
        graph = vdag_data.get('graph', {})

        vdag_dict = {
            "discoveryTags": discovery_tags,
            "controller": {
                "inputSources": input_sources,
                "initParameters": init_parameters,
                "initSettings": init_settings,
                "policies": policies
            },
            "nodes": nodes,
            "graph": graph
        }

        logging.info(f"g: {vdag_dict}")

        return vdag_dict
    except KeyError as e:
        logging.error(f"Missing key in JSON document: {e}")
        raise e
    except Exception as e:
        logging.error(f"Error parsing JSON document: {e}")
        raise e


type_action_dispatcher = {
    "blockCreate": block_create_IR,
    "createCluster": cluster_create_IR,
    "vdagCreate": create_vdag_IR,
    "parameterUpdate": None,
    "llmCreate": llm_create_IR,
    "llmVDAGCreate": llm_vdag_manual_create_IR,
    "search": search_IR
}


def ir(spec: dict, action: str):
    try:

        if action not in type_action_dispatcher:
            raise Exception(f"invalid action {action}")

        action_function = type_action_dispatcher[action]
        return action_function(spec)

    except Exception as e:
        raise e
