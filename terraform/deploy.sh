#!/bin/bash

# Jira Q Business Connector - Terraform Deployment Script
# This script sources environment variables and runs terraform securely

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if required environment variables are set
check_required_vars() {
    local required_vars=(
        "TF_VAR_container_image"
        "TF_VAR_jira_server_url"
        "TF_VAR_jira_username"
        "TF_VAR_jira_password"
        "TF_VAR_q_application_id"
        "TF_VAR_q_data_source_id"
        "TF_VAR_q_index_id"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        print_message $RED "❌ Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "   - $var"
        done
        echo
        print_message $YELLOW "💡 Create .env.terraform from env.terraform.example and source it:"
        echo "   cp env.terraform.example .env.terraform"
        echo "   # Edit .env.terraform with your values"
        echo "   source .env.terraform"
        echo "   # Then run this script again"
        exit 1
    fi
}

# Function to display help
show_help() {
    cat << EOF
Jira Q Business Connector - Terraform Deployment Script

USAGE:
    $0 [COMMAND] [OPTIONS]

COMMANDS:
    plan        Run terraform plan
    apply       Run terraform apply
    destroy     Run terraform destroy
    output      Show terraform outputs
    clean       Clean terraform state and modules
    help        Show this help message

OPTIONS:
    --auto-approve    Skip interactive approval for apply/destroy
    --var-file FILE   Use additional var file
    --target RESOURCE Target specific resource

EXAMPLES:
    # Source environment variables and run plan
    source .env.terraform && $0 plan
    
    # Apply with auto-approval
    source .env.terraform && $0 apply --auto-approve
    
    # Destroy infrastructure
    source .env.terraform && $0 destroy
    
    # Show outputs
    $0 output

SETUP:
    1. Copy environment template:
       cp env.terraform.example .env.terraform
    
    2. Edit with your values:
       nano .env.terraform
    
    3. Source environment variables:
       source .env.terraform
    
    4. Run terraform:
       $0 plan
       $0 apply

EOF
}

# Main script logic
main() {
    local command=${1:-help}
    shift || true
    
    case $command in
        plan)
            print_message $BLUE "🔍 Checking environment variables..."
            check_required_vars
            print_message $GREEN "✅ All required variables are set"
            
            print_message $BLUE "📋 Running terraform plan..."
            terraform init
            terraform plan "$@"
            ;;
            
        apply)
            print_message $BLUE "🔍 Checking environment variables..."
            check_required_vars
            print_message $GREEN "✅ All required variables are set"
            
            print_message $BLUE "🚀 Running terraform apply..."
            terraform init
            terraform apply "$@"
            
            if [[ $? -eq 0 ]]; then
                print_message $GREEN "🎉 Deployment completed successfully!"
                echo
                print_message $BLUE "📊 Quick Links:"
                terraform output monitoring_urls 2>/dev/null || true
                echo
                print_message $BLUE "💻 Useful Commands:"
                terraform output useful_commands 2>/dev/null || true
            fi
            ;;
            
        destroy)
            print_message $YELLOW "⚠️  This will destroy all infrastructure!"
            if [[ "$*" != *"--auto-approve"* ]]; then
                read -p "Are you sure? (yes/no): " -r
                if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
                    print_message $YELLOW "Aborted."
                    exit 1
                fi
            fi
            
            print_message $BLUE "🔍 Checking environment variables..."
            check_required_vars
            print_message $GREEN "✅ All required variables are set"
            
            print_message $RED "💥 Running terraform destroy..."
            terraform destroy "$@"
            ;;
            
        output)
            print_message $BLUE "📊 Terraform outputs:"
            terraform output "$@"
            ;;
            
        clean)
            print_message $YELLOW "🧹 Cleaning terraform state and modules..."
            rm -rf .terraform
            rm -f .terraform.lock.hcl
            rm -f terraform.tfstate*
            print_message $GREEN "✅ Cleaned terraform files"
            ;;
            
        help|--help|-h)
            show_help
            ;;
            
        *)
            print_message $RED "❌ Unknown command: $command"
            echo
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 