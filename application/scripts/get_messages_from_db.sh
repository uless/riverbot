#!/bin/bash

# Set AWS variables
REGION="us-west-2"
CLUSTER="water-bot-cluster"
CONTAINER="waterbot-container"
DB_HOST="waterbot-logs.c3usgymgs1y2.us-west-2.rds.amazonaws.com"
DB_USER="postgres"
DB_NAME="waterbot_logs"

# Output file
OUTPUT_FILE="latest_messages.txt"

# Get the latest running ECS task ID dynamically
TASK_ID=$(aws ecs list-tasks --region $REGION --cluster $CLUSTER --desired-status RUNNING --query "taskArns[0]" --output text)

# If no task is found, exit
if [[ -z "$TASK_ID" || "$TASK_ID" == "None" ]]; then
  echo "No running ECS task found. Exiting."
  exit 1
fi

echo "Connecting to ECS Task: $TASK_ID"

# Execute command in the ECS container and save output to file
aws ecs execute-command \
    --region $REGION \
    --cluster $CLUSTER \
    --task $TASK_ID \
    --container $CONTAINER \
    --command "/bin/bash -c 'apt update && apt install -y postgresql-client && psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \"SELECT * FROM messages ORDER BY created_at DESC LIMIT 5;\" > ./latest_messages.txt && cat ./latest_messages.txt'" \
    --interactive | tee "$OUTPUT_FILE"

echo "Latest messages saved to $OUTPUT_FILE"
