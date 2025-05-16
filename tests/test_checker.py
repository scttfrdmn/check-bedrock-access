"""
Unit tests for the bedrock_access_checker.checker module.
These tests use mocked AWS responses to test the functionality.
"""

import pytest
from unittest.mock import patch, MagicMock

from bedrock_access_checker.checker import (
    check_aws_credentials,
    check_bedrock_regions,
    check_bedrock_models,
    test_model_invocation,
    get_model_quotas_and_details
)


@pytest.mark.unit
@pytest.mark.mock
def test_check_aws_credentials(mock_aws):
    """Test the AWS credentials checking function."""
    # Test with default profile
    result = check_aws_credentials()
    assert result is True
    
    # Test with specific profile
    result = check_aws_credentials(profile_name="test-profile")
    # This should return False because the test profile doesn't exist
    assert result is False


@pytest.mark.unit
@pytest.mark.mock
@patch('bedrock_access_checker.checker.boto3.Session')
def test_check_bedrock_regions(mock_session, mock_foundation_models_response):
    """Test the Bedrock regions checking function."""
    # Configure the mock
    mock_session_instance = MagicMock()
    mock_client = MagicMock()
    mock_session_instance.client.return_value = mock_client
    mock_session.return_value = mock_session_instance
    
    # Set up the mock to return success for us-east-1 and failure for us-west-2
    def mock_list_foundation_models(**kwargs):
        if kwargs.get('region_name') == 'us-east-1':
            return mock_foundation_models_response
        else:
            raise Exception("Service not available in this region")
    
    mock_client.list_foundation_models.side_effect = mock_list_foundation_models
    
    # Test with specific regions
    regions = check_bedrock_regions(regions_to_check=['us-east-1', 'us-west-2'])
    assert 'us-east-1' in regions
    assert 'us-west-2' not in regions
    assert len(regions) == 1


@pytest.mark.unit
@pytest.mark.mock
@patch('bedrock_access_checker.checker.boto3.Session')
def test_check_bedrock_models(mock_session, mock_foundation_models_response):
    """Test the Bedrock models checking function."""
    # Configure the mock
    mock_session_instance = MagicMock()
    mock_client = MagicMock()
    mock_session_instance.client.return_value = mock_client
    mock_session.return_value = mock_session_instance
    
    # Set up the mock to return the foundation models response
    mock_client.list_foundation_models.return_value = mock_foundation_models_response
    
    # Test the function
    check_bedrock_models('us-east-1')
    
    # Verify that the function made the correct API call
    mock_client.list_foundation_models.assert_called_once()
    
    # Verify that models were added to the results
    from bedrock_access_checker.checker import check_results
    assert len(check_results["bedrock_models"]["available"]) == 4
    assert "anthropic.claude-3-sonnet-20240229-v1:0" in check_results["bedrock_models"]["available"]


@pytest.mark.unit
@pytest.mark.mock
@patch('bedrock_access_checker.checker.boto3.Session')
def test_test_model_invocation(mock_session, mock_model_invoke_response):
    """Test the model invocation test function."""
    # Configure the mock
    mock_session_instance = MagicMock()
    mock_client = MagicMock()
    mock_session_instance.client.return_value = mock_client
    mock_session.return_value = mock_session_instance
    
    # Set up the mock to return success
    mock_client.invoke_model.return_value = mock_model_invoke_response
    
    # Test invocation for a Claude model
    success, message = test_model_invocation('anthropic.claude-3-sonnet-20240229-v1:0', 'us-east-1')
    
    # Verify that the function made the correct API call
    mock_client.invoke_model.assert_called_once()
    
    # Check the result
    assert success is True
    assert "Success" in message


@pytest.mark.unit
@pytest.mark.mock
@patch('bedrock_access_checker.checker.boto3.Session')
def test_get_model_quotas_and_details(mock_session, mock_model_details_response, mock_servicequotas_response):
    """Test the model quota and details function."""
    # Configure the mock
    mock_session_instance = MagicMock()
    mock_bedrock_client = MagicMock()
    mock_quotas_client = MagicMock()
    
    # Configure the mock session to return different clients
    def get_mock_client(service, **kwargs):
        if service == 'bedrock':
            return mock_bedrock_client
        elif service == 'service-quotas':
            return mock_quotas_client
        else:
            raise ValueError(f"Unexpected service: {service}")
    
    mock_session_instance.client.side_effect = get_mock_client
    mock_session.return_value = mock_session_instance
    
    # Set up the mock clients to return the expected responses
    mock_bedrock_client.get_foundation_model.return_value = mock_model_details_response
    mock_quotas_client.list_service_quotas.return_value = mock_servicequotas_response
    
    # Test the function
    details = get_model_quotas_and_details('anthropic.claude-3-sonnet-20240229-v1:0', 'us-east-1')
    
    # Verify the API calls
    mock_bedrock_client.get_foundation_model.assert_called_once()
    mock_quotas_client.list_service_quotas.assert_called_once()
    
    # Check the results
    assert "specs" in details
    assert "inference_params" in details
    assert "quotas" in details
    assert details["specs"]["model_name"] == "Claude 3 Sonnet"
    assert details["inference_params"]["maxTokens"]["defaultValue"] == "4096"