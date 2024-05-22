_Reference Site: https://waterbot-stream-bda64cf22bc1.herokuapp.com/_

# Note: Additional file in root:  ecr_auth.sh
**Not tracked on github; dynamic based on deploy.**

```bash
#!/bin/sh
aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {act_num}.dkr.ecr.{region}.amazonaws.com/{repo}
```

**Give it run permissions:** `chmod +x ecr_auth.sh`

# Prerequisites

**Grab additional software**
```bash
sudo apt-get install jq
```

**Set your environment variables**
```bash
export AWS_ACCESS_KEY_ID=""
export AWS_SECRET_ACCESS_KEY=""
export AWS_SESSION_TOKEN=""
export OPENAI_API_KEY=""
export SECRET_HEADER_KEY=""
export BASIC_AUTH_SECRET=""
export CLUSTER_NAME=""
export SERVICE_NAME=""
```
_**Note:** You won't know CLUSTER_NAME & SERVICE_NAME until post deployment; these variables are only necessary for fargate_update_cluster.sh script_

# Choice: Run Locally (No Container)
```bash
cd application
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
fastapi dev main.py
````

# Choice: Run Locally (In Container)
```bash
./docker_build.sh
./docker_run.sh
```

# Choice: Deploy to AWS
_**Note:** You will need CDK preqruisites._

_**Reference:**_ https://cdkworkshop.com/
```
1) Bootstrap CDK
2) cdk deploy cdk-ecr-stack
3) ./docker_build.sh
4) ./docker_run.sh (to test)
5) ./ecr_auth.sh
6) https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html
----> docker tag {container_id} {act_id}.dkr.ecr.us-east-1.amazonaws.com/{repo}:latest
----> docker push {act_id}.dkr.ecr.us-east-1.amazonaws.com/{repo}:latest
7) build rest of cdk stack
----> cdk deploy '*'
```

