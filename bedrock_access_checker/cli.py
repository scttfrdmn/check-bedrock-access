#!/usr/bin/env python3
"""
Command-line interface for the AWS Bedrock Access Checker.
"""

import argparse
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from bedrock_access_checker.checker import (
    list_available_profiles,
    check_aws_credentials,
    check_bedrock_regions,
    check_bedrock_runtime_access,
    check_bedrock_models,
    check_specific_models_simple,
    check_sagemaker_jumpstart_alternatives,
    display_summary_dashboard,
    output_results
)

console = Console()

def main():
    """Main entry point for the AWS Bedrock Access Checker"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Check AWS Bedrock access with profile support')
    parser.add_argument('--profile', '-p', help='AWS profile name to use')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode to select profile and/or regions')
    parser.add_argument('--output', '-o', choices=['json', 'csv', 'html'], help='Output format for saving results')
    parser.add_argument('--region', '-r', action='append', help='Specific AWS region(s) to check (can be used multiple times)')
    parser.add_argument('--all-regions', '-a', action='store_true', help='Check all Bedrock-supported regions')
    parser.add_argument('--test-invoke', '-t', action='store_true', help='Test model invocation to verify full access (may incur costs)')
    parser.add_argument('--advanced', '-v', action='store_true', help='Enable advanced mode with detailed inference capabilities and quota information')
    parser.add_argument('--sagemaker-alternatives', '-s', action='store_true', help='Check SageMaker JumpStart for alternatives to missing Bedrock models')
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
        display_summary_dashboard()
        return
    
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
        
        # Display the summary dashboard even if there are errors
        display_summary_dashboard()
        return
    
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
    
    # Add notices based on mode
    if args.test_invoke:
        console.print("\n[yellow]Notice: Model invocation tests may have incurred small AWS charges.[/yellow]")
    
    if args.advanced:
        console.print("\n[blue]Advanced mode: Detailed model information and quotas have been included in the results.[/blue]")
        
    if args.sagemaker_alternatives:
        console.print("\n[blue]SageMaker JumpStart alternatives have been suggested for missing Bedrock models.[/blue]")
    
    # Display the summary dashboard
    display_summary_dashboard()
    
    # Handle output formats if specified
    if args.output:
        output_results(args.output)

if __name__ == "__main__":
    main()