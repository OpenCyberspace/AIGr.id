import os 
import sys
import yaml
import json
import argparse
from subprocess import call

nodes_list = sys.argv[1].split(",")

address = "https://52.86.96.95:6443"

production_values = yaml.load(open('values-production.yaml'))

for idx, node in enumerate(nodes_list) :
    production_values['master']['nodeSelector']['framedb'] = node
    production_values['slave']['nodeSelector']['framedb'] = node
    
    yaml_name = 'production-{}.yaml'.format(node)
    yaml.dump(production_values, open(yaml_name, 'w'))

    call([
        'helm', 
        'install', 
        node, 
        'bitnami/redis',  
        '--insecure-skip-tls-verify',
        '--create-namespace=true',
        '--namespace=framedb',
        '--values', 
        yaml_name
    ])

