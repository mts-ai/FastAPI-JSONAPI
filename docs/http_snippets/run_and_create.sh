#!/usr/bin/env bash

echo "Create HTTP and Python snippets"

for filename in ./"$1"*.json; do
  echo "process $filename"
  httpsnippet "$filename" --target http --output ./snippets -x '{"autoHost": false, "autoContentLength": false}'
  httpsnippet "$filename" --target python --client requests --output ./snippets
done

echo "Run requests"
python3 update_snippets_with_responses.py "$1"
