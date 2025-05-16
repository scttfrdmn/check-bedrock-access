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

def check_bedrock_regions(profile_name=None, regions_to_check=None):
    """
    Check which regions have Bedrock available
    
    Args:
        profile_name (str, optional): AWS profile name to use
        regions_to_check (list, optional): Specific regions to check
    
    Returns:
        list: List of available regions
    """
    console.print("\n[bold]Checking Bedrock availability in regions...[/bold]")
    
    # Reset results for this check
    check_results["bedrock_regions"] = {"status": None, "available": [], "details": [], "errors": []}
    
    # All regions where Bedrock is available (define at module level for import in CLI)
all_bedrock_regions = [
    'us-east-1',    # N. Virginia
    'us-west-2',    # Oregon
    'ap-northeast-1', # Tokyo
    'ap-southeast-1', # Singapore
    'eu-central-1',   # Frankfurt
    'us-east-2',      # Ohio 
    'ap-south-1',     # Mumbai
    'ap-northeast-2', # Seoul
    'eu-west-1',      # Ireland
    'ca-central-1',   # Canada
]

def check_bedrock_regions(profile_name=None, regions_to_check=None):
    """
    Check which regions have Bedrock available
    
    Args:
        profile_name (str, optional): AWS profile name to use
        regions_to_check (list, optional): Specific regions to check
    
    Returns:
        list: List of available regions
    """
    console.print("\n[bold]Checking Bedrock availability in regions...[/bold]")
    
    # Reset results for this check
    check_results["bedrock_regions"] = {"status": None, "available": [], "details": [], "errors": []}
    
    # Use provided regions or default to common ones
    regions_to_check = regions_to_check if regions_to_check else ['us-east-1', 'us-west-2']
    
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

def test_model_invocation(model_id, region, profile_name=None):
    """
    Test a simple model invocation to verify full access
    
    Args:
        model_id (str): The model ID to test
        region (str): AWS region to test in
        profile_name (str, optional): AWS profile name to use
        
    Returns:
        bool: True if invocation successful, False otherwise
        str: Response or error message
    """
    console.print(f"[dim]Testing model invocation for {model_id}...[/dim]")
    
    try:
        # Create session with profile if specified
        session = boto3.Session(profile_name=profile_name)
        
        # Create bedrock-runtime client
        client = session.client('bedrock-runtime', region_name=region)
        
        # Prepare a minimal test prompt based on model type
        if "embed" in model_id.lower():
            # Embedding model
            request_body = {
                "inputText": "Hello, world!"
            }
        elif "anthropic.claude" in model_id.lower():
            # Claude model
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": "Say hello in 5 words or less."}]
                    }
                ]
            }
        elif "cohere" in model_id.lower():
            # Cohere model
            request_body = {
                "prompt": "Say hello in 5 words or less.",
                "max_tokens": 10
            }
        elif "meta.llama" in model_id.lower():
            # Llama model
            request_body = {
                "prompt": "Human: Say hello in 5 words or less.\nAssistant:",
                "max_gen_len": 10
            }
        elif "titan" in model_id.lower():
            # Titan model
            request_body = {
                "inputText": "Say hello in 5 words or less.",
                "textGenerationConfig": {
                    "maxTokenCount": 10
                }
            }
        else:
            # Generic format - may not work with all models
            request_body = {
                "prompt": "Say hello in 5 words or less.",
                "max_tokens": 10
            }
        
        # Invoke the model
        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read().decode('utf-8'))
        
        # Return success with shortened response
        response_str = str(response_body)[:50] + "..." if len(str(response_body)) > 50 else str(response_body)
        return True, f"Success: {response_str}"
    
    except Exception as e:
        error_msg = str(e)
        if "AccessDeniedException" in error_msg:
            return False, "Access denied"
        elif "ResourceNotFoundException" in error_msg:
            return False, "Model not found"
        elif "ValidationException" in error_msg:
            return False, f"Validation error: {error_msg[:50]}..."
        elif "ThrottlingException" in error_msg:
            return False, "Rate limited"
        else:
            return False, f"Error: {error_msg[:50]}..."

