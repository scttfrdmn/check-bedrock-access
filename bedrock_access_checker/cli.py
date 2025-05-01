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
    display_summary_dashboard,
    output_results
)

console = Console()

def main():
    """Main entry point for the AWS Bedrock Access Checker"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Check AWS Bedrock access with profile support')
    parser.add_argument('--profile', '-p', help='AWS profile name to use')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode to select profile')
    parser.add_argument('--output', '-o', choices=['json', 'csv'], help='Output format for saving results')
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
    
    # Check Bedrock regions
    available_regions = check_bedrock_regions(profile_name)
    
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
        check_specific_models_simple(region, profile_name)
    
    # Display the summary dashboard
    display_summary_dashboard()
    
    # Handle output formats if specified
    if args.output:
        output_results(args.output)

if __name__ == "__main__":
    main()