# AWS Bedrock Access Verification Tool

A comprehensive utility to check if your AWS credentials have the necessary permissions to access AWS Bedrock services and models, with a helpful dashboard, troubleshooting assistance, and detailed reporting.

## Features

- **Complete AWS Bedrock Verification:**
  - Validates AWS credentials and IAM permissions
  - Checks Bedrock availability in common regions
  - Verifies access to bedrock-runtime service
  - Lists available foundation models
  - Validates access to specific key models (Claude, Titan, etc.)

- **Clear Visual Dashboard:**
  - Summary dashboard showing overall status
  - Traffic light indicators (green/yellow/red) for key components
  - Detailed counts of available regions and models
  - Timestamp and environment information

- **Troubleshooting Assistance:**  
  - Detailed guidance for fixing common issues
  - Specific remediation steps for different error types
  - Links to relevant AWS documentation
  - IAM permission suggestions

- **Flexible Configuration:**
  - Support for AWS profiles
  - Interactive profile selection mode
  - Export results to JSON or CSV

## Requirements

- Python 3.6+
- boto3 >= 1.28.0 (for Bedrock support)
- rich (for console formatting)

## Installation

### Option 1: Install required packages

```bash
# Install required packages
pip install boto3 rich

# Or using the requirements.txt file
pip install -r requirements.txt
```

### Option 2: Use a virtual environment

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Option 3: Use pipx (Recommended)

[pipx](https://github.com/pypa/pipx) is a tool to run Python applications in isolated environments:

```bash
# Install pipx
pip install --user pipx
pipx ensurepath

# Run directly from GitHub (no installation required)
pipx run --spec git+https://github.com/scttfrdmn/check-bedrock-access.git check-bedrock-access.py
```

## Usage

### Basic Options

```bash
# Basic usage (uses default profile)
python check-bedrock-access.py

# Use a specific AWS profile
python check-bedrock-access.py --profile myprofile

# Interactive profile selection
python check-bedrock-access.py --interactive

# Export results to JSON
python check-bedrock-access.py --output json

# Export results to CSV
python check-bedrock-access.py --output csv
```

### Using with pipx

```bash
# Run with default profile
pipx run --spec git+https://github.com/scttfrdmn/check-bedrock-access.git check-bedrock-access.py

# With a specific profile
pipx run --spec git+https://github.com/scttfrdmn/check-bedrock-access.git check-bedrock-access.py --profile your-profile

# Interactive mode
pipx run --spec git+https://github.com/scttfrdmn/check-bedrock-access.git check-bedrock-access.py --interactive
```

## Screenshots

_(Example screenshot of the dashboard would go here)_

## Troubleshooting

If you encounter issues with Bedrock access, the tool will provide specific troubleshooting steps. Common solutions include:

- Ensure your AWS account has Bedrock enabled
- Verify your IAM permissions include necessary Bedrock actions
- Check that boto3 is updated to version 1.28.0 or newer
- Confirm model access in the AWS Bedrock console

## License

MIT