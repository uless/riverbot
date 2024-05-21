```
cd application
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
fastapi dev main.py
````

For Amazon Bedrock adapters (Claude) during local testing set your security tokens prior to running `fastapi dev main.py`


*Reference Site*

https://waterbot-stream-bda64cf22bc1.herokuapp.com/ 


set env variables
```
export AWS_ACCESS_KEY_ID=""
export AWS_SECRET_ACCESS_KEY=""
export AWS_SESSION_TOKEN=""
export OPENAI_API_KEY=""
export SECRET_HEADER_KEY=""
export BASIC_AUTH_SECRET=""
```

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