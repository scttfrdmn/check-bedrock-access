# AWS Bedrock Access Verification Tool

A comprehensive utility to check if your AWS credentials have the necessary permissions to access AWS Bedrock services and models, with a helpful dashboard, troubleshooting assistance, and detailed reporting.

## Features

- **Complete AWS Bedrock Verification:**
  - Validates AWS credentials and IAM permissions
  - Checks Bedrock availability in all supported regions
  - Verifies access to bedrock-runtime service
  - Lists available foundation models
  - Validates access to specific key models (Claude 3 family, Claude 2, Titan, etc.)
  - Performs actual model invocation tests to verify full access (optional)

- **Advanced Inference Capabilities Analysis:**
  - Retrieves model quotas and rate limits for your AWS account
  - Shows inference parameters for each model (tokens, temperature, etc.)
  - Displays supported input/output modalities (text, images)
  - Identifies streaming capabilities
  - Tests actual model inference with minimal prompts
  - Provides detailed specification for each model
  - Suggests SageMaker JumpStart alternatives for missing models

- **Clear Visual Dashboard:**
  - Summary dashboard showing overall status
  - Traffic light indicators (green/yellow/red) for key components
  - Detailed counts of available regions and models
  - Interactive HTML reports with expandable model details
  - Timestamp and environment information

- **Troubleshooting Assistance:**  
  - Detailed guidance for fixing common issues
  - Specific remediation steps for different error types
  - Links to relevant AWS documentation
  - IAM permission suggestions
  - Quota increase recommendations

- **Flexible Configuration:**
  - Support for AWS profiles
  - Interactive profile and region selection mode
  - Specific region targeting (check only regions you care about)
  - Export results to JSON, CSV, or HTML
  - Advanced mode for detailed model capabilities
  - Docker container for environment-independent deployment
  - Multiple installation methods (pip, pipx, Docker)

## Requirements

- Python 3.6+
- boto3 >= 1.28.0 (for Bedrock support)
- rich (for console formatting)

## Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/scttfrdmn/check-bedrock-access.git
cd check-bedrock-access

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Linting and Formatting

The project uses:
- flake8 for linting
- black for code formatting
- isort for import sorting

Run linting checks:

```bash
# Run all checks
pre-commit run --all-files

# Or run individual tools
black .
flake8
isort .
```

### Testing

The project uses pytest for testing. Tests are divided into:
- Unit tests with mocked AWS responses
- Integration tests requiring real AWS credentials

Run tests:

```bash
# Run all tests
pytest

# Run only unit tests
pytest -m unit

# Run only integration tests (requires AWS credentials)
pytest -m integration

# Run with coverage report
pytest --cov=bedrock_access_checker
```

The integration tests will be skipped automatically if no valid AWS credentials are found.

## Installation

### Install from PyPI

```bash
# Install from PyPI
pip install check-bedrock-access

# Run the tool
check-bedrock-access
```

### Development Installation

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

# Interactive profile selection and region selection
python check-bedrock-access.py --interactive

# Export results to various formats
python check-bedrock-access.py --output json
python check-bedrock-access.py --output csv
python check-bedrock-access.py --output html  # Creates a detailed visual report

# Check specific regions
python check-bedrock-access.py --region us-east-1 --region us-west-2

# Check all supported Bedrock regions
python check-bedrock-access.py --all-regions

# Test actual model invocation (incurs minimal AWS costs)
python check-bedrock-access.py --test-invoke

# Advanced mode with quota and inference parameter details
python check-bedrock-access.py --advanced

# Check SageMaker JumpStart alternatives for unavailable Bedrock models
python check-bedrock-access.py --sagemaker-alternatives

# Comprehensive check with all features
python check-bedrock-access.py --all-regions --test-invoke --advanced --sagemaker-alternatives
```

### Using with pipx (Recommended for One-Time Use)

[pipx](https://github.com/pypa/pipx) lets you run Python applications in isolated environments without installation:

```bash
# Install pipx if you don't have it
pip install --user pipx
pipx ensurepath

# Run with default profile
pipx run --spec git+https://github.com/scttfrdmn/check-bedrock-access.git check-bedrock-access.py

# With a specific profile
pipx run --spec git+https://github.com/scttfrdmn/check-bedrock-access.git check-bedrock-access.py --profile your-profile

# Advanced mode with model invocation testing
pipx run --spec git+https://github.com/scttfrdmn/check-bedrock-access.git check-bedrock-access.py --test-invoke --advanced
```

### Using with pyenv

If you use [pyenv](https://github.com/pyenv/pyenv) to manage Python versions:

```bash
# Make sure you have the right Python version active
pyenv install 3.9.0
pyenv local 3.9.0

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install and run
pip install -e .
check-bedrock-access --interactive
```

### Using with Docker

You can run the tool using Docker without installing Python or any dependencies locally:

```bash
# Using the provided convenience script
./docker-run.sh --interactive