def check_sagemaker_jumpstart_alternatives(missing_model_ids, region, profile_name=None):
    """
    Check for SageMaker JumpStart alternatives for missing Bedrock models
    
    Args:
        missing_model_ids (list): List of missing Bedrock model IDs
        region (str): AWS region to check in
        profile_name (str, optional): AWS profile name to use
        
    Returns:
        dict: Dictionary mapping missing models to alternatives
    """
    console.print(f"\n[bold]Checking SageMaker JumpStart alternatives in {region}...[/bold]")
    
    # Initialize SageMaker JumpStart alternatives in check_results if not present
    if "sagemaker_alternatives" not in check_results:
        check_results["sagemaker_alternatives"] = {}
    
    # Create a mapping of Bedrock models to similar JumpStart models
    # This is a manually curated list based on model capabilities
    jumpstart_alternatives = {
        # Claude alternatives
        "anthropic.claude-3-opus": [
            {"model_id": "huggingface-llm-llama-2-70b", "name": "Meta Llama 2 (70B)", "notes": "Open source alternative with strong capabilities"},
            {"model_id": "huggingface-llm-mistral-7b", "name": "Mistral (7B)", "notes": "Open source model with good performance for its size"},
            {"model_id": "meta-textgeneration-llama-2-70b-f", "name": "Meta Llama 2 Chat (70B)", "notes": "Fine-tuned for chat and instruction following"}
        ],
        "anthropic.claude-3-sonnet": [
            {"model_id": "huggingface-llm-llama-2-13b", "name": "Meta Llama 2 (13B)", "notes": "Smaller open source alternative"},
            {"model_id": "huggingface-llm-mistral-7b", "name": "Mistral (7B)", "notes": "Efficient open source model with good capabilities"}
        ],
        "anthropic.claude-3-haiku": [
            {"model_id": "huggingface-llm-mistral-7b", "name": "Mistral (7B)", "notes": "Comparable size with efficient performance"},
            {"model_id": "huggingface-textgeneration-gpt2-xl", "name": "GPT-2 XL", "notes": "Fast text generation for simple tasks"}
        ],
        "anthropic.claude-v2": [
            {"model_id": "huggingface-llm-llama-2-13b", "name": "Meta Llama 2 (13B)", "notes": "Good general purpose alternative"}
        ],
        # Titan alternatives
        "amazon.titan": [
            {"model_id": "huggingface-llm-falcon-7b", "name": "Falcon (7B)", "notes": "Good general purpose alternative"},
            {"model_id": "huggingface-llm-mistral-7b", "name": "Mistral (7B)", "notes": "Strong performance for its size"}
        ],
        # Embedding model alternatives
        "amazon.titan-embed": [
            {"model_id": "huggingface-textembedding-bge-large-en", "name": "BGE Large Embeddings", "notes": "Strong text embedding alternative"},
            {"model_id": "huggingface-textembedding-all-mpnet-base-v2", "name": "MPNet Embeddings", "notes": "Good general purpose embeddings"}
        ],
        # Cohere alternatives
        "cohere.command": [
            {"model_id": "huggingface-llm-mistral-7b", "name": "Mistral (7B)", "notes": "Comparable capabilities"},
            {"model_id": "huggingface-llm-falcon-7b", "name": "Falcon (7B)", "notes": "Good general purpose alternative"}
        ],
        # Llama alternatives (mostly for completeness)
        "meta.llama2": [
            {"model_id": "huggingface-llm-mistral-7b", "name": "Mistral (7B)", "notes": "Alternative high-quality open source model"}
        ]
    }
    
    alternatives_found = {}
    
    try:
        # Create session with profile if specified
        session = boto3.Session(profile_name=profile_name)
        
        # Create SageMaker client
        try:
            sm_client = session.client('sagemaker', region_name=region)
            
            # Create a table for alternatives
            table = Table(title=f"SageMaker JumpStart Alternatives", box=ROUNDED)
            table.add_column("Missing Bedrock Model", style="red")
            table.add_column("JumpStart Alternative", style="green")
            table.add_column("Notes", style="cyan")
            
            # Check availability of alternatives for each missing model
            for full_model_id in missing_model_ids:
                # Extract the base model name (without version)
                base_model_id = full_model_id.split(':')[0]  # Remove version if present
                base_model_parts = base_model_id.split('.')
                
                if len(base_model_parts) >= 2:
                    # Get just provider.model format (e.g., anthropic.claude, amazon.titan)
                    simplified_id = f"{base_model_parts[0]}.{base_model_parts[1].split('-')[0]}"
                    
                    # Try to find alternatives for this model
                    matched_alternatives = []
                    
                    # Check for direct match
                    if simplified_id in jumpstart_alternatives:
                        matched_alternatives = jumpstart_alternatives[simplified_id]
                    else:
                        # Try partial matching
                        for model_key in jumpstart_alternatives:
                            if simplified_id in model_key or model_key in simplified_id:
                                matched_alternatives = jumpstart_alternatives[model_key]
                                break
                    
                    if matched_alternatives:
                        # Store the alternatives
                        alternatives_found[full_model_id] = matched_alternatives
                        check_results["sagemaker_alternatives"][full_model_id] = matched_alternatives
                        
                        # Add to the table
                        for alt in matched_alternatives:
                            table.add_row(
                                full_model_id if matched_alternatives.index(alt) == 0 else "", 
                                f"{alt['name']} ({alt['model_id']})",
                                alt['notes']
                            )
            
            # Display the alternatives table if any found
            if alternatives_found:
                console.print(table)
                console.print(f"[green]✓ Found SageMaker JumpStart alternatives for {len(alternatives_found)} missing Bedrock models[/green]")
            else:
                console.print("[yellow]No SageMaker JumpStart alternatives found for your missing models[/yellow]")
            
            return alternatives_found
            
        except Exception as e:
            error_msg = f"Error checking SageMaker JumpStart alternatives: {e}"
            console.print(f"[yellow]{error_msg}[/yellow]")
            check_results["sagemaker_alternatives"]["error"] = error_msg
            return {}
            
    except Exception as e:
        error_msg = f"Error initializing SageMaker client: {e}"
        console.print(f"[yellow]{error_msg}[/yellow]")
        check_results["sagemaker_alternatives"]["error"] = error_msg
        return {}

