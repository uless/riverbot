#!/bin/sh

# Check if AWS_ACCESS_KEY_ID is set
if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "AWS_ACCESS_KEY_ID is not set"
    exit 1
fi

# Check if AWS_SECRET_ACCESS_KEY is set
if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "AWS_SECRET_ACCESS_KEY is not set"
    exit 1
fi

# Check if AWS_SESSION_TOKEN is set
if [ -z "$AWS_SESSION_TOKEN" ]; then
    echo "AWS_SESSION_TOKEN is not set"
    exit 1
fi


# Check if CLUSTER_NAME is set
if [ -z "$CLUSTER_NAME" ]; then
    echo "CLUSTER_NAME is not set"
    exit 1
fi

# Check if SERVICE_NAME is set
if [ -z "$SERVICE_NAME" ]; then
    echo "SERVICE_NAME is not set"
    exit 1
fi

# Set the required variables
CLUSTER_NAME=$CLUSTER_NAME
SERVICE_NAME=$SERVICE_NAME

# Get the service details
SERVICE_DETAILS=$(aws ecs describe-services --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME" --query 'services[0]')

# Extract the task definition ARN from the service details
TASK_DEFINITION_ARN=$(echo "$SERVICE_DETAILS" | jq -r '.taskDefinition')

# Get the list of running tasks for the service
TASK_ARNS=$(aws ecs list-tasks --cluster "$CLUSTER_NAME" --service-name "$SERVICE_NAME" --desired-status RUNNING --query 'taskArns[*]' --output text)

# Force a new deployment for the service
aws ecs update-service --cluster "$CLUSTER_NAME" --service "$SERVICE_NAME" --force-new-deployment

echo "Forced a new deployment for service $SERVICE_NAME"
echo "Task Definition ARN: $TASK_DEFINITION_ARN"
echo "Running Tasks:"
echo "$TASK_ARNS"