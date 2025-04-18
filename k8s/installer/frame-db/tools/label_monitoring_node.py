import os 
import sys 

node_names = sys.argv[1].split(",")
for node_name in node_names :
    os.system("kubectl label nodes {} monitoring=True --overwrite".format(node_name))
