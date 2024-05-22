import boto3
import datetime


class DynamoDBManager():
    def __init__(self, messages_table, *args, **kwargs):
        self.client = boto3.resource('dynamodb')
        self.messages_table=messages_table
        
        super().__init__(*args,**kwargs)
    
    async def write_msg(self, 
                        session_uuid, 
                        msg_id, 
                        user_query, 
                        response_content, 
                        source=None, 
                        rating=None, 
                        comment=None ):
        messages_table = self.client.Table(self.messages_table)

        # Get the current timestamp
        timestamp = datetime.datetime.now()
        # Convert timestamp to ISO 8601 string
        iso_string = timestamp.isoformat()

        # Insert into dynamodb all items
        messages_table.put_item(
            Item={
                'sessionId': session_uuid,
                'timestamp': iso_string,
                'msgId': msg_id,
                'userQuery': user_query,
                'responseContent': response_content,
                'source': source,
                'rating': rating,
                'comment': comment
            }
        )