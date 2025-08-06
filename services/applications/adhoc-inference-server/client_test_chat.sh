curl -X POST http://35.247.86.57:31504/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
        "model": "magistral-small-2506-llama-cpp-block",
        "session_id": "chat-session-001",
        "seq_no": 1001,
        "messages": {"mode": "chat", "message": "hello"},
        "graph": {},
        "selection_query": {}
      }'
