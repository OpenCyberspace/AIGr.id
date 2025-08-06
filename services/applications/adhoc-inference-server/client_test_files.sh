curl -X POST http://35.232.150.117:31504/v1/infer-multipart \
  -F "model=hello-multi-001" \
  -F "session_id=session-555" \
  -F "seq_no=3" \
  -F "ts=1721234567.89" \
  -F "data={\"message\": \"Prasanna\"}" \
  -F "file1=@./Dockerfile" \
  -F "file1_metadata={\"name\": \"input_file.pdf\", \"type\": \"document\"}"
