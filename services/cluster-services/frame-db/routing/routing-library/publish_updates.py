from redis import Redis
import json

connection = Redis('localhost', 6379, db = 0, password = "Friends123#")

sourceId = "test"
routing_table = "routing_updates"

key = "{}__{}".format(sourceId, routing_table)

command_test = {"command" : "remove", "payload" : ["framedb-0"]}

response = connection.publish(key, json.dumps(command_test))
print(response)