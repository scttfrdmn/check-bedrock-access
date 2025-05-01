#!/usr/bin/env python3
"""
AWS Bedrock Access Verification Tool

This script checks if your AWS credentials have the necessary permissions
to access AWS Bedrock services and models, with support for AWS profiles.
Uses modern importlib.metadata instead of pkg_resources.
"""

import boto3
import json
import sys
import os
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

# Modern imports to replace pkg_resources
try:
    # Python 3.8+
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    # Python < 3.8
    from importlib_metadata import version, PackageNotFoundError

# Initialize Rich console
console = Console()

# Version comparison utility
def is_version_less_than(v1, v2):
    """Compare two version strings"""
    try:
        v1_parts = [int(x) for x in v1.split('.')]
        v2_parts = [int(x) for x in v2.split('.')]
        
        for i in range(min(len(v1_parts), len(v2_parts))):
            if v1_parts[i] < v2_parts[i]:
                return True
            elif v1_parts[i] > v2_parts[i]:
                return False
        
        # If we get here, the common parts are equal, so the shorter version is less
        return len(v1_parts) < len(v2_parts)
    except (ValueError, AttributeError):
        # If comparison fails, assume versions are compatible
        return False

def list_available_profiles():
    """List all available AWS profiles configured on the system"""
    try:
        # Check if AWS credentials file exists
        credentials_file = os.path.expanduser("~/.aws/credentials")
        config_file = os.path.expanduser("~/.aws/config")
        
        if not (os.path.exists(credentials_file) or os.path.exists(config_file)):
            return []
        
        # Use boto3 to get profiles
        session = boto3.Session()
        available_profiles = session.available_profiles
        return available_profiles
    
    except Exception as e:
        console.print(f"[bold red]Error listing profiles: {e}[/bold red]")
        return []

def check_aws_credentials(profile_name=None):
    """
    Check if AWS credentials are configured
    
    Args:
        profile_name (str, optional): AWS profile name to use
    
    Returns:
        bool: True if valid credentials found, False otherwise
    """
    if profile_name:
        console.print(f"[bold]Checking AWS credentials for profile: [cyan]{profile_name}[/cyan]...[/bold]")
    else:
        console.print("[bold]Checking AWS credentials (default profile)...[/bold]")
    
    # If profile specified, check if it exists
    if profile_name:
        available_profiles = list_available_profiles()
        if profile_name not in available_profiles:
            console.print(f"[bold red]Profile '{profile_name}' not found in AWS configuration![/bold red]")
            console.print(f"[yellow]Available profiles: {', '.join(available_profiles) if available_profiles else 'None'}[/yellow]")
            return False
    
    # Check environment variables (only relevant for default profile)
    has_env_credentials = False
    if not profile_name:
        has_env_credentials = "AWS_ACCESS_KEY_ID" in os.environ and "AWS_SECRET_ACCESS_KEY" in os.environ
    
    # Check credential file
    credentials_file = os.path.expanduser("~/.aws/credentials")
    config_file = os.path.expanduser("~/.aws/config")
    has_file_credentials = os.path.exists(credentials_file) or os.path.exists(config_file)
    
    if not (has_env_credentials or has_file_credentials):
        console.print("[bold red]No AWS credentials found![/bold red]")
        console.print("Please set up your AWS credentials using one of these methods:")
        console.print("1. Run 'aws configure' to create credentials file")
        console.print("2. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables (default profile only)")
        return False
    
    # Try creating a session
    try:
        session = boto3.Session(profile_name=profile_name)
        credentials = session.get_credentials()
        
        if credentials is None:
            console.print("[bold red]AWS credentials found but not valid![/bold red]")
            return False
            
        # Show credential source (not the actual credentials)
        if profile_name:
            cred_source = f"Profile '{profile_name}'"
        else:
            cred_source = "Environment variables" if has_env_credentials else \
                         "Credentials file (default profile)" if has_file_credentials else \
                         "Unknown source"
        
        console.print(f"[green]✓ Valid AWS credentials found from: {cred_source}[/green]")
        
        # Print boto3 version for debugging
        import botocore
        try:
            boto3_version = version('boto3')
            botocore_version = version('botocore')
            console.print(f"[dim]boto3 version: {boto3_version}[/dim]")
            console.print(f"[dim]botocore version: {botocore_version}[/dim]")
            
            # Check if boto3 version might be too old
            MIN_BOTO3_VERSION = "1.28.0"
            if is_version_less_than(boto3_version, MIN_BOTO3_VERSION):
                console.print(f"[yellow]Warning: Your boto3 version ({boto3_version}) might be too old for Bedrock![/yellow]")
                console.print(f"[yellow]Recommended version is {MIN_BOTO3_VERSION} or newer.[/yellow]")
        except PackageNotFoundError:
            console.print("[dim]Could not determine boto3 version[/dim]")
        
        # Print account information if possible (without exposing sensitive data)
        try:
            sts_client = session.client('sts')
            identity = sts_client.get_caller_identity()
            account_id = identity['Account']
            user_id = identity['UserId']
            # Mask most of the account ID for security
            masked_account = f"{account_id[:4]}...{account_id[-4:]}"
            # For user ID, keep the type but mask the actual ID
            if '/' in user_id:
                user_type, user_value = user_id.split('/', 1)
                masked_user = f"{user_type}/****"
            else:
                masked_user = "****"
            
            console.print(f"[dim]AWS Account: {masked_account}[/dim]")
            console.print(f"[dim]Identity Type: {masked_user}[/dim]")
        except Exception:
            # Don't show error if this fails
            pass
        
        return True
        
    except Exception as e:
        console.print(f"[bold red]Error checking AWS credentials: {e}[/bold red]")
        return False

