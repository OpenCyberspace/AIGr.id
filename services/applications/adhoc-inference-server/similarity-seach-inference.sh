curl -X POST  http://35.232.150.117:31504/v1/infer \
  -H "Content-Type: application/json" \
  -d '{
  "model": "",
  "session_id": "session-2",
  "seq_no": 11,
  "data": {
    "mode": "chat",
    "gen_params": {
      "temperature": 0.1,
      "top_p": 0.95,
      "max_tokens": 4096
    },
    "messages": [
      {
        "content": [
          {
            "type": "text",
            "text": "Analyze the following image and generate your objective scene report.?"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "https://akm-img-a-in.tosshub.com/indiatoday/images/story/202311/chain-snatching-caught-on-camera-in-bengaluru-293151697-16x9_0.jpg"
            }
          }
        ]
      }
    ]
  },
  "graph": {},
  "selection_query": {
    "header": {
      "templateUri": "Parser/V1",
      "parameters": {}
    },
    "body": {
      "values": {
        "matchType": "block",
        "rankingPolicyRule": {
          "values": {
            "policyRuleURI": "non-llm-matcher:2.0-stable",
            "settings": {},
            "parameters": {
              "filterRule": {
                "matchType": "block",
                "filter": {
                  "blockQuery": {
                    "logicalOperator": "AND",
                    "conditions": [
                      {
                        "variable": "component.componentMetadata.framework",
                        "operator": "==",
                        "value": "llama-cpp-python"
                      },
                      {
                        "variable": "component.componentMetadata.supports_quantization",
                        "value": true,
                        "operator": "=="
                      },
                      {
                        "variable": "component.tags",
                        "value": "multi-modal",
                        "operator": "=="
                      }
                    ]
                  },
                  "blockMetricsQuery": {
                    "logicalOperator": "AND",
                    "conditions": [
                      {
                        "aggOperator": "avg",
                        "target": "instances.on_preprocess_fps",
                        "operator": ">",
                        "value": 8000
                      },
                      {
                        "aggOperator": "max",
                        "target": "instances.llm_active_sessions",
                        "value": 20,
                        "operator": ">="
                      }
                    ]
                  }
                }
              },
              "method": "hybrid",
              "user_query": "chat model",
              "threshold": 0.1
            }
          }
        }
      }
    }
  }
}'
