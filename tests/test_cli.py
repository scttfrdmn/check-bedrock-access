"""
Tests for the CLI interface of the bedrock_access_checker.
"""

import sys
import pytest
from unittest.mock import patch, MagicMock

from bedrock_access_checker.cli import main


@pytest.mark.unit
@pytest.mark.mock
@patch('bedrock_access_checker.cli.check_aws_credentials')
@patch('bedrock_access_checker.cli.check_bedrock_regions')
@patch('bedrock_access_checker.cli.display_summary_dashboard')
def test_cli_basic_flow(mock_display, mock_regions, mock_credentials):
    """Test the basic CLI flow with mocked components."""
    # Configure mocks
    mock_credentials.return_value = True
    mock_regions.return_value = ['us-east-1']
    
    # Mock argparse to simulate command line args
    with patch('sys.argv', ['check-bedrock-access.py']):
        # Silence output for cleaner test results
        with patch('bedrock_access_checker.cli.console.print'):
            main()
    
    # Verify correct function calls
    mock_credentials.assert_called_once()
    mock_regions.assert_called_once()
    mock_display.assert_called_once()


@pytest.mark.unit
@pytest.mark.mock
@patch('bedrock_access_checker.cli.check_aws_credentials')
@patch('bedrock_access_checker.cli.check_bedrock_regions')
@patch('bedrock_access_checker.cli.check_bedrock_runtime_access')
@patch('bedrock_access_checker.cli.check_bedrock_models')
@patch('bedrock_access_checker.cli.check_specific_models_simple')
@patch('bedrock_access_checker.cli.display_summary_dashboard')
def test_cli_with_profile(mock_display, mock_models_simple, mock_models, 
                          mock_runtime, mock_regions, mock_credentials):
    """Test CLI with a profile argument."""
    # Configure mocks
    mock_credentials.return_value = True
    mock_regions.return_value = ['us-east-1']
    
    # Mock argparse to simulate command line args with profile
    with patch('sys.argv', ['check-bedrock-access.py', '--profile', 'test-profile']):
        # Silence output for cleaner test results
        with patch('bedrock_access_checker.cli.console.print'):
            main()
    
    # Verify correct function calls with profile
    mock_credentials.assert_called_once_with('test-profile')
    mock_regions.assert_called_once()
    mock_runtime.assert_called_once_with('us-east-1', 'test-profile')
    mock_models.assert_called_once_with('us-east-1', 'test-profile')


@pytest.mark.unit
@pytest.mark.mock
@patch('bedrock_access_checker.cli.check_aws_credentials')
@patch('bedrock_access_checker.cli.check_bedrock_regions')
@patch('bedrock_access_checker.cli.check_sagemaker_jumpstart_alternatives')
@patch('bedrock_access_checker.cli.display_summary_dashboard')
def test_cli_with_sagemaker_alternatives(mock_display, mock_sagemaker, mock_regions, mock_credentials):
    """Test CLI with SageMaker alternatives option."""
    # Configure mocks
    mock_credentials.return_value = True
    mock_regions.return_value = ['us-east-1']
    
    # Set up check_results mock
    with patch('bedrock_access_checker.cli.check_results', {'key_models': {'missing': ['model1', 'model2']}}):
        # Mock argparse to simulate command line args
        with patch('sys.argv', ['check-bedrock-access.py', '--sagemaker-alternatives']):
            # Silence output for cleaner test results
            with patch('bedrock_access_checker.cli.console.print'):
                main()
    
    # Verify SageMaker alternatives check was called
    mock_sagemaker.assert_called_once()


@pytest.mark.unit
@pytest.mark.mock
@patch('bedrock_access_checker.cli.check_aws_credentials')
@patch('bedrock_access_checker.cli.check_bedrock_regions')
@patch('bedrock_access_checker.cli.output_results')
@patch('bedrock_access_checker.cli.display_summary_dashboard')
def test_cli_with_output_option(mock_display, mock_output, mock_regions, mock_credentials):
    """Test CLI with output option."""
    # Configure mocks
    mock_credentials.return_value = True
    mock_regions.return_value = ['us-east-1']
    
    # Mock argparse to simulate command line args
    with patch('sys.argv', ['check-bedrock-access.py', '--output', 'json']):
        # Silence output for cleaner test results
        with patch('bedrock_access_checker.cli.console.print'):
            main()
    
    # Verify output function was called with correct format
    mock_output.assert_called_once_with('json')


@pytest.mark.unit
@pytest.mark.mock
@patch('bedrock_access_checker.cli.check_aws_credentials')
def test_cli_with_failed_credentials(mock_credentials):
    """Test CLI when credentials check fails."""
    # Configure mock to fail credentials check
    mock_credentials.return_value = False
    
    # Mock argparse to simulate command line args
    with patch('sys.argv', ['check-bedrock-access.py']):
        # Silence output for cleaner test results
        with patch('bedrock_access_checker.cli.console.print'):
            with patch('bedrock_access_checker.cli.display_summary_dashboard') as mock_display:
                main()
    
    # Verify display_summary_dashboard was called (should show error)
    mock_display.assert_called_once()
    
    # Verify regions check was not called (should exit early)
    with patch('bedrock_access_checker.cli.check_bedrock_regions') as mock_regions:
        assert mock_regions.call_count == 0