def check_bedrock_regions(profile_name=None):
    """
    Check which regions have Bedrock available
    
    Args:
        profile_name (str, optional): AWS profile name to use
    
    Returns:
        list: List of available regions
    """
    console.print("\n[bold]Checking Bedrock availability in regions...[/bold]")
    
    # Common regions to check
    regions_to_check = [
        'us-east-1', 
        'us-west-2', 
    ]
    
    # Create a table for results
    table = Table(title="Bedrock Region Availability")
    table.add_column("Region", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Message", style="yellow")
    
    available_regions = []
    
    # Create session with profile if specified
    session = boto3.Session(profile_name=profile_name)
    
    for region in regions_to_check:
        try:
            # Try to create a Bedrock client
            client = session.client('bedrock', region_name=region)
            
            # Try a simple operation - without parameters
            try:
                client.list_foundation_models()
                table.add_row(region, "✓ Available", "Successfully connected")
                available_regions.append(region)
            except Exception as op_error:
                error_msg = str(op_error)
                if "AccessDeniedException" in error_msg:
                    table.add_row(region, "✗ No access", "Permission denied")
                elif "not authorized" in error_msg.lower():
                    table.add_row(region, "✗ No access", "Not authorized")
                else:
                    table.add_row(region, "✗ Error", error_msg[:50])
                
        except Exception as e:
            error_msg = str(e)
            if "Could not connect to the endpoint URL" in error_msg:
                table.add_row(region, "✗ Not available", "Bedrock not available in this region")
            elif "ResourceNotFoundException" in error_msg:
                table.add_row(region, "✗ Not available", "Bedrock not found in this region")
            else:
                table.add_row(region, "✗ Error", error_msg[:50])
    
    console.print(table)
    return available_regions

def check_bedrock_runtime_access(region, profile_name=None):
    """
    Check if bedrock-runtime service is accessible
    
    Args:
        region (str): AWS region to check
        profile_name (str, optional): AWS profile name to use
    
    Returns:
        bool: True if accessible, False otherwise
    """
    console.print(f"\n[bold]Checking bedrock-runtime service in {region}...[/bold]")
    
    try:
        # Create session with profile if specified
        session = boto3.Session(profile_name=profile_name)
        
        # Create bedrock-runtime client
        client = session.client('bedrock-runtime', region_name=region)
        
        # We can't make a simple call without invoking a model, so we'll just check if the client initializes
        console.print(f"[green]✓ bedrock-runtime client created successfully in {region}[/green]")
        return True
    except Exception as e:
        console.print(f"[bold red]Error creating bedrock-runtime client: {e}[/bold red]")
        return False

def check_bedrock_models(region, profile_name=None):
    """
    Check which Bedrock models are available in the specified region
    
    Args:
        region (str): AWS region to check
        profile_name (str, optional): AWS profile name to use
    """
    console.print(f"\n[bold]Checking available Bedrock models in {region}...[/bold]")
    
    try:
        # Create session with profile if specified
        session = boto3.Session(profile_name=profile_name)
        
        # Create Bedrock client
        client = session.client('bedrock', region_name=region)
        
        # List foundation models - without parameters
        response = client.list_foundation_models()
        
        # Create a table for results
        table = Table(title=f"Bedrock Models in {region}")
        table.add_column("Model ID", style="cyan")
        table.add_column("Provider", style="blue")
        table.add_column("Status", style="green")
        
        # Check if any models are returned
        if 'modelSummaries' not in response or not response['modelSummaries']:
            console.print("[yellow]No models found in the response. Your account may not have Bedrock enabled.[/yellow]")
            return
        
        # Process models
        for model in response.get('modelSummaries', []):
            model_id = model.get('modelId')
            provider = model.get('providerName', 'Unknown')
            
            # Instead of checking for access, we'll just show if the model is listed
            table.add_row(model_id, provider, "Listed")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error checking Bedrock models: {e}[/bold red]")

def check_specific_models_simple(region, profile_name=None):
    """
    Check specific models needed for common Bedrock use cases
    
    Args:
        region (str): AWS region to check
        profile_name (str, optional): AWS profile name to use
    """
    console.print(f"\n[bold]Checking key Bedrock model access in {region}...[/bold]")
    
    needed_models = [
        "amazon.titan-embed-text-v1",
        "amazon.titan-embed-text-v2:0",
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0"
    ]
    
    try:
        # Create session with profile if specified
        session = boto3.Session(profile_name=profile_name)
        
        # Create bedrock client
        client = session.client('bedrock', region_name=region)
        
        # Get all available models
        response = client.list_foundation_models()
        
        # Extract model IDs
        available_models = [model.get('modelId') for model in response.get('modelSummaries', [])]
        
        # Check which needed models are available
        for model_id in needed_models:
            if model_id in available_models:
                console.print(f"[green]✓ Model {model_id} is available[/green]")
            else:
                console.print(f"[yellow]✗ Model {model_id} is not available[/yellow]")
        
    except Exception as e:
        console.print(f"[bold red]Error checking models: {e}[/bold red]")

def main():
    """Main function to check AWS Bedrock access"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Check AWS Bedrock access with profile support')
    parser.add_argument('--profile', '-p', help='AWS profile name to use')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode to select profile')
    args = parser.parse_args()
    
    profile_name = args.profile
    
    # If interactive mode, let user select a profile
    if args.interactive:
        available_profiles = list_available_profiles()
        if not available_profiles:
            console.print("[yellow]No AWS profiles found. Using default credentials.[/yellow]")
            profile_name = None
        else:
            # Add "default" option (no profile)
            choices = ["default (no profile)"] + available_profiles
            selected = Prompt.ask(
                "[bold blue]Select AWS profile[/bold blue]", 
                choices=choices,
                default="default (no profile)"
            )
            
            if selected == "default (no profile)":
                profile_name = None
            else:
                profile_name = selected
    
    console.print(Panel.fit(
        "[bold green]AWS Bedrock Access Verification Tool[/bold green]\n"
        "[yellow]Check if your AWS credentials can access Bedrock services[/yellow]",
        border_style="blue"
    ))
    
    if profile_name:
        console.print(f"[bold]Using AWS profile: [cyan]{profile_name}[/cyan][/bold]")
    
    # Check AWS credentials
    if not check_aws_credentials(profile_name):
        console.print("\n[bold red]AWS credential check failed. Please fix credential issues before continuing.[/bold red]")
        return
    
    # Check Bedrock regions
    available_regions = check_bedrock_regions(profile_name)
    
    if not available_regions:
        console.print("\n[bold red]No available Bedrock regions found![/bold red]")
        console.print("[yellow]Possible reasons:[/yellow]")
        console.print("1. Your AWS account doesn't have Bedrock enabled")
        console.print("2. Your AWS credentials don't have Bedrock permissions")
        console.print("3. Bedrock isn't available in your account's regions")
        
        # Check if the boto3 version is too old
        try:
            boto3_version = version('boto3')
            MIN_BOTO3_VERSION = "1.28.0"
            if is_version_less_than(boto3_version, MIN_BOTO3_VERSION):
                console.print(f"\n[bold red]Your boto3 version ({boto3_version}) might be too old for Bedrock![/bold red]")
                console.print("[yellow]Bedrock requires boto3 >= 1.28.0. Try upgrading:[/yellow]")
                console.print("pip install --upgrade boto3")
        except PackageNotFoundError:
            pass
        
        return
    
    # For each available region, check runtime access and models
    for region in available_regions:
        check_bedrock_runtime_access(region, profile_name)
        check_bedrock_models(region, profile_name)
        check_specific_models_simple(region, profile_name)
    
    console.print("\n[bold green]Next steps:[/bold green]")
    console.print("1. To update boto3 if needed:")
    console.print("   pip install --upgrade boto3")
    console.print("2. To check your Bedrock model subscriptions, visit:")
    console.print("   https://console.aws.amazon.com/bedrock/home#/modelaccess")

if __name__ == "__main__":
    main()