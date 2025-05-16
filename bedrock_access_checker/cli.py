"""
Command-line interface for the AWS Bedrock Access Checker.
"""

import argparse
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.box import ROUNDED

from bedrock_access_checker.checker import (
    list_available_profiles,
    check_aws_credentials,
    check_bedrock_regions,
    check_bedrock_runtime_access,
    check_bedrock_models,
    check_specific_models_simple,
    check_sagemaker_jumpstart_alternatives,
    display_summary_dashboard,
    output_results,
    check_results
)

console = Console()


def compare_profile_results(profile_results):
    """
    Compare the results from multiple profiles and display a comparison table.
    
    Args:
        profile_results (dict): Dictionary mapping profile names to their check_results
    """
    console.print("\n[bold]Profile Comparison[/bold]")
    
    # Create tables for different comparison aspects
    
    # 1. Overall status comparison
    status_table = Table(title="Profile Status Comparison", box=ROUNDED)
    status_table.add_column("Profile", style="cyan")
    status_table.add_column("AWS Credentials", style="green")
    status_table.add_column("Bedrock Regions", style="green")
    status_table.add_column("Bedrock Models", style="green")
    status_table.add_column("Key Models", style="green")
    
    for profile_name, results in profile_results.items():
        # For each profile, add a row with their statuses
        cred_status = results["aws_credentials"]["status"] or "N/A"
        region_status = results["bedrock_regions"]["status"] or "N/A"
        models_status = results["bedrock_models"]["status"] or "N/A"
        key_models_status = results["key_models"]["status"] or "N/A"
        
        status_table.add_row(
            profile_name,
            cred_status,
            region_status,
            models_status,
            key_models_status
        )
    
    console.print(status_table)
    
    # 2. Region availability comparison
    region_table = Table(title="Region Availability Comparison", box=ROUNDED)
    region_table.add_column("Profile", style="cyan")
    
    # Find all available regions across all profiles
    all_regions = set()
    for results in profile_results.values():
        all_regions.update(results["bedrock_regions"]["available"])
    
    # Add columns for each region
    for region in sorted(all_regions):
        region_table.add_column(region, style="green")
    
    # Add rows for each profile
    for profile_name, results in profile_results.items():
        row_data = [profile_name]
        
        # Add availability for each region
        for region in sorted(all_regions):
            if region in results["bedrock_regions"]["available"]:
                row_data.append("✓")
            else:
                row_data.append("✗")
        
        region_table.add_row(*row_data)
    
    console.print(region_table)
    
    # 3. Key model availability comparison
    model_table = Table(title="Key Model Availability Comparison", box=ROUNDED)
    model_table.add_column("Profile", style="cyan")
    
    # Find all available and missing models across all profiles
    all_models = set()
    for results in profile_results.values():
        all_models.update(results["key_models"]["available"])
        all_models.update(results["key_models"]["missing"])
    
    # Add columns for each model
    for model in sorted(all_models):
        # Shorten model name for display
        short_model = model.split(':')[0] if ':' in model else model
        short_model = short_model.split('.')[-1]  # Get just the model name part
        model_table.add_column(short_model, style="green")
    
    # Add rows for each profile
    for profile_name, results in profile_results.items():
        row_data = [profile_name]
        
        # Add availability for each model
        for model in sorted(all_models):
            if model in results["key_models"]["available"]:
                row_data.append("✓")
            elif model in results["key_models"]["missing"]:
                row_data.append("✗")
            else:
                row_data.append("-")
        
        model_table.add_row(*row_data)
    
    console.print(model_table)
    
    # 4. Summary statistics
    summary_table = Table(title="Profile Summary Statistics", box=ROUNDED)
    summary_table.add_column("Profile", style="cyan")
    summary_table.add_column("Available Regions", style="green")
    summary_table.add_column("Available Models", style="green")
    summary_table.add_column("Key Models", style="green")
    
    for profile_name, results in profile_results.items():
        region_count = len(results["bedrock_regions"]["available"])
        model_count = len(set(results["bedrock_models"]["available"])) if "available" in results["bedrock_models"] else 0
        key_model_count = len(results["key_models"]["available"])
        key_model_total = len(results["key_models"]["available"]) + len(results["key_models"]["missing"])
        
        summary_table.add_row(
            profile_name,
            str(region_count),
            str(model_count),
            f"{key_model_count}/{key_model_total}"
        )
    
    console.print(summary_table)


