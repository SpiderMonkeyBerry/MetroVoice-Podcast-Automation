#!/bin/bash

# MetroVoice Podcast Automation - Deployment Script
# This script packages and deploys the Lambda function to AWS

set -e  # Exit on any error

# Configuration
STACK_NAME="metrovoice-podcast-automation"
LAMBDA_FUNCTION_NAME="metrovoice-podcast-automation"
S3_BUCKET_NAME="tmv-podcast-content"
SNS_TOPIC_NAME="Upload_Podcast_Trigger"
REGION="us-west-2"
DEPLOYMENT_PACKAGE="deployment-package.zip"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists aws; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install it first."
        exit 1
    fi
    
    if ! command_exists pip3; then
        print_error "pip3 is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Create deployment package
create_deployment_package() {
    print_status "Creating deployment package..."
    
    # Create temporary directory
    TEMP_DIR=$(mktemp -d)
    print_status "Using temporary directory: $TEMP_DIR"
    
    # Copy source files
    cp *.py "$TEMP_DIR/"
    cp requirements.txt "$TEMP_DIR/"
    
    # Install dependencies
    print_status "Installing dependencies..."
    pip3 install -r requirements.txt -t "$TEMP_DIR/" --no-deps
    
    # Create deployment package
    cd "$TEMP_DIR"
    zip -r "$DEPLOYMENT_PACKAGE" . -x "*.pyc" "__pycache__/*" "*.pyo" "*.pyd" ".Python" "env/*" "venv/*" ".venv/*"
    
    # Move package to current directory
    mv "$DEPLOYMENT_PACKAGE" "$OLDPWD/"
    cd "$OLDPWD"
    
    # Clean up
    rm -rf "$TEMP_DIR"
    
    print_success "Deployment package created: $DEPLOYMENT_PACKAGE"
}

# Deploy CloudFormation stack
deploy_cloudformation() {
    print_status "Deploying CloudFormation stack..."
    
    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" >/dev/null 2>&1; then
        print_status "Stack exists, updating..."
        aws cloudformation update-stack \
            --stack-name "$STACK_NAME" \
            --template-body file://deployment/cloudformation.yaml \
            --parameters \
                ParameterKey=LambdaFunctionName,ParameterValue="$LAMBDA_FUNCTION_NAME" \
                ParameterKey=S3BucketName,ParameterValue="$S3_BUCKET_NAME" \
                ParameterKey=SNSTopicName,ParameterValue="$SNS_TOPIC_NAME" \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$REGION"
        
        print_status "Waiting for stack update to complete..."
        aws cloudformation wait stack-update-complete --stack-name "$STACK_NAME" --region "$REGION"
    else
        print_status "Creating new stack..."
        aws cloudformation create-stack \
            --stack-name "$STACK_NAME" \
            --template-body file://deployment/cloudformation.yaml \
            --parameters \
                ParameterKey=LambdaFunctionName,ParameterValue="$LAMBDA_FUNCTION_NAME" \
                ParameterKey=S3BucketName,ParameterValue="$S3_BUCKET_NAME" \
                ParameterKey=SNSTopicName,ParameterValue="$SNS_TOPIC_NAME" \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$REGION"
        
        print_status "Waiting for stack creation to complete..."
        aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME" --region "$REGION"
    fi
    
    print_success "CloudFormation stack deployed successfully"
}

# Update Lambda function code
update_lambda_code() {
    print_status "Updating Lambda function code..."
    
    # Get function ARN
    FUNCTION_ARN=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='LambdaFunctionArn'].OutputValue" \
        --output text)
    
    # Update function code
    aws lambda update-function-code \
        --function-name "$FUNCTION_ARN" \
        --zip-file "fileb://$DEPLOYMENT_PACKAGE" \
        --region "$REGION"
    
    print_status "Waiting for Lambda function update to complete..."
    aws lambda wait function-updated --function-name "$FUNCTION_ARN" --region "$REGION"
    
    print_success "Lambda function code updated successfully"
}

# Set environment variables
set_environment_variables() {
    print_status "Setting environment variables..."
    
    # Check if environment variables are set
    if [ -z "$PERPLEXITY_API_KEY" ] || [ -z "$ELEVENLABS_API_KEY" ] || [ -z "$PODBEAN_CLIENT_ID" ] || [ -z "$PODBEAN_CLIENT_SECRET" ]; then
        print_warning "Environment variables not set. Please set the following variables:"
        echo "  PERPLEXITY_API_KEY"
        echo "  ELEVENLABS_API_KEY"
        echo "  PODBEAN_CLIENT_ID"
        echo "  PODBEAN_CLIENT_SECRET"
        echo ""
        echo "You can set them using:"
        echo "  export PERPLEXITY_API_KEY='your_key'"
        echo "  export ELEVENLABS_API_KEY='your_key'"
        echo "  export PODBEAN_CLIENT_ID='your_id'"
        echo "  export PODBEAN_CLIENT_SECRET='your_secret'"
        echo ""
        read -p "Do you want to continue without setting environment variables? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        # Get function ARN
        FUNCTION_ARN=$(aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$REGION" \
            --query "Stacks[0].Outputs[?OutputKey=='LambdaFunctionArn'].OutputValue" \
            --output text)
        
        # Update environment variables
        aws lambda update-function-configuration \
            --function-name "$FUNCTION_ARN" \
            --environment "Variables={PERPLEXITY_API_KEY=$PERPLEXITY_API_KEY,ELEVENLABS_API_KEY=$ELEVENLABS_API_KEY,PODBEAN_CLIENT_ID=$PODBEAN_CLIENT_ID,PODBEAN_CLIENT_SECRET=$PODBEAN_CLIENT_SECRET}" \
            --region "$REGION"
        
        print_success "Environment variables set successfully"
    fi
}

# Test the deployment
test_deployment() {
    print_status "Testing deployment..."
    
    # Get function ARN
    FUNCTION_ARN=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='LambdaFunctionArn'].OutputValue" \
        --output text)
    
    # Test with status action
    aws lambda invoke \
        --function-name "$FUNCTION_ARN" \
        --payload '{"action": "status"}' \
        --region "$REGION" \
        response.json
    
    if [ -f response.json ]; then
        print_status "Test response:"
        cat response.json
        rm response.json
    fi
    
    print_success "Deployment test completed"
}

# Clean up
cleanup() {
    print_status "Cleaning up..."
    rm -f "$DEPLOYMENT_PACKAGE"
    print_success "Cleanup completed"
}

# Main deployment function
main() {
    print_status "Starting MetroVoice Podcast Automation deployment..."
    
    check_prerequisites
    create_deployment_package
    deploy_cloudformation
    update_lambda_code
    set_environment_variables
    test_deployment
    cleanup
    
    print_success "Deployment completed successfully!"
    print_status "Your MetroVoice Podcast Automation system is now live."
    print_status "Check CloudWatch Logs for function execution details."
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --test         Only test the deployment (skip actual deployment)"
        echo "  --cleanup      Only clean up deployment artifacts"
        echo ""
        echo "Environment Variables:"
        echo "  PERPLEXITY_API_KEY      API key for Perplexity AI"
        echo "  ELEVENLABS_API_KEY      API key for ElevenLabs"
        echo "  PODBEAN_CLIENT_ID       Client ID for Podbean"
        echo "  PODBEAN_CLIENT_SECRET   Client secret for Podbean"
        exit 0
        ;;
    --test)
        print_status "Running in test mode..."
        check_prerequisites
        create_deployment_package
        test_deployment
        cleanup
        exit 0
        ;;
    --cleanup)
        cleanup
        exit 0
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac 