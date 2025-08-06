curl -X POST  http://35.232.150.117:30893/v1/infer \
  -H "Content-Type: application/json" \
  -d '{
  "session_id": "session-abc-123",
  "seq_no": 3,
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
  "selection_query": {}
}'
