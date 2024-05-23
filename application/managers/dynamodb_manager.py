import boto3
import datetime

from boto3.dynamodb.conditions import Key, Attr

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

    async def update_rating_fields(self, session_uuid, message_id, reaction, userComment):
        messages_table = self.client.Table(self.messages_table)
        
        if reaction is not None:
            try:
                response = messages_table.update_item(
                    Key={
                        'sessionId': session_uuid,
                        'msgId': message_id
                    },
                    UpdateExpression='SET reaction = :r',
                    ExpressionAttributeValues={
                        ':r': reaction,
                    },
                    ReturnValues='UPDATED_NEW'
                )
                return response
            except Exception as e:
                print(f"Error updating rating fields: {e}")
                return None
            
        if userComment is not None:
            try:
                response = messages_table.update_item(
                    Key={
                        'sessionId': session_uuid,
                        'msgId': message_id
                    },
                    UpdateExpression='SET userComment = :r',
                    ExpressionAttributeValues={
                        ':r': userComment
                    },
                    ReturnValues='UPDATED_NEW'
                )
                return response
            except Exception as e:
                print(f"Error updating rating fields: {e}")
                return None