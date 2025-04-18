import os, sys
from subprocess import call

labels = {
    "primary" : True,
    "framedb" : ""
}

nodes = sys.argv[1].split(",")
for idx, node in enumerate(nodes) :
    label_strings = []
    for label, value in labels.items() :
        if label == "framedb" :
            value = "framedb-{}".format(idx)

        label_strings.append("{}={}".format(label, value))

    call(['kubectl', 'label', 'nodes', node, *label_strings, '--overwrite'])
    print('Assigned labels to {}'.format(node))