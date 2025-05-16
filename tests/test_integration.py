"""
Integration tests for the bedrock_access_checker package.
These tests require real AWS credentials to run.
"""

import os
import pytest
from unittest.mock import patch

from bedrock_access_checker.checker import (
    check_aws_credentials,
    check_bedrock_regions,
    check_bedrock_runtime_access,
    check_bedrock_models
)


@pytest.mark.integration
def test_check_aws_credentials_with_real_creds(use_real_aws):
    """Test AWS credentials checking with real credentials."""
    # Test with default profile (should succeed with real credentials)
    result = check_aws_credentials()
    assert result is True


@pytest.mark.integration
def test_check_bedrock_regions_with_real_creds(use_real_aws):
    """Test Bedrock region checking with real credentials."""
    # Use limited set of regions to avoid long tests
    test_regions = ['us-east-1']
    
    # Silence output for cleaner test results
    with patch('bedrock_access_checker.checker.console.print'):
        regions = check_bedrock_regions(regions_to_check=test_regions)
    
    # Check that we got any regions (might be empty if account doesn't have Bedrock access)
    # We don't assert specific regions are available because that depends on the account
    assert isinstance(regions, list)


@pytest.mark.integration
def test_check_bedrock_runtime_access_with_real_creds(use_real_aws):
    """Test Bedrock runtime access with real credentials."""
    # Use us-east-1 which is commonly available
    region = 'us-east-1'
    
    # Silence output for cleaner test results
    with patch('bedrock_access_checker.checker.console.print'):
        result = check_bedrock_runtime_access(region)
    
    # The result will depend on whether the account has Bedrock access
    # We'll assert the function doesn't crash
    assert result in [True, False]


@pytest.mark.integration
def test_check_bedrock_models_with_real_creds(use_real_aws):
    """Test Bedrock models checking with real credentials."""
    # Use us-east-1 which is commonly available
    region = 'us-east-1'
    
    # Silence output for cleaner test results
    with patch('bedrock_access_checker.checker.console.print'):
        # This doesn't return a value, just updates check_results
        check_bedrock_models(region)
    
    # Import check_results to verify updates
    from bedrock_access_checker.checker import check_results
    
    # Verify that we have some results (might be empty if account doesn't have access)
    assert "bedrock_models" in check_results
    assert "available" in check_results["bedrock_models"]
    assert isinstance(check_results["bedrock_models"]["available"], list)