def main():
    """Main entry point for the AWS Bedrock Access Checker"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Check AWS Bedrock access with profile support')
    parser.add_argument('--profile', '-p', action='append', help='AWS profile name(s) to use (can be specified multiple times)')
    parser.add_argument('--all-profiles', '-P', action='store_true', help='Check all available AWS profiles')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode to select profile and/or regions')
    parser.add_argument('--output', '-o', choices=['json', 'csv', 'html'], help='Output format for saving results')
    parser.add_argument('--region', '-r', action='append', help='Specific AWS region(s) to check (can be used multiple times)')
    parser.add_argument('--all-regions', '-a', action='store_true', help='Check all Bedrock-supported regions')
    parser.add_argument('--test-invoke', '-t', action='store_true', help='Test model invocation to verify full access (may incur costs)')
    parser.add_argument('--advanced', '-v', action='store_true', help='Enable advanced mode with detailed inference capabilities and quota information')
    parser.add_argument('--sagemaker-alternatives', '-s', action='store_true', help='Check SageMaker JumpStart for alternatives to missing Bedrock models')
    parser.add_argument('--estimate-costs', '-e', action='store_true', help='Show cost estimates for using available Bedrock models')
    parser.add_argument('--compare', '-c', action='store_true', help='Compare results when checking multiple profiles')
    args = parser.parse_args()
    
    # Initialize results storage for multiple profiles
    all_profile_results = {}
    
    # Get all available profiles
    available_profiles = list_available_profiles()
    
    # Determine which profiles to check
    profiles_to_check = []
    
    if args.all_profiles:
        # Use all available profiles
        profiles_to_check = available_profiles
        console.print(f"[bold]Checking all {len(profiles_to_check)} AWS profiles...[/bold]")
    elif args.profile:
        # Use profiles specified on the command line
        profiles_to_check = args.profile
        # Validate profiles
        for profile in profiles_to_check[:]:
            if profile not in available_profiles:
                console.print(f"[yellow]Warning: Profile '{profile}' not found. It will be skipped.[/yellow]")
    elif args.interactive:
        # Interactive profile selection
        if not available_profiles:
            console.print("[yellow]No AWS profiles found. Using default credentials.[/yellow]")
            profiles_to_check = [None]  # Use default profile
        else:
            # Add "default" option (no profile)
            choices = ["default (no profile)"] + available_profiles + ["All profiles"]
            
            # Let the user select multiple profiles
            console.print("\n[bold]Select AWS profiles to check:[/bold]")
            console.print("[dim](You can select multiple profiles by running this selection multiple times)[/dim]")
            
            selected_profiles = []
            while True:
                # Show current selection
                if selected_profiles:
                    if None in selected_profiles:
                        current = ["default"] + [p for p in selected_profiles if p is not None]
                        console.print(f"[green]Currently selected: {', '.join(current)}[/green]")
                    else:
                        console.print(f"[green]Currently selected: {', '.join(selected_profiles)}[/green]")
                
                # Ask for profile
                selected = Prompt.ask(
                    "[bold blue]Select AWS profile[/bold blue] (Enter 'done' when finished)", 
                    choices=choices + ["done"],
                    default="done" if selected_profiles else "default (no profile)"
                )
                
                if selected == "done":
                    break
                elif selected == "All profiles":
                    selected_profiles = available_profiles
                    break
                elif selected == "default (no profile)":
                    if None not in selected_profiles:
                        selected_profiles.append(None)
                else:
                    if selected not in selected_profiles:
                        selected_profiles.append(selected)
            
            profiles_to_check = selected_profiles
    else:
        # Default to using no profile (default credentials)
        profiles_to_check = [None]
    
    # Add default profile if list is empty
    if not profiles_to_check:
        console.print("[yellow]No valid profiles selected. Using default credentials.[/yellow]")
        profiles_to_check = [None]
    
    # Print welcome message
    console.print(Panel.fit(
        "[bold green]AWS Bedrock Access Verification Tool[/bold green]\n"
        "[yellow]Check if your AWS credentials can access Bedrock services[/yellow]",
        border_style="blue"
    ))
    
    # Initialize a dictionary to store results for each profile
    from copy import deepcopy
    
    # Loop through each profile and run the checks
    for profile_index, profile_name in enumerate(profiles_to_check):
        # Reset check_results for each profile 
        global check_results
        check_results = {
            "aws_credentials": {"status": None, "details": [], "errors": []},
            "bedrock_regions": {"status": None, "available": [], "details": [], "errors": []},
            "bedrock_runtime": {"status": None, "available": [], "details": [], "errors": []},
            "bedrock_models": {"status": None, "available": [], "details": [], "errors": []},
            "key_models": {"status": None, "available": [], "missing": [], "details": [], "errors": []},
            "cost_estimates": {"models": {}, "details": []},
        }
        
        # Print header for current profile
        if len(profiles_to_check) > 1:
            console.print(f"\n[bold]=== Checking profile {profile_index + 1}/{len(profiles_to_check)}: {profile_name or 'default'} ===[/bold]")
        elif profile_name:
            console.print(f"[bold]Using AWS profile: [cyan]{profile_name}[/cyan][/bold]")
        
        # Check AWS credentials
        if not check_aws_credentials(profile_name):
            console.print(f"\n[bold red]AWS credential check failed for profile '{profile_name or 'default'}'. Skipping this profile.[/bold red]")
            # Store the results for this profile anyway
            all_profile_results[profile_name or "default"] = deepcopy(check_results)
            continue
    
        # Determine which regions to check
        regions_to_check = None
        
        # Get list of all Bedrock regions from checker module
        from bedrock_access_checker.checker import all_bedrock_regions
        
        if args.all_regions:
            # Use all available Bedrock regions
            regions_to_check = all_bedrock_regions.copy()
            console.print(f"[bold]Checking all {len(regions_to_check)} Bedrock-supported regions...[/bold]")
        elif args.region:
            # Use regions specified on the command line
            regions_to_check = args.region
            # Validate regions
            for region in regions_to_check[:]:
                if region not in all_bedrock_regions:
                    console.print(f"[yellow]Warning: {region} may not support Bedrock[/yellow]")
        elif args.interactive:
            # Interactive region selection
            from rich.checkbox import Checkbox
            
            console.print("\n[bold]Select regions to check:[/bold]")
            
            # Group regions by geography for easier selection
            region_groups = {
                "US Regions": [r for r in all_bedrock_regions if r.startswith("us-")],
                "Europe Regions": [r for r in all_bedrock_regions if r.startswith("eu-")],
                "Asia Pacific Regions": [r for r in all_bedrock_regions if r.startswith("ap-")],
                "Other Regions": [r for r in all_bedrock_regions if not (r.startswith("us-") or r.startswith("eu-") or r.startswith("ap-"))]
            }
            
            # Create region choices with human-readable names
            region_display = {
                'us-east-1': 'US East (N. Virginia)',
                'us-east-2': 'US East (Ohio)',
                'us-west-1': 'US West (N. California)',
                'us-west-2': 'US West (Oregon)',
                'ap-northeast-1': 'Asia Pacific (Tokyo)',
                'ap-northeast-2': 'Asia Pacific (Seoul)',
                'ap-south-1': 'Asia Pacific (Mumbai)',
                'ap-southeast-1': 'Asia Pacific (Singapore)',
                'ap-southeast-2': 'Asia Pacific (Sydney)',
                'eu-central-1': 'Europe (Frankfurt)',
                'eu-north-1': 'Europe (Stockholm)',
                'eu-west-1': 'Europe (Ireland)',
                'eu-west-2': 'Europe (London)',
                'eu-west-3': 'Europe (Paris)',
                'ca-central-1': 'Canada (Central)'
            }
            
            # Display choices by group
            selected_regions = []
            
            console.print("\nSelect regions to check (space to select, enter to confirm):")
            
            for group_name, group_regions in region_groups.items():
                if not group_regions:
                    continue
                    
                console.print(f"\n[bold]{group_name}:[/bold]")
                choices = [f"{r} - {region_display.get(r, r)}" for r in group_regions]
                
                # Use Prompt.ask for each region rather than Checkbox which is harder to use in CLI
                for i, choice in enumerate(choices):
                    include = Prompt.ask(f"  Include {choice}", choices=["y", "n"], default="n")
                    if include.lower() == "y":
                        selected_regions.append(group_regions[i])
            
            # Make sure at least one region is selected
            if not selected_regions:
                console.print("[yellow]No regions selected. Using default regions (us-east-1, us-west-2).[/yellow]")
                selected_regions = ['us-east-1', 'us-west-2']
            else:
                console.print(f"[green]Selected {len(selected_regions)} regions for checking.[/green]")
                
            regions_to_check = selected_regions
        
        # Check Bedrock regions
        available_regions = check_bedrock_regions(profile_name, regions_to_check)
        
        if not available_regions:
            console.print("\n[bold red]No available Bedrock regions found![/bold red]")
            console.print("[yellow]Possible reasons:[/yellow]")
            console.print("1. Your AWS account doesn't have Bedrock enabled")
            console.print("2. Your AWS credentials don't have Bedrock permissions")
            console.print("3. Bedrock isn't available in your account's regions")
            
            # Store the results for this profile
            all_profile_results[profile_name or "default"] = deepcopy(check_results)
            
            # Skip to the next profile
            continue
        
        # For each available region, check runtime access and models
        for region in available_regions:
            check_bedrock_runtime_access(region, profile_name)
            check_bedrock_models(region, profile_name)
            check_specific_models_simple(region, profile_name, args.test_invoke, args.advanced)
            
        # Check SageMaker JumpStart alternatives if requested
        if args.sagemaker_alternatives and check_results["key_models"]["missing"]:
            # Use the first valid region for checking SageMaker alternatives
            sagemaker_region = available_regions[0] if available_regions else "us-east-1"
            check_sagemaker_jumpstart_alternatives(check_results["key_models"]["missing"], sagemaker_region, profile_name)
            
        # Estimate costs if requested
        if args.estimate_costs and check_results["key_models"]["available"]:
            # Import the function
            from bedrock_access_checker.checker import estimate_model_costs
            # Use the first valid region for cost estimation (pricing may vary by region)
            cost_region = available_regions[0] if available_regions else "us-east-1"
            estimate_model_costs(check_results["key_models"]["available"], cost_region, profile_name)
        
        # Store the results for this profile
        all_profile_results[profile_name or "default"] = deepcopy(check_results)
        
        # Add notices based on mode
        if args.test_invoke:
            console.print("\n[yellow]Notice: Model invocation tests may have incurred small AWS charges.[/yellow]")
        
        if args.advanced:
            console.print("\n[blue]Advanced mode: Detailed model information and quotas have been included in the results.[/blue]")
            
        if args.sagemaker_alternatives:
            console.print("\n[blue]SageMaker JumpStart alternatives have been suggested for missing Bedrock models.[/blue]")
        
        if args.estimate_costs:
            console.print("\n[blue]Cost estimates have been provided for available Bedrock models.[/blue]")
        
        # Display the summary dashboard for each profile
        if len(profiles_to_check) > 1:
            console.print(f"\n[bold]Summary for profile: {profile_name or 'default'}[/bold]")
        
        display_summary_dashboard()
    
    # If multiple profiles were checked and --compare was specified, display a comparison
    if len(profiles_to_check) > 1 and args.compare:
        compare_profile_results(all_profile_results)
    
    # Handle output formats if specified
    if args.output:
        # For multiple profiles, create separate output files for each profile
        if len(profiles_to_check) > 1:
            for profile_name, results in all_profile_results.items():
                # Temporarily replace check_results with this profile's results
                temp_results = check_results
                check_results = results
                
                # Create a filename that includes the profile name
                output_results(args.output, f"{profile_name}_")
                
                # Restore the original check_results
                check_results = temp_results
        else:
            output_results(args.output)
            
    # If multiple profiles were checked, display a summary
    if len(profiles_to_check) > 1:
        console.print(f"\n[bold green]Completed checking {len(profiles_to_check)} AWS profiles.[/bold green]")
        
        # Count profiles with access
        profiles_with_access = sum(1 for results in all_profile_results.values() 
                                  if results["key_models"]["available"])
        
        console.print(f"[green]{profiles_with_access}/{len(profiles_to_check)} profiles have Bedrock access.[/green]")


if __name__ == "__main__":
    main()