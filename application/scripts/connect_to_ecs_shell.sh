#!/bin/bash

# Set AWS variables
REGION="us-west-2"
CLUSTER="water-bot-cluster"
CONTAINER="waterbot-container"

# Get the latest running ECS task ID dynamically
TASK_ID=$(aws ecs list-tasks --region $REGION --cluster $CLUSTER --desired-status RUNNING --query "taskArns[0]" --output text)

# If no task is found, exit
if [[ -z "$TASK_ID" || "$TASK_ID" == "None" ]]; then
  echo "No running ECS task found. Exiting."
  exit 1
fi

echo "Connecting to ECS Task: $TASK_ID"

# Start an interactive shell session in the ECS container
aws ecs execute-command \
    --region $REGION \
    --cluster $CLUSTER \
    --task $TASK_ID \
    --container $CONTAINER \
    --interactive \
    --command "/bin/bash"