#!/bin/bash

echo "Get By URI"
curl -d '{"uriString" : "node.algorithms.objectdet.test_component:v0.0.2-beta"}' \
     -H "Content-Type:application/json" \
     http://localhost:4000/api/getByURI | json_pp


#echo "Get by type"
#curl -d '{"typeString": "algorithm"}' \
#     -H "Content-Type:application/json" \
#     http://localhost:4000/api/getByType | json_pp

#echo "Generic Query"
#curl -d '{"query" : {"componentMetadata.author.authorEmail" : {"$regex" : "prasa"}}}' \
#     -H "Content-Type:application/json" \
#     http://localhost:4000/api/query | json_pp
    
#echo "GRAPHQL test"
#curl -d '{"query" : "{componentMany { _id componentURI }}"}' -H "Content-Type:application/json" \
#     http://localhost:4000/gql
