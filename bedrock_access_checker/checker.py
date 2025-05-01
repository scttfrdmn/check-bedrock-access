"""
AWS Bedrock Access Checker core module

Contains the core functionality for checking AWS Bedrock access.
"""

import boto3
import json
import sys
import os
import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.style import Style
from rich.text import Text
from rich.box import ROUNDED
from rich.align import Align
from rich.layout import Layout
from rich import print as rprint

# Modern imports to replace pkg_resources
try:
    # Python 3.8+
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    # Python < 3.8
    from importlib_metadata import version, PackageNotFoundError

# Initialize Rich console
console = Console()

# Define status constants
STATUS_SUCCESS = "✅ SUCCESS"
STATUS_WARNING = "⚠️ WARNING"
STATUS_ERROR = "❌ ERROR"
STATUS_INFO = "ℹ️ INFO"

# Data structure to store check results
check_results = {
    "aws_credentials": {"status": None, "details": [], "errors": []},
    "bedrock_regions": {"status": None, "available": [], "details": [], "errors": []},
    "bedrock_runtime": {"status": None, "available": [], "details": [], "errors": []},
    "bedrock_models": {"status": None, "available": [], "details": [], "errors": []},
    "key_models": {"status": None, "available": [], "missing": [], "details": [], "errors": []},
}

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
    
    # Reset results for this check
    check_results["aws_credentials"] = {"status": None, "details": [], "errors": []}
    
    # If profile specified, check if it exists
    if profile_name:
        available_profiles = list_available_profiles()
        if profile_name not in available_profiles:
            error_msg = f"Profile '{profile_name}' not found in AWS configuration!"
            console.print(f"[bold red]{error_msg}[/bold red]")
            console.print(f"[yellow]Available profiles: {', '.join(available_profiles) if available_profiles else 'None'}[/yellow]")
            
            check_results["aws_credentials"]["status"] = STATUS_ERROR
            check_results["aws_credentials"]["errors"].append(error_msg)
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
        error_msg = "No AWS credentials found!"
        console.print(f"[bold red]{error_msg}[/bold red]")
        console.print("Please set up your AWS credentials using one of these methods:")
        console.print("1. Run 'aws configure' to create credentials file")
        console.print("2. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables (default profile only)")
        
        check_results["aws_credentials"]["status"] = STATUS_ERROR
        check_results["aws_credentials"]["errors"].append(error_msg)
        return False
    
    # Try creating a session
    try:
        session = boto3.Session(profile_name=profile_name)
        credentials = session.get_credentials()
        
        if credentials is None:
            error_msg = "AWS credentials found but not valid!"
            console.print(f"[bold red]{error_msg}[/bold red]")
            
            check_results["aws_credentials"]["status"] = STATUS_ERROR
            check_results["aws_credentials"]["errors"].append(error_msg)
            return False
            
        # Show credential source (not the actual credentials)
        if profile_name:
            cred_source = f"Profile '{profile_name}'"
        else:
            cred_source = "Environment variables" if has_env_credentials else \
                         "Credentials file (default profile)" if has_file_credentials else \
                         "Unknown source"
        
        success_msg = f"Valid AWS credentials found from: {cred_source}"
        console.print(f"[green]✓ {success_msg}[/green]")
        check_results["aws_credentials"]["details"].append(success_msg)
        
        # Print boto3 version for debugging
        import botocore
        boto3_version = "unknown"
        try:
            boto3_version = version('boto3')
            botocore_version = version('botocore')
            console.print(f"[dim]boto3 version: {boto3_version}[/dim]")
            console.print(f"[dim]botocore version: {botocore_version}[/dim]")
            check_results["aws_credentials"]["details"].append(f"boto3 version: {boto3_version}")
            check_results["aws_credentials"]["details"].append(f"botocore version: {botocore_version}")
            
            # Check if boto3 version might be too old
            MIN_BOTO3_VERSION = "1.28.0"
            if is_version_less_than(boto3_version, MIN_BOTO3_VERSION):
                warning_msg = f"Your boto3 version ({boto3_version}) might be too old for Bedrock! Recommended version is {MIN_BOTO3_VERSION} or newer."
                console.print(f"[yellow]Warning: {warning_msg}[/yellow]")
                check_results["aws_credentials"]["status"] = STATUS_WARNING
                check_results["aws_credentials"]["details"].append(f"WARNING: {warning_msg}")
        except PackageNotFoundError:
            console.print("[dim]Could not determine boto3 version[/dim]")
            check_results["aws_credentials"]["details"].append("Could not determine boto3 version")
        
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
            check_results["aws_credentials"]["details"].append(f"AWS Account: {masked_account}")
            check_results["aws_credentials"]["details"].append(f"Identity Type: {masked_user}")
        except Exception:
            # Don't show error if this fails
            pass
        
        # If we got here and status is still None, set it to SUCCESS
        if check_results["aws_credentials"]["status"] is None:
            check_results["aws_credentials"]["status"] = STATUS_SUCCESS
            
        return True
        
    except Exception as e:
        error_msg = f"Error checking AWS credentials: {e}"
        console.print(f"[bold red]{error_msg}[/bold red]")
        
        check_results["aws_credentials"]["status"] = STATUS_ERROR
        check_results["aws_credentials"]["errors"].append(error_msg)
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
    
    # Reset results for this check
    check_results["bedrock_regions"] = {"status": None, "available": [], "details": [], "errors": []}
    
    # Common regions to check
    regions_to_check = [
        'us-east-1', 
        'us-west-2', 
    ]
    
    # Create a table for results
    table = Table(title="Bedrock Region Availability", box=ROUNDED)
    table.add_column("Region", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Message", style="yellow")
    
    available_regions = []
    region_statuses = {}
    
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
                region_statuses[region] = {"status": "available", "message": "Successfully connected"}
                check_results["bedrock_regions"]["details"].append(f"Region {region}: Available - Successfully connected")
            except Exception as op_error:
                error_msg = str(op_error)
                if "AccessDeniedException" in error_msg:
                    table.add_row(region, "✗ No access", "Permission denied")
                    region_statuses[region] = {"status": "denied", "message": "Permission denied"}
                    check_results["bedrock_regions"]["errors"].append(f"Region {region}: Permission denied")
                elif "not authorized" in error_msg.lower():
                    table.add_row(region, "✗ No access", "Not authorized")
                    region_statuses[region] = {"status": "denied", "message": "Not authorized"}
                    check_results["bedrock_regions"]["errors"].append(f"Region {region}: Not authorized")
                else:
                    table.add_row(region, "✗ Error", error_msg[:50])
                    region_statuses[region] = {"status": "error", "message": error_msg[:50]}
                    check_results["bedrock_regions"]["errors"].append(f"Region {region}: Error - {error_msg}")
                
        except Exception as e:
            error_msg = str(e)
            if "Could not connect to the endpoint URL" in error_msg:
                table.add_row(region, "✗ Not available", "Bedrock not available in this region")
                region_statuses[region] = {"status": "not_available", "message": "Bedrock not available in this region"}
                check_results["bedrock_regions"]["details"].append(f"Region {region}: Not available")
            elif "ResourceNotFoundException" in error_msg:
                table.add_row(region, "✗ Not available", "Bedrock not found in this region")
                region_statuses[region] = {"status": "not_available", "message": "Bedrock not found in this region"}
                check_results["bedrock_regions"]["details"].append(f"Region {region}: Not available - Service not found")
            else:
                table.add_row(region, "✗ Error", error_msg[:50])
                region_statuses[region] = {"status": "error", "message": error_msg[:50]}
                check_results["bedrock_regions"]["errors"].append(f"Region {region}: Error - {error_msg}")
    
    console.print(table)
    
    # Store available regions in results
    check_results["bedrock_regions"]["available"] = available_regions
    
    # Set overall status based on results
    if available_regions:
        check_results["bedrock_regions"]["status"] = STATUS_SUCCESS
    elif any(status["status"] == "denied" for status in region_statuses.values()):
        check_results["bedrock_regions"]["status"] = STATUS_ERROR
    elif all(status["status"] == "not_available" for status in region_statuses.values()):
        check_results["bedrock_regions"]["status"] = STATUS_WARNING
    else:
        check_results["bedrock_regions"]["status"] = STATUS_ERROR
    
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
    
    # Initialize result for this region if not present
    if "bedrock_runtime" not in check_results:
        check_results["bedrock_runtime"] = {"status": None, "available": [], "details": [], "errors": []}
    
    try:
        # Create session with profile if specified
        session = boto3.Session(profile_name=profile_name)
        
        # Create bedrock-runtime client
        client = session.client('bedrock-runtime', region_name=region)
        
        # We can't make a simple call without invoking a model, so we'll just check if the client initializes
        success_msg = f"bedrock-runtime client created successfully in {region}"
        console.print(f"[green]✓ {success_msg}[/green]")
        
        # Update results
        check_results["bedrock_runtime"]["available"].append(region)
        check_results["bedrock_runtime"]["details"].append(success_msg)
        
        # Set status to success if not already set to an error
        if check_results["bedrock_runtime"]["status"] != STATUS_ERROR:
            check_results["bedrock_runtime"]["status"] = STATUS_SUCCESS
            
        return True
    except Exception as e:
        error_msg = f"Error creating bedrock-runtime client in {region}: {e}"
        console.print(f"[bold red]{error_msg}[/bold red]")
        
        # Update results
        check_results["bedrock_runtime"]["errors"].append(error_msg)
        
        # Set status to error if there are no available regions
        if not check_results["bedrock_runtime"]["available"]:
            check_results["bedrock_runtime"]["status"] = STATUS_ERROR
            
        return False

def check_bedrock_models(region, profile_name=None):
    """
    Check which Bedrock models are available in the specified region
    
    Args:
        region (str): AWS region to check
        profile_name (str, optional): AWS profile name to use
    """
    console.print(f"\n[bold]Checking available Bedrock models in {region}...[/bold]")
    
    # Initialize result for this region if not present
    if "bedrock_models" not in check_results:
        check_results["bedrock_models"] = {"status": None, "available": [], "details": [], "errors": []}
    
    try:
        # Create session with profile if specified
        session = boto3.Session(profile_name=profile_name)
        
        # Create Bedrock client
        client = session.client('bedrock', region_name=region)
        
        # List foundation models - without parameters
        response = client.list_foundation_models()
        
        # Create a table for results
        table = Table(title=f"Bedrock Models in {region}", box=ROUNDED)
        table.add_column("Model ID", style="cyan")
        table.add_column("Provider", style="blue")
        table.add_column("Status", style="green")
        
        # Check if any models are returned
        if 'modelSummaries' not in response or not response['modelSummaries']:
            warning_msg = f"No models found in {region}. Your account may not have Bedrock enabled."
            console.print(f"[yellow]{warning_msg}[/yellow]")
            check_results["bedrock_models"]["details"].append(warning_msg)
            
            # Set warning status if no models found but no error occurred
            if check_results["bedrock_models"]["status"] is None:
                check_results["bedrock_models"]["status"] = STATUS_WARNING
                
            return
        
        # Process models
        available_models = []
        for model in response.get('modelSummaries', []):
            model_id = model.get('modelId')
            provider = model.get('providerName', 'Unknown')
            
            # Instead of checking for access, we'll just show if the model is listed
            table.add_row(model_id, provider, "Listed")
            
            # Add to available models
            available_models.append(model_id)
            check_results["bedrock_models"]["available"].append(model_id)
        
        console.print(table)
        
        # Add success message to details
        count_msg = f"Found {len(available_models)} models in {region}"
        check_results["bedrock_models"]["details"].append(count_msg)
        
        # Set success status if models are found and no errors
        if available_models and check_results["bedrock_models"]["status"] is None:
            check_results["bedrock_models"]["status"] = STATUS_SUCCESS
        
    except Exception as e:
        error_msg = f"Error checking Bedrock models in {region}: {e}"
        console.print(f"[bold red]{error_msg}[/bold red]")
        
        # Update results
        check_results["bedrock_models"]["errors"].append(error_msg)
        
        # Set error status if there are errors and no models found
        if not check_results["bedrock_models"]["available"]:
            check_results["bedrock_models"]["status"] = STATUS_ERROR

def check_specific_models_simple(region, profile_name=None):
    """
    Check specific models needed for common Bedrock use cases
    
    Args:
        region (str): AWS region to check
        profile_name (str, optional): AWS profile name to use
    """
    console.print(f"\n[bold]Checking key Bedrock model access in {region}...[/bold]")
    
    # Initialize result for key models if not present
    if "key_models" not in check_results:
        check_results["key_models"] = {"status": None, "available": [], "missing": [], "details": [], "errors": []}
    
    # Create a table for key models
    table = Table(title=f"Key Models in {region}", box=ROUNDED)
    table.add_column("Model", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Purpose", style="blue")
    
    # Define models to check with their purpose
    needed_models = [
        {"id": "amazon.titan-embed-text-v1", "purpose": "Text embeddings (V1)"},
        {"id": "amazon.titan-embed-text-v2:0", "purpose": "Text embeddings (V2)"},
        {"id": "anthropic.claude-3-sonnet-20240229-v1:0", "purpose": "Text generation (Mid-tier)"},
        {"id": "anthropic.claude-3-haiku-20240307-v1:0", "purpose": "Text generation (Fastest)"}
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
        found_models = []
        missing_models = []
        
        for model_info in needed_models:
            model_id = model_info["id"]
            purpose = model_info["purpose"]
            
            if model_id in available_models:
                status_msg = f"Model {model_id} is available"
                console.print(f"[green]✓ {status_msg}[/green]")
                table.add_row(model_id, "✅ Available", purpose)
                found_models.append(model_id)
                
                # Add to available models in results if not already there
                if model_id not in check_results["key_models"]["available"]:
                    check_results["key_models"]["available"].append(model_id)
                
                check_results["key_models"]["details"].append(f"{model_id}: Available")
            else:
                status_msg = f"Model {model_id} is not available"
                console.print(f"[yellow]✗ {status_msg}[/yellow]")
                table.add_row(model_id, "❌ Not Available", purpose)
                missing_models.append(model_id)
                
                # Add to missing models in results if not already there
                if model_id not in check_results["key_models"]["missing"]:
                    check_results["key_models"]["missing"].append(model_id)
                
                check_results["key_models"]["details"].append(f"{model_id}: Not Available")
        
        console.print(table)
        
        # Set status based on results
        if found_models:
            if missing_models:
                check_results["key_models"]["status"] = STATUS_WARNING
            else:
                check_results["key_models"]["status"] = STATUS_SUCCESS
        else:
            check_results["key_models"]["status"] = STATUS_ERROR
        
    except Exception as e:
        error_msg = f"Error checking key models in {region}: {e}"
        console.print(f"[bold red]{error_msg}[/bold red]")
        
        # Update results
        check_results["key_models"]["errors"].append(error_msg)
        
        # Set error status if there are errors and no available models
        if not check_results["key_models"]["available"]:
            check_results["key_models"]["status"] = STATUS_ERROR

def display_summary_dashboard():
    """Display a summary dashboard with status of all checks"""
    console.print("\n")
    
    # Create the overall panel
    panel = Panel(
        Align.center("[bold blue]AWS Bedrock Access Verification Summary[/bold blue]", vertical="middle"),
        box=ROUNDED,
        padding=(1, 2),
        title="[bold]Status Dashboard[/bold]",
        border_style="blue"
    )
    console.print(panel)
    
    # Create the summary table
    table = Table(box=ROUNDED, expand=True, padding=(0, 1))
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold", justify="center")
    table.add_column("Details", style="green")
    
    # Add rows for each component
    # AWS Credentials
    cred_status = check_results["aws_credentials"]["status"] or STATUS_INFO
    cred_style = "green" if cred_status == STATUS_SUCCESS else "yellow" if cred_status == STATUS_WARNING else "red"
    cred_details = ""
    if check_results["aws_credentials"]["details"]:
        cred_details = check_results["aws_credentials"]["details"][0]
    elif check_results["aws_credentials"]["errors"]:
        cred_details = check_results["aws_credentials"]["errors"][0]
    table.add_row("AWS Credentials", f"[{cred_style}]{cred_status}[/{cred_style}]", cred_details)
    
    # Bedrock Regions
    region_status = check_results["bedrock_regions"]["status"] or STATUS_INFO
    region_style = "green" if region_status == STATUS_SUCCESS else "yellow" if region_status == STATUS_WARNING else "red"
    region_count = len(check_results["bedrock_regions"]["available"])
    region_details = f"{region_count} available regions"
    if region_count > 0:
        region_details += f": {', '.join(check_results['bedrock_regions']['available'])}"
    elif check_results["bedrock_regions"]["errors"]:
        region_details = check_results["bedrock_regions"]["errors"][0]
    table.add_row("Bedrock Regions", f"[{region_style}]{region_status}[/{region_style}]", region_details)
    
    # Bedrock Runtime
    runtime_status = check_results["bedrock_runtime"]["status"] or STATUS_INFO
    runtime_style = "green" if runtime_status == STATUS_SUCCESS else "yellow" if runtime_status == STATUS_WARNING else "red"
    runtime_details = "Runtime service accessible"
    if check_results["bedrock_runtime"]["errors"]:
        runtime_details = check_results["bedrock_runtime"]["errors"][0]
    table.add_row("Bedrock Runtime", f"[{runtime_style}]{runtime_status}[/{runtime_style}]", runtime_details)
    
    # Bedrock Models
    models_status = check_results["bedrock_models"]["status"] or STATUS_INFO
    models_style = "green" if models_status == STATUS_SUCCESS else "yellow" if models_status == STATUS_WARNING else "red"
    models_count = len(set(check_results["bedrock_models"]["available"]))  # Use set to avoid duplicates
    models_details = f"{models_count} models available"
    if models_count == 0 and check_results["bedrock_models"]["errors"]:
        models_details = check_results["bedrock_models"]["errors"][0]
    table.add_row("Bedrock Models", f"[{models_style}]{models_status}[/{models_style}]", models_details)
    
    # Key Models
    key_status = check_results["key_models"]["status"] or STATUS_INFO
    key_style = "green" if key_status == STATUS_SUCCESS else "yellow" if key_status == STATUS_WARNING else "red"
    available_count = len(check_results["key_models"]["available"])
    missing_count = len(check_results["key_models"]["missing"])
    total_count = available_count + missing_count
    key_details = f"{available_count}/{total_count} key models available"
    if missing_count > 0 and available_count > 0:
        key_details += " (partial access)"
    elif missing_count == total_count:
        key_details += " (no key models available)"
    table.add_row("Key Models", f"[{key_style}]{key_status}[/{key_style}]", key_details)
    
    console.print(table)
    
    # Overall status
    all_statuses = [
        check_results["aws_credentials"]["status"],
        check_results["bedrock_regions"]["status"],
        check_results["bedrock_runtime"]["status"],
        check_results["bedrock_models"]["status"],
        check_results["key_models"]["status"]
    ]
    
    if STATUS_ERROR in all_statuses:
        overall_status = STATUS_ERROR
        overall_style = "red"
        overall_message = "There are critical issues with your Bedrock setup"
    elif STATUS_WARNING in all_statuses:
        overall_status = STATUS_WARNING
        overall_style = "yellow"
        overall_message = "Your Bedrock setup has some issues but may work for some use cases"
    elif all(status == STATUS_SUCCESS for status in all_statuses if status is not None):
        overall_status = STATUS_SUCCESS
        overall_style = "green"
        overall_message = "Your Bedrock setup looks good!"
    else:
        overall_status = STATUS_INFO
        overall_style = "blue"
        overall_message = "Some checks were inconclusive"
    
    # Print overall status
    console.print(f"\n[bold {overall_style}]Overall Status: {overall_status}[/bold {overall_style}]")
    console.print(f"[{overall_style}]{overall_message}[/{overall_style}]")
    
    # Print timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"\n[dim]Check completed at: {timestamp}[/dim]")
    
    # Print troubleshooting tips based on status
    if overall_status != STATUS_SUCCESS:
        console.print("\n[bold yellow]Troubleshooting Tips:[/bold yellow]")
        
        # AWS Credentials issues
        if check_results["aws_credentials"]["status"] in [STATUS_ERROR, STATUS_WARNING]:
            console.print("[yellow]• AWS Credentials:[/yellow]")
            console.print("  - Run 'aws configure' to set up credentials")
            console.print("  - Verify your credentials have Bedrock permissions")
            console.print("  - Check if boto3 version is at least 1.28.0")
        
        # Bedrock Regions issues
        if check_results["bedrock_regions"]["status"] in [STATUS_ERROR, STATUS_WARNING]:
            console.print("[yellow]• Bedrock Regions:[/yellow]")
            console.print("  - Make sure Bedrock is enabled in your AWS account")
            console.print("  - Check if your IAM permissions include bedrock:ListFoundationModels")
            console.print("  - Verify you're checking regions where Bedrock is available")
        
        # Bedrock Runtime issues
        if check_results["bedrock_runtime"]["status"] in [STATUS_ERROR, STATUS_WARNING]:
            console.print("[yellow]• Bedrock Runtime:[/yellow]")
            console.print("  - Verify your IAM permissions include bedrock-runtime:* actions")
            console.print("  - Check if the Bedrock service endpoint is accessible from your network")
        
        # Model access issues
        if check_results["key_models"]["status"] in [STATUS_ERROR, STATUS_WARNING]:
            console.print("[yellow]• Model Access:[/yellow]")
            console.print("  - Visit AWS console to request access to needed models:")
            console.print("    https://console.aws.amazon.com/bedrock/home#/modelaccess")
            console.print("  - For Claude models, make sure you've accepted Anthropic's terms of service")
            console.print("  - Some models require explicit subscription - check your model access")
    
    # Print next steps
    console.print("\n[bold green]Next Steps:[/bold green]")
    if overall_status == STATUS_SUCCESS:
        console.print("✓ Your setup looks good! You can start using Bedrock services")
        console.print("✓ For usage examples, visit: https://docs.aws.amazon.com/bedrock/latest/userguide/")
    else:
        console.print("1. Address the issues highlighted above")
        console.print("2. Run this tool again to verify your changes")
        console.print("3. Refer to AWS Bedrock documentation for specific IAM policies and setup instructions")
    
    # Print boto3 upgrade reminder if necessary
    try:
        boto3_version = version('boto3')
        MIN_BOTO3_VERSION = "1.28.0"
        if is_version_less_than(boto3_version, MIN_BOTO3_VERSION):
            console.print("\n[yellow]Remember to upgrade boto3:[/yellow]")
            console.print("   pip install --upgrade boto3")
    except PackageNotFoundError:
        pass

def output_results(format_type):
    """
    Output results in the specified format
    
    Args:
        format_type (str): 'json' or 'csv'
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format_type == 'json':
        filename = f"bedrock_check_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(check_results, f, indent=2)
        console.print(f"\n[green]Results saved to {filename}[/green]")
    
    elif format_type == 'csv':
        filename = f"bedrock_check_{timestamp}.csv"
        with open(filename, 'w') as f:
            f.write("Component,Status,Details\n")
            
            # AWS Credentials
            cred_details = ""
            if check_results["aws_credentials"]["details"]:
                cred_details = check_results["aws_credentials"]["details"][0].replace(',', ';')
            f.write(f"AWS Credentials,{check_results['aws_credentials']['status']},{cred_details}\n")
            
            # Bedrock Regions
            regions = ';'.join(check_results["bedrock_regions"]["available"])
            f.write(f"Bedrock Regions,{check_results['bedrock_regions']['status']},{regions}\n")
            
            # Bedrock Runtime
            runtime_details = "Runtime service accessible"
            if check_results["bedrock_runtime"]["errors"]:
                runtime_details = check_results["bedrock_runtime"]["errors"][0].replace(',', ';')
            f.write(f"Bedrock Runtime,{check_results['bedrock_runtime']['status']},{runtime_details}\n")
            
            # Bedrock Models
            models_count = len(set(check_results["bedrock_models"]["available"]))
            f.write(f"Bedrock Models,{check_results['bedrock_models']['status']},{models_count} models available\n")
            
            # Key Models
            available_count = len(check_results["key_models"]["available"])
            missing_count = len(check_results["key_models"]["missing"])
            total_count = available_count + missing_count
            key_details = f"{available_count}/{total_count} key models available"
            f.write(f"Key Models,{check_results['key_models']['status']},{key_details}\n")
            
        console.print(f"\n[green]Results saved to {filename}[/green]")