import boto3

class DynamoDBHandler():
    def __init__(self, messages_table, *args, **kwargs):
        self.client = boto3.resource('dynamodb')
        self.messages_table=messages_table
        
        super().__init__(*args,**kwargs)
    
    async def write_msg():
        messages_table = self.client.Table(self.messages_table)
        pass