# Or using docker-compose
docker-compose up --build

# Run with specific options
./docker-run.sh --profile myprofile --all-regions --test-invoke

# Export HTML report to the mounted reports directory
./docker-run.sh --output html
```

The Docker container:
- Mounts your local `~/.aws` directory for credentials (read-only)
- Creates a `./reports` directory for output files
- Runs with a non-root user for better security
- Works with all tool features including interactive mode

## Example Output

### Status Dashboard

When you run the tool, you'll see a comprehensive dashboard like this:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Status Dashboard                                     │
└─────────────────────────────────────────────────────────────────────────────┘
┌───────────────┬───────────────┬───────────────────────────────────────────────┐
│ Component     │ Status        │ Details                                       │
├───────────────┼───────────────┼───────────────────────────────────────────────┤
│ AWS Credentials │ ✅ SUCCESS  │ Valid AWS credentials found from: Profile 'dev' │
│ Bedrock Regions │ ✅ SUCCESS  │ 2 available regions: us-east-1, us-west-2       │
│ Bedrock Runtime │ ✅ SUCCESS  │ Runtime service accessible                      │
│ Bedrock Models  │ ✅ SUCCESS  │ 17 models available                            │
│ Key Models      │ ⚠️ WARNING  │ 5/11 key models available (partial access)     │
│ Model Invocation│ ✅ SUCCESS  │ 5/5 models invoked successfully                │
└───────────────┴───────────────┴───────────────────────────────────────────────┘

Overall Status: ⚠️ WARNING
Your Bedrock setup has some issues but may work for some use cases
```

### SageMaker JumpStart Alternatives

For models you don't have access to, the tool can suggest alternatives available in SageMaker JumpStart:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SageMaker JumpStart Alternatives                         │
└─────────────────────────────────────────────────────────────────────────────┘
┌────────────────────────────────────┬─────────────────────────┬────────────────────────────────────┐
│ Missing Bedrock Model              │ JumpStart Alternative    │ Notes                              │
├────────────────────────────────────┼─────────────────────────┼────────────────────────────────────┤
│ anthropic.claude-3-opus-20240229-v1:0 │ Meta Llama 2 (70B)   │ Open source alternative with strong │
│                                     │ (huggingface-llm-llama-2-70b) │ capabilities               │
│                                     │ Mistral (7B)           │ Open source model with good         │
│                                     │ (huggingface-llm-mistral-7b) │ performance for its size     │
├────────────────────────────────────┼─────────────────────────┼────────────────────────────────────┤
│ amazon.titan-embed-text-v2:0       │ BGE Large Embeddings    │ Strong text embedding alternative   │
│                                     │ (huggingface-textembedding-bge-large-en) │                  │
└────────────────────────────────────┴─────────────────────────┴────────────────────────────────────┘
```

### Model Details (Advanced Mode)

In advanced mode, you'll see detailed information for each model:

```
Details for anthropic.claude-3-sonnet-20240229-v1:0
┌──────────────────────────┬───────────────────────────────────────────────────┐
│ Parameter                │ Value                                             │
├──────────────────────────┼───────────────────────────────────────────────────┤
│ Spec: model_name         │ Claude 3 Sonnet                                   │
│ Spec: provider           │ Anthropic                                         │
│ Spec: input_modalities   │ ['TEXT', 'IMAGE']                                 │
│ Spec: output_modalities  │ ['TEXT']                                          │
│ Spec: response_streaming_supported │ True                                    │
│ Param: maxTokens         │ {"type": "integer", "defaultValue": "4096"}       │
│ Param: temperature       │ {"type": "float", "defaultValue": "0.7"}          │
│ Param: topP              │ {"type": "float", "defaultValue": "1.0"}          │
│ Param: stopSequences     │ {"type": "array", "defaultValue": "[]"}           │
│ Quota: TPM for Claude 3  │ 50000 TPM (adjustable)                            │
│ Quota: RPM for Claude 3  │ 500 RPM (adjustable)                              │
└──────────────────────────┴───────────────────────────────────────────────────┘
```

### HTML Report

With `--output html`, you'll get a comprehensive visual report that includes:

- A summary dashboard with traffic light indicators
- Detailed region availability map
- Model cards showing access status and capabilities
- Invocation test results (when used with `--test-invoke`)
- Quota information and inference parameters (when used with `--advanced`)
- Troubleshooting recommendations

![Example HTML Report](https://example.com/report_screenshot.png)

## Screenshots

![Dashboard Screenshot](https://example.com/dashboard.png)
![Model Details Screenshot](https://example.com/model_details.png)

## Troubleshooting

If you encounter issues with Bedrock access, the tool will provide specific troubleshooting steps. Common solutions include:

- Ensure your AWS account has Bedrock enabled
- Verify your IAM permissions include necessary Bedrock actions
- Check that boto3 is updated to version 1.28.0 or newer
- Confirm model access in the AWS Bedrock console

## License

MIT