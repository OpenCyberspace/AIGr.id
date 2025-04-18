import json
import requests
import os
import logging


from .webhooks.clusters import ClusterClient
from .similarity_search import FilterSearch, SimilaritySearch
from .ir import search_IR


def filter_path(ir: dict):
    try:

        search = FilterSearch(ir)
        return search.execute()

    except Exception as e:
        return False, str(e)


def similarity_search_path(ir: dict):
    try:

        search = SimilaritySearch(ir)
        return search.execute()

    except Exception as e:
        return False, str(e)




def filter_IR(json_doc):
    try:
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


def filter_data(input: dict):
    try:

        filter_ir = filter_IR(input)
        return filter_path(filter_ir)

    except Exception as e:
        raise e


def similarity_search(input: dict):
    try:

        search_ir = search_IR(input)
        print(search_ir['rankingPolicyRule'])
        return similarity_search_path(search_ir)

    except Exception as e:
        raise e
