#!/bin/bash
# 
# Run the AWS Bedrock Access Verification Tool using Docker
#

# Create output directory if it doesn't exist
mkdir -p ./reports

# Check if .aws directory exists
if [ ! -d "${HOME}/.aws" ]; then
  echo "Warning: AWS credentials directory not found at ${HOME}/.aws"
  echo "You may need to run 'aws configure' first to set up credentials."
fi

# Run the Docker container
docker run --rm -it \
  -v "${HOME}/.aws:/home/bedrock-checker/.aws:ro" \
  -v "$(pwd)/reports:/tmp/bedrock-reports" \
  "$(docker build -q .)" "$@"

echo ""
echo "Any report outputs have been saved to the ./reports directory."