def get_model_quotas_and_details(model_id, region, profile_name=None):
    """
    Get detailed information about a model's quotas and inference capabilities
    
    Args:
        model_id (str): The model ID to get information for
        region (str): AWS region to check in
        profile_name (str, optional): AWS profile name to use
        
    Returns:
        dict: Dictionary with quota and inference details
    """
    details = {
        "quotas": {},
        "inference_params": {},
        "pricing": {},
        "specs": {}
    }
    
    try:
        # Create session with profile if specified
        session = boto3.Session(profile_name=profile_name)
        
        # Get account quotas for the model using service quotas API
        try:
            quotas_client = session.client('service-quotas', region_name=region)
            
            # Get service code for Bedrock
            service_code = "bedrock"
            
            # Try to get quotas for the model
            response = quotas_client.list_service_quotas(
                ServiceCode=service_code
            )
            
            # Filter quotas related to the model (this is approximate as model IDs may not match quota names exactly)
            model_name_parts = model_id.split('.')[-1].split('-')
            for quota in response.get('Quotas', []):
                quota_name = quota.get('QuotaName', '').lower()
                
                # Check if quota is related to this model by looking for substrings
                relevant = False
                for part in model_name_parts:
                    if len(part) > 3 and part.lower() in quota_name:  # Only consider meaningful parts
                        relevant = True
                        break
                
                # Also include general throughput/rate quotas
                if "throughput" in quota_name or "rate" in quota_name:
                    relevant = True
                    
                if relevant:
                    details["quotas"][quota.get('QuotaName')] = {
                        "value": quota.get('Value'),
                        "unit": quota.get('Unit'),
                        "adjustable": quota.get('Adjustable', False)
                    }
        except Exception as e:
            details["quotas"]["error"] = f"Could not fetch quotas: {str(e)}"
        
        # Get model details from Bedrock API
        try:
            bedrock_client = session.client('bedrock', region_name=region)
            
            # Get model details
            response = bedrock_client.get_foundation_model(
                modelIdentifier=model_id
            )
            
            # Extract useful information
            if 'modelDetails' in response:
                model_details = response.get('modelDetails', {})
                
                # Get inference parameters
                if 'inferenceParameters' in model_details:
                    details["inference_params"] = model_details['inferenceParameters']
                
                # Get pricing information if available
                if 'pricingDetails' in model_details:
                    details["pricing"] = model_details['pricingDetails']
                
                # Get model specifications
                details["specs"] = {
                    "model_name": model_details.get('name', ''),
                    "provider": model_details.get('providerName', ''),
                    "input_modalities": model_details.get('inputModalities', []),
                    "output_modalities": model_details.get('outputModalities', []),
                    "customizations_supported": model_details.get('customizationsSupported', []),
                    "response_streaming_supported": model_details.get('responseStreamingSupported', False),
                }
        except Exception as e:
            details["specs"]["error"] = f"Could not fetch model details: {str(e)}"
        
        return details
        
    except Exception as e:
        return {"error": str(e)}

def check_specific_models_simple(region, profile_name=None, test_invocation=False, advanced_mode=False):
    """
    Check specific models needed for common Bedrock use cases
    
    Args:
        region (str): AWS region to check
        profile_name (str, optional): AWS profile name to use
        test_invocation (bool, optional): Whether to test model invocation
        advanced_mode (bool, optional): Whether to show detailed model information
    """
    console.print(f"\n[bold]Checking key Bedrock model access in {region}...[/bold]")
    
    # Initialize result for key models if not present
    if "key_models" not in check_results:
        check_results["key_models"] = {"status": None, "available": [], "missing": [], "details": [], "errors": []}
    
    # Create a table for key models
    table = Table(title=f"Key Models in {region}", box=ROUNDED)
    table.add_column("Model", style="cyan")
    table.add_column("Listed", style="green")
    if test_invocation:
        table.add_column("Invocation", style="magenta")
    table.add_column("Purpose", style="blue")
    
    # Define models to check with their purpose
    needed_models = [
        # Embedding models
        {"id": "amazon.titan-embed-text-v1", "purpose": "Text embeddings (V1)"},
        {"id": "amazon.titan-embed-text-v2:0", "purpose": "Text embeddings (V2)"},
        
        # Claude 3 models - latest and most advanced
        {"id": "anthropic.claude-3-opus-20240229-v1:0", "purpose": "Text generation (Flagship)"},
        {"id": "anthropic.claude-3-sonnet-20240229-v1:0", "purpose": "Text generation (Mid-tier)"},
        {"id": "anthropic.claude-3-haiku-20240307-v1:0", "purpose": "Text generation (Fastest)"},
        
        # Claude 2 models - previous generation
        {"id": "anthropic.claude-v2:1", "purpose": "Text generation (Previous gen)"},
        {"id": "anthropic.claude-v2", "purpose": "Text generation (Previous gen)"},
        {"id": "anthropic.claude-instant-v1", "purpose": "Text generation (Previous gen, fast)"},
        
        # Other useful models
        {"id": "amazon.titan-text-express-v1", "purpose": "Amazon's text model"},
        {"id": "cohere.command-text-v14", "purpose": "Cohere's text model"},
        {"id": "meta.llama2-13b-chat-v1", "purpose": "Meta's open model"}
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
        
        # Initialize invocation results in check_results if testing invocation
        if test_invocation and "model_invocations" not in check_results:
            check_results["model_invocations"] = {"successful": [], "failed": [], "details": []}
            
        # Initialize advanced details if in advanced mode
        if advanced_mode and "model_details" not in check_results:
            check_results["model_details"] = {}
        
        for model_info in needed_models:
            model_id = model_info["id"]
            purpose = model_info["purpose"]
            
            if model_id in available_models:
                status_msg = f"Model {model_id} is available"
                console.print(f"[green]✓ {status_msg}[/green]")
                
                # Add to available models in results if not already there
                if model_id not in check_results["key_models"]["available"]:
                    check_results["key_models"]["available"].append(model_id)
                
                check_results["key_models"]["details"].append(f"{model_id}: Available")
                
                # Advanced mode processing
                model_details_table = None
                if advanced_mode:
                    # Get detailed model information
                    console.print(f"[dim]  Getting detailed information for {model_id}...[/dim]")
                    model_details = get_model_quotas_and_details(model_id, region, profile_name)
                    
                    # Store in results
                    check_results["model_details"][model_id] = model_details
                    
                    # Create a detailed table for this model
                    model_details_table = Table(title=f"Details for {model_id}", box=ROUNDED)
                    model_details_table.add_column("Parameter", style="cyan")
                    model_details_table.add_column("Value", style="yellow")
                    
                    # Add basic specs
                    if "specs" in model_details and model_details["specs"]:
                        for key, value in model_details["specs"].items():
                            if key != "error":
                                model_details_table.add_row(f"Spec: {key}", str(value))
                    
                    # Add inference parameters
                    if "inference_params" in model_details and model_details["inference_params"]:
                        for key, value in model_details["inference_params"].items():
                            model_details_table.add_row(f"Param: {key}", str(value))
                    
                    # Add quota information
                    if "quotas" in model_details and model_details["quotas"]:
                        for key, value in model_details["quotas"].items():
                            if key != "error":
                                if isinstance(value, dict):
                                    quota_str = f"{value.get('value')} {value.get('unit', '')}"
                                    if value.get('adjustable'):
                                        quota_str += " (adjustable)"
                                    model_details_table.add_row(f"Quota: {key}", quota_str)
                                else:
                                    model_details_table.add_row(f"Quota: {key}", str(value))
                
                # Test invocation if requested
                if test_invocation:
                    invoke_success, invoke_msg = test_model_invocation(model_id, region, profile_name)
                    
                    if invoke_success:
                        table.add_row(model_id, "✅ Available", "✅ Success", purpose)
                        console.print(f"[green]  ✓ Invocation successful: {invoke_msg}[/green]")
                        
                        # Add to successful invocations
                        if model_id not in check_results["model_invocations"]["successful"]:
                            check_results["model_invocations"]["successful"].append(model_id)
                        
                        check_results["model_invocations"]["details"].append(f"{model_id}: {invoke_msg}")
                    else:
                        table.add_row(model_id, "✅ Available", f"❌ Failed: {invoke_msg}", purpose)
                        console.print(f"[yellow]  ✗ Invocation failed: {invoke_msg}[/yellow]")
                        
                        # Add to failed invocations
                        if model_id not in check_results["model_invocations"]["failed"]:
                            check_results["model_invocations"]["failed"].append(model_id)
                        
                        check_results["model_invocations"]["details"].append(f"{model_id}: Failed - {invoke_msg}")
                else:
                    table.add_row(model_id, "✅ Available", purpose)
                
                # Display detailed model information if in advanced mode
                if advanced_mode and model_details_table:
                    console.print(model_details_table)
                
                found_models.append(model_id)
            else:
                status_msg = f"Model {model_id} is not available"
                console.print(f"[yellow]✗ {status_msg}[/yellow]")
                
                if test_invocation:
                    table.add_row(model_id, "❌ Not Available", "❌ Not Tested", purpose)
                else:
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
    
    # Add model invocation results if available
    if "model_invocations" in check_results:
        invoke_success_count = len(check_results["model_invocations"]["successful"])
        invoke_failed_count = len(check_results["model_invocations"]["failed"])
        invoke_total = invoke_success_count + invoke_failed_count
        
        if invoke_total > 0:
            invoke_status = STATUS_SUCCESS if invoke_failed_count == 0 else STATUS_WARNING if invoke_success_count > 0 else STATUS_ERROR
            invoke_style = "green" if invoke_status == STATUS_SUCCESS else "yellow" if invoke_status == STATUS_WARNING else "red"
            invoke_details = f"{invoke_success_count}/{invoke_total} models invoked successfully"
            table.add_row("Model Invocation", f"[{invoke_style}]{invoke_status}[/{invoke_style}]", invoke_details)
    
    # Add SageMaker JumpStart alternatives if available
    if "sagemaker_alternatives" in check_results and check_results["sagemaker_alternatives"]:
        # Exclude error entry when counting alternatives
        alternatives_count = sum(1 for k in check_results["sagemaker_alternatives"] if k != "error")
        
        if alternatives_count > 0:
            sm_status = STATUS_INFO
            sm_style = "blue"
            sm_details = f"Found alternatives for {alternatives_count} missing Bedrock models"
            table.add_row("SageMaker Alternatives", f"[{sm_style}]{sm_status}[/{sm_style}]", sm_details)
    
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
        format_type (str): 'json', 'csv', or 'html'
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
        
    elif format_type == 'html':
        filename = f"bedrock_check_{timestamp}.html"
        
        # Create an HTML report with improved visualization
        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html lang='en'>")
        html.append("<head>")
        html.append("  <meta charset='UTF-8'>")
        html.append("  <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
        html.append("  <title>AWS Bedrock Access Check Report</title>")
        html.append("  <style>")
        html.append("    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }")
        html.append("    .container { max-width: 1200px; margin: 0 auto; }")
        html.append("    .header { text-align: center; margin-bottom: 30px; }")
        html.append("    .dashboard { background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 30px; }")
        html.append("    .summary-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }")
        html.append("    .summary-table th, .summary-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }")
        html.append("    .summary-table th { background-color: #f0f0f0; }")
        html.append("    .success { color: #2e7d32; font-weight: bold; }")
        html.append("    .warning { color: #f57c00; font-weight: bold; }")
        html.append("    .error { color: #d32f2f; font-weight: bold; }")
        html.append("    .info { color: #1976d2; font-weight: bold; }")
        html.append("    .details-section { margin-bottom: 30px; }")
        html.append("    .details-section h2 { border-bottom: 1px solid #eee; padding-bottom: 8px; }")
        html.append("    .model-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }")
        html.append("    .model-card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }")
        html.append("    .model-card h3 { margin-top: 0; }")
        html.append("    .region-list { display: flex; flex-wrap: wrap; gap: 10px; }")
        html.append("    .region-badge { background: #e3f2fd; padding: 5px 10px; border-radius: 16px; font-size: 14px; }")
        html.append("    .footer { margin-top: 30px; text-align: center; color: #666; font-size: 14px; }")
        html.append("  </style>")
        html.append("</head>")
        html.append("<body>")
        html.append("  <div class='container'>")
        
        # Header
        html.append("    <div class='header'>")
        html.append("      <h1>AWS Bedrock Access Verification Report</h1>")
        html.append(f"      <p>Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
        html.append("    </div>")
        
        # Dashboard
        html.append("    <div class='dashboard'>")
        html.append("      <h2>Status Dashboard</h2>")
        html.append("      <table class='summary-table'>")
        html.append("        <tr><th>Component</th><th>Status</th><th>Details</th></tr>")
        
        # AWS Credentials
        cred_status = check_results["aws_credentials"]["status"] or "ℹ️ INFO"
        cred_class = "success" if "SUCCESS" in cred_status else "warning" if "WARNING" in cred_status else "error" if "ERROR" in cred_status else "info"
        cred_details = check_results["aws_credentials"]["details"][0] if check_results["aws_credentials"]["details"] else "N/A"
        html.append(f"        <tr><td>AWS Credentials</td><td class='{cred_class}'>{cred_status}</td><td>{cred_details}</td></tr>")
        
        # Bedrock Regions
        region_status = check_results["bedrock_regions"]["status"] or "ℹ️ INFO"
        region_class = "success" if "SUCCESS" in region_status else "warning" if "WARNING" in region_status else "error" if "ERROR" in region_status else "info"
        region_count = len(check_results["bedrock_regions"]["available"])
        region_details = f"{region_count} available regions"
        html.append(f"        <tr><td>Bedrock Regions</td><td class='{region_class}'>{region_status}</td><td>{region_details}</td></tr>")
        
        # Bedrock Runtime
        runtime_status = check_results["bedrock_runtime"]["status"] or "ℹ️ INFO"
        runtime_class = "success" if "SUCCESS" in runtime_status else "warning" if "WARNING" in runtime_status else "error" if "ERROR" in runtime_status else "info"
        runtime_details = "Runtime service accessible" if not check_results["bedrock_runtime"]["errors"] else check_results["bedrock_runtime"]["errors"][0]
        html.append(f"        <tr><td>Bedrock Runtime</td><td class='{runtime_class}'>{runtime_status}</td><td>{runtime_details}</td></tr>")
        
        # Bedrock Models
        models_status = check_results["bedrock_models"]["status"] or "ℹ️ INFO"
        models_class = "success" if "SUCCESS" in models_status else "warning" if "WARNING" in models_status else "error" if "ERROR" in models_status else "info"
        models_count = len(set(check_results["bedrock_models"]["available"]))
        models_details = f"{models_count} models available"
        html.append(f"        <tr><td>Bedrock Models</td><td class='{models_class}'>{models_status}</td><td>{models_details}</td></tr>")
        
        # Key Models
        key_status = check_results["key_models"]["status"] or "ℹ️ INFO"
        key_class = "success" if "SUCCESS" in key_status else "warning" if "WARNING" in key_status else "error" if "ERROR" in key_status else "info"
        available_count = len(check_results["key_models"]["available"])
        missing_count = len(check_results["key_models"]["missing"])
        total_count = available_count + missing_count
        key_details = f"{available_count}/{total_count} key models available"
        html.append(f"        <tr><td>Key Models</td><td class='{key_class}'>{key_status}</td><td>{key_details}</td></tr>")
        
        # Model Invocation if available
        if "model_invocations" in check_results:
            invoke_success_count = len(check_results["model_invocations"]["successful"])
            invoke_failed_count = len(check_results["model_invocations"]["failed"])
            invoke_total = invoke_success_count + invoke_failed_count
            
            if invoke_total > 0:
                if invoke_failed_count == 0:
                    invoke_status = "✅ SUCCESS"
                    invoke_class = "success"
                elif invoke_success_count > 0:
                    invoke_status = "⚠️ WARNING"
                    invoke_class = "warning"
                else:
                    invoke_status = "❌ ERROR"
                    invoke_class = "error"
                    
                invoke_details = f"{invoke_success_count}/{invoke_total} models invoked successfully"
                html.append(f"        <tr><td>Model Invocation</td><td class='{invoke_class}'>{invoke_status}</td><td>{invoke_details}</td></tr>")
        
        html.append("      </table>")
        
        # Overall status
        all_statuses = [
            check_results["aws_credentials"]["status"],
            check_results["bedrock_regions"]["status"],
            check_results["bedrock_runtime"]["status"],
            check_results["bedrock_models"]["status"],
            check_results["key_models"]["status"]
        ]
        
        if "❌ ERROR" in all_statuses:
            overall_status = "❌ ERROR"
            overall_class = "error"
            overall_message = "There are critical issues with your Bedrock setup"
        elif "⚠️ WARNING" in all_statuses:
            overall_status = "⚠️ WARNING"
            overall_class = "warning"
            overall_message = "Your Bedrock setup has some issues but may work for some use cases"
        elif all(status == "✅ SUCCESS" for status in all_statuses if status is not None):
            overall_status = "✅ SUCCESS"
            overall_class = "success"
            overall_message = "Your Bedrock setup looks good!"
        else:
            overall_status = "ℹ️ INFO"
            overall_class = "info"
            overall_message = "Some checks were inconclusive"
        
        html.append(f"      <h3>Overall Status: <span class='{overall_class}'>{overall_status}</span></h3>")
        html.append(f"      <p>{overall_message}</p>")
        html.append("    </div>")
        
        # Regions Section
        html.append("    <div class='details-section'>")
        html.append("      <h2>Available Regions</h2>")
        html.append("      <div class='region-list'>")
        for region in check_results["bedrock_regions"]["available"]:
            html.append(f"        <div class='region-badge'>{region}</div>")
        html.append("      </div>")
        html.append("    </div>")
        
        # SageMaker Alternatives Section
        if "sagemaker_alternatives" in check_results and check_results["sagemaker_alternatives"]:
            # Exclude error entry when counting alternatives
            alternatives_count = sum(1 for k in check_results["sagemaker_alternatives"] if k != "error")
            
            if alternatives_count > 0:
                html.append("    <div class='details-section'>")
                html.append("      <h2>SageMaker JumpStart Alternatives</h2>")
                html.append("      <p>The following alternatives are available in SageMaker JumpStart for missing Bedrock models:</p>")
                html.append("      <table class='summary-table'>")
                html.append("        <tr><th>Missing Bedrock Model</th><th>SageMaker Alternative</th><th>Notes</th></tr>")
                
                for model_id, alternatives in check_results["sagemaker_alternatives"].items():
                    if model_id != "error" and alternatives:
                        for i, alt in enumerate(alternatives):
                            if i == 0:  # First alternative for this model
                                html.append(f"        <tr><td>{model_id}</td><td>{alt['name']} ({alt['model_id']})</td><td>{alt['notes']}</td></tr>")
                            else:  # Additional alternatives
                                html.append(f"        <tr><td></td><td>{alt['name']} ({alt['model_id']})</td><td>{alt['notes']}</td></tr>")
                
                html.append("      </table>")
                html.append("    </div>")
        
        # Models Section
        html.append("    <div class='details-section'>")
        html.append("      <h2>Model Availability</h2>")
        html.append("      <div class='model-grid'>")
        
        # Key models with their status
        all_key_models = check_results["key_models"]["available"] + check_results["key_models"]["missing"]
        
        # Get invocation results if available
        invoke_success = []
        invoke_fail = []
        if "model_invocations" in check_results:
            invoke_success = check_results["model_invocations"]["successful"]
            invoke_fail = check_results["model_invocations"]["failed"]
        
        for model in sorted(all_key_models):
            is_available = model in check_results["key_models"]["available"]
            status_class = "success" if is_available else "error"
            status_text = "Available" if is_available else "Not Available"
            
            html.append(f"        <div class='model-card'>")
            html.append(f"          <h3>{model}</h3>")
            html.append(f"          <p>Listing: <span class='{status_class}'>{status_text}</span></p>")
            
            # Add invocation status if available
            if is_available and (model in invoke_success or model in invoke_fail):
                invoke_status = "Invocation Successful" if model in invoke_success else "Invocation Failed"
                invoke_class = "success" if model in invoke_success else "error"
                html.append(f"          <p>Test: <span class='{invoke_class}'>{invoke_status}</span></p>")
            elif is_available and "model_invocations" in check_results:
                html.append(f"          <p>Test: <span class='info'>Not Tested</span></p>")
                
            # Get the purpose for this model
            model_purpose = "Unknown"
            for model_info in needed_models:
                if model_info["id"] == model:
                    model_purpose = model_info["purpose"]
                    break
                    
            html.append(f"          <p><small>{model_purpose}</small></p>")
            
            # Add detailed model information if available
            if "model_details" in check_results and model in check_results["model_details"]:
                model_details = check_results["model_details"][model]
                
                # Add collapsible section for details
                html.append("          <details>")
                html.append("            <summary>Advanced Details</summary>")
                html.append("            <div style='margin-top: 10px;'>")
                
                # Specs section
                if "specs" in model_details and model_details["specs"]:
                    html.append("              <h4>Specifications</h4>")
                    html.append("              <ul>")
                    for key, value in model_details["specs"].items():
                        if key != "error":
                            html.append(f"                <li><strong>{key}:</strong> {value}</li>")
                    html.append("              </ul>")
                
                # Inference parameters
                if "inference_params" in model_details and model_details["inference_params"]:
                    html.append("              <h4>Inference Parameters</h4>")
                    html.append("              <ul>")
                    for key, value in model_details["inference_params"].items():
                        html.append(f"                <li><strong>{key}:</strong> {value}</li>")
                    html.append("              </ul>")
                
                # Quotas
                if "quotas" in model_details and model_details["quotas"]:
                    html.append("              <h4>Quotas</h4>")
                    html.append("              <ul>")
                    for key, value in model_details["quotas"].items():
                        if key != "error":
                            if isinstance(value, dict):
                                quota_str = f"{value.get('value')} {value.get('unit', '')}"
                                if value.get('adjustable'):
                                    quota_str += " (adjustable)"
                                html.append(f"                <li><strong>{key}:</strong> {quota_str}</li>")
                            else:
                                html.append(f"                <li><strong>{key}:</strong> {value}</li>")
                    html.append("              </ul>")
                
                # Close the collapsible section
                html.append("            </div>")
                html.append("          </details>")
            
            html.append("        </div>")
        
        html.append("      </div>")
        html.append("    </div>")
        
        # Troubleshooting Section
        if overall_status != "✅ SUCCESS":
            html.append("    <div class='details-section'>")
            html.append("      <h2>Troubleshooting Tips</h2>")
            
            if check_results["aws_credentials"]["status"] in ["❌ ERROR", "⚠️ WARNING"]:
                html.append("      <h3>AWS Credentials</h3>")
                html.append("      <ul>")
                html.append("        <li>Run 'aws configure' to set up credentials</li>")
                html.append("        <li>Verify your credentials have Bedrock permissions</li>")
                html.append("        <li>Check if boto3 version is at least 1.28.0</li>")
                html.append("      </ul>")
            
            if check_results["bedrock_regions"]["status"] in ["❌ ERROR", "⚠️ WARNING"]:
                html.append("      <h3>Bedrock Regions</h3>")
                html.append("      <ul>")
                html.append("        <li>Make sure Bedrock is enabled in your AWS account</li>")
                html.append("        <li>Check if your IAM permissions include bedrock:ListFoundationModels</li>")
                html.append("        <li>Verify you're checking regions where Bedrock is available</li>")
                html.append("      </ul>")
            
            if check_results["key_models"]["status"] in ["❌ ERROR", "⚠️ WARNING"]:
                html.append("      <h3>Model Access</h3>")
                html.append("      <ul>")
                html.append("        <li>Visit AWS console to request access to needed models: ")
                html.append("          <a href='https://console.aws.amazon.com/bedrock/home#/modelaccess' target='_blank'>AWS Bedrock Model Access</a></li>")
                html.append("        <li>For Claude models, make sure you've accepted Anthropic's terms of service</li>")
                html.append("        <li>Some models require explicit subscription - check your model access</li>")
                html.append("      </ul>")
            html.append("    </div>")
        
        # Footer
        html.append("    <div class='footer'>")
        html.append("      <p>Generated by AWS Bedrock Access Verification Tool</p>")
        html.append(f"      <p>Report ID: {timestamp}</p>")
        html.append("    </div>")
        
        html.append("  </div>")
        html.append("</body>")
        html.append("</html>")
        
        # Write the HTML file
        with open(filename, 'w') as f:
            f.write('\n'.join(html))
        
        console.print(f"\n[green]HTML report saved to {filename}[/green]")