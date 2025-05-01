# AWS Bedrock Access Verification Tool

A simple utility to check if your AWS credentials have the necessary permissions to access AWS Bedrock services and models.

## Features

- Verifies AWS credentials and permission to access Bedrock
- Checks Bedrock availability in common regions
- Lists available foundation models
- Validates access to specific key models
- Supports AWS profiles
- Includes interactive profile selection mode

## Requirements

- Python 3.6+
- boto3 >= 1.28.0 (for Bedrock support)
- rich (for console formatting)

## Installation

```bash
# Install required packages
pip install boto3 rich
```

## Usage

```bash
# Basic usage (uses default profile)
python check-bedrock-access.py

# Use a specific AWS profile
python check-bedrock-access.py --profile myprofile

# Interactive profile selection
python check-bedrock-access.py --interactive
```

## License

MIT