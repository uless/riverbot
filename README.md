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



```
1) Bootstrap CDK
2) cdk deploy cdk-ecr-stack
3) ./docker_build.sh
4) ./docker_run.sh (to test)
5) ./ecr_auth.sh
6) https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html
----> docker tag
----> docker push
7) build rest of cdk stack
----> cdk deploy '*'