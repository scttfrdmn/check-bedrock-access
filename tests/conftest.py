"""
Test configuration for the AWS Bedrock Access Checker.
This file contains fixtures for both mocked and real AWS credentials testing.
"""

import os
import json
from unittest.mock import patch, MagicMock

import boto3
import pytest
from moto import mock_sts, mock_bedrock, mock_sagemaker, mock_servicequotas


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    yield
    os.environ.pop("AWS_ACCESS_KEY_ID", None)
    os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
    os.environ.pop("AWS_SECURITY_TOKEN", None)
    os.environ.pop("AWS_SESSION_TOKEN", None)
    os.environ.pop("AWS_DEFAULT_REGION", None)


@pytest.fixture
def mock_aws(aws_credentials):
    """Mock AWS services using moto."""
    with mock_sts(), mock_bedrock(), mock_sagemaker(), mock_servicequotas():
        yield


@pytest.fixture
def mock_foundation_models_response():
    """Mocked response for list_foundation_models Bedrock API call."""
    return {
        'modelSummaries': [
            {
                'modelId': 'anthropic.claude-3-sonnet-20240229-v1:0',
                'modelName': 'Claude 3 Sonnet',
                'providerName': 'Anthropic'
            },
            {
                'modelId': 'anthropic.claude-3-haiku-20240307-v1:0',
                'modelName': 'Claude 3 Haiku',
                'providerName': 'Anthropic'
            },
            {
                'modelId': 'amazon.titan-text-express-v1',
                'modelName': 'Titan Text Express',
                'providerName': 'Amazon'
            },
            {
                'modelId': 'amazon.titan-embed-text-v1',
                'modelName': 'Titan Embeddings',
                'providerName': 'Amazon'
            }
        ]
    }


@pytest.fixture
def mock_model_details_response():
    """Mocked response for get_foundation_model Bedrock API call."""
    return {
        'modelDetails': {
            'name': 'Claude 3 Sonnet',
            'providerName': 'Anthropic',
            'inputModalities': ['TEXT', 'IMAGE'],
            'outputModalities': ['TEXT'],
            'responseStreamingSupported': True,
            'inferenceParameters': {
                'maxTokens': {'type': 'integer', 'defaultValue': '4096'},
                'temperature': {'type': 'float', 'defaultValue': '0.7'},
                'topP': {'type': 'float', 'defaultValue': '1.0'}
            }
        }
    }


@pytest.fixture
def mock_model_invoke_response():
    """Mocked response for invoke_model Bedrock API call."""
    class MockResponse:
        def __init__(self):
            self.body = MagicMock()
            self.body.read.return_value = json.dumps({
                'content': [{'type': 'text', 'text': 'Hello world!'}]
            }).encode()
    
    return MockResponse()


@pytest.fixture
def mock_servicequotas_response():
    """Mocked response for list_service_quotas ServiceQuotas API call."""
    return {
        'Quotas': [
            {
                'QuotaName': 'Claude 3 Tokens per minute',
                'Value': 50000,
                'Unit': 'TPM',
                'Adjustable': True
            },
            {
                'QuotaName': 'Claude 3 Requests per minute',
                'Value': 500,
                'Unit': 'RPM',
                'Adjustable': True
            }
        ]
    }


@pytest.fixture
def use_real_aws():
    """Skip tests if real AWS credentials are not available."""
    try:
        # Check for real AWS credentials by attempting to use the default profile
        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials is None:
            pytest.skip("Real AWS credentials not available, skipping test")
    except Exception:
        pytest.skip("Real AWS credentials not available, skipping test")
    return session