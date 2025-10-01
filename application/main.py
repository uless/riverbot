import uvicorn
import uuid
import secrets
import socket
import httpx
import logging

from typing import Annotated

import mappings.custom_tags as custom_tags

from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from fastapi import Request, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi import WebSocket

from managers.memory_manager import MemoryManager
from managers.dynamodb_manager import DynamoDBManager
from managers.chroma_manager import ChromaManager
from managers.s3_manager import S3Manager

from adapters.claude import BedrockClaudeAdapter
from adapters.openai import OpenAIAdapter

from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from starlette.middleware.sessions import SessionMiddleware
from starlette.websockets import WebSocketState
from langdetect import detect, DetectorFactory

import asyncio

from dotenv import load_dotenv

import os
import json
import datetime
from starlette.middleware.base import BaseHTTPMiddleware

### Postgres
import psycopg2
from psycopg2.extras import execute_values, DictCursor
import logging

# Configure logging
logging.basicConfig(
    filename='app.log',  # Log to a file named app.log
    level=logging.INFO,  # Log all INFO level messages and above
    format='%(asctime)s - %(levelname)s - %(message)s'  # Include timestamp, log level, and message
)

# Ensure reproducibility by setting the seed
DetectorFactory.seed = 0

def detect_language(text):
    try:
        language = detect(text)
        logging.info(f"Detected language: {language}")
        return language
    except Exception as e:
        logging.error(f"Language detection failed: {str(e)}")
        return None

# Set the cookie name to match the one configured in the CDK
COOKIE_NAME = "WATERBOT"

class SetCookieMiddleware(BaseHTTPMiddleware):
    def __init__(self,app,client_cookie_disabled_uuid=None):
        super().__init__(app)
        self.client_cookie_disabled_uuid = client_cookie_disabled_uuid

    
    async def dispatch(self, request: Request, call_next):
        # store session ID in memory if we are in situation where client has cookies disabled.
        session_value = request.cookies.get(COOKIE_NAME) or self.client_cookie_disabled_uuid or str(uuid.uuid4())
        self.client_cookie_disabled_uuid=session_value
    
        request.state.client_cookie_disabled_uuid = "COOKIE_DISABLED."+session_value

        response = await call_next(request)
        # Set the application cookie in the response headers
        response.set_cookie(
            key=COOKIE_NAME,
            value=session_value,  # You can set any value you want
            max_age=7200,  # Cookie expiration time in seconds (1 hour in this example)
            httponly=True,  # Set to True for better security
            samesite="Strict"  # Strict mode to prevent CSRF attacks
        )
        

        return response

class MyEventHandler(TranscriptResultStreamHandler):
    def __init__(self, output_stream, websocket):
        super().__init__(output_stream)
        self.websocket = websocket
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
        self.base_url = f"http://{websocket.base_url.hostname}:{websocket.base_url.port if websocket.base_url.port else ''}"
        
        print("printing the base url inside event handler: ", self.base_url)
        self.api_endpoints = {
            "tell me more": str(self.base_url) + "/chat_detailed_api",
            "next steps": str(self.base_url) +"/chat_actionItems_api",
            "sources": str(self.base_url) + "/chat_sources_api",
        }
        self.transcribed_text = None
        self.designated_action = None

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        for result in results:
            if not result.is_partial:
                for alt in result.alternatives:
                    logging.info(f"Handling full transcript: {alt.transcript}")
                    api_url = self.determine_api_url(alt.transcript.strip().lower())
                    # print(api_url)
                    self.transcribed_text = alt.transcript
                    self.designated_action = api_url
                    form_data = {'user_query': alt.transcript}
                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.post(api_url, data=form_data)
                            response.raise_for_status()  # This will raise an exception for HTTP error responses
                            await self.send_responses(alt.transcript, response)
                    except (httpx.HTTPError, httpx.RequestError) as e:
                        logging.error(f"Failed to post to chat API: {e}")
                        await self.websocket.send_json({'type': 'error', 'details': str(e)})

    def determine_api_url(self, transcript):
        # Exact matches for specific requests, considering an optional period
        for key, url in self.api_endpoints.items():
            if transcript == key or transcript == key + '.':
                return url
        return str(self.base_url) + "/chat_api"  # Default API if no exact match is found

    async def send_responses(self, user_transcript, api_response):
        await self.websocket.send_json({
            'type': 'user',
            'transcript': user_transcript
        })
        logging.info("Sent user message to client.")
        api_response_data = api_response.json()
        await self.websocket.send_json({
            'type': 'bot',
            'response': api_response_data['resp'],
            'messageID': api_response_data['msgID']
        })
        logging.info("Sent bot response to client.")


# Take environment variables from .env
load_dotenv(override=True)  

# FastaAPI startup
app = FastAPI()
security = HTTPBasic()
templates = Jinja2Templates(directory='templates')
app.mount("/static", StaticFiles(directory="static"), name="static")

# Middleware management
secret_key=secrets.token_urlsafe(32)
app.add_middleware(SetCookieMiddleware)
app.add_middleware(SessionMiddleware, secret_key=secret_key)

MESSAGES_TABLE=os.getenv("MESSAGES_TABLE")
TRANSCRIPT_BUCKET_NAME=os.getenv("TRANSCRIPT_BUCKET_NAME")

# adapter choices
ADAPTERS = {
    "claude.haiku":BedrockClaudeAdapter("anthropic.claude-3-haiku-20240307-v1:0"),
    "claude.":BedrockClaudeAdapter("anthropic.claude-3-sonnet-20240229-v1:0"),
    "openai-gpt4.1":OpenAIAdapter("gpt-4.1")
}

# Set adapter choice
# llm_adapter=ADAPTERS["claude.haiku"]
llm_adapter=ADAPTERS["openai-gpt4.1"]



embeddings = llm_adapter.get_embeddings()



# Manager classes
memory = MemoryManager()  # Assuming you have a MemoryManager class
datastore = DynamoDBManager(messages_table=MESSAGES_TABLE)
knowledge_base = ChromaManager(persist_directory="docs/chroma/", embedding_function=embeddings)
knowledge_base_spanish = ChromaManager(persist_directory="docs/chroma/spanish", embedding_function=embeddings)
s3_manager = S3Manager(bucket_name=TRANSCRIPT_BUCKET_NAME)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request,):
    # hostname = socket.gethostname()
    # ip_address = socket.gethostbyname(hostname)

    context = {
        "request": request,
        # "hostname": hostname,
        # "ip_address": ip_address
    }

    return templates.TemplateResponse("splashScreen.html", context )

@app.get("/waterbot", response_class=HTMLResponse)
async def home(request: Request,):
    # hostname = socket.gethostname()
    # ip_address = socket.gethostbyname(hostname)

    context = {
        "request": request,
        # "hostname": hostname,
        # "ip_address": ip_address
    }

    return templates.TemplateResponse("index.html", context )
# for waterBot html

@app.get("/aboutwaterbot", response_class=HTMLResponse)
async def home(request: Request,):
    # hostname = socket.gethostname()
    # ip_address = socket.gethostbyname(hostname)

    context = {
        "request": request,
        # "hostname": hostname,
        # "ip_address": ip_address
    }

    return templates.TemplateResponse("aboutWaterbot.html", context )

@app.get("/Spanish_Translation_2.0.1.html", response_class=HTMLResponse)
async def home(request: Request,):
    # hostname = socket.gethostname()
    # ip_address = socket.gethostbyname(hostname)

    context = {
        "request": request,
        # "hostname": hostname,
        # "ip_address": ip_address
    }

    return templates.TemplateResponse("spanish.html", context )

@app.get("/riverbot", response_class=HTMLResponse)
async def riverbot(request: Request,):
    
    context = {
        "request": request,
    }
    return templates.TemplateResponse("riverbot.html", context)




# Database connection variables
db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")

# Database connection parameters
DB_PARAMS = {
    "dbname": db_name,
    "user": db_user,
    "password": db_password,
    "host": db_host,
    "port": "5432"
}


# Authentication function
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = "admin"
    correct_password = "supersecurepassword"
    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return credentials.username

# Secure endpoint
@app.get("/messages")
def get_messages(user: str = Depends(authenticate)):  # Requires authentication
    """Read the messages from the PostgreSQL database"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT * FROM messages ORDER BY created_at DESC LIMIT 100;")
        messages = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convert datetime objects to strings
        def convert_datetime_to_str(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()  # Convert datetime to ISO format string
            return obj

        # Convert each message (dict) to a JSON-serializable format
        serializable_messages = []
        for msg in messages:
            msg_dict = dict(msg)
            serializable_messages.append({k: convert_datetime_to_str(v) for k, v in msg_dict.items()})

        return json.dumps(serializable_messages)
    except Exception as e:
        logging.error("Database Error: %s", e, exc_info=True)

def log_message(session_uuid, msg_id, user_query, response_content, source):
    """Insert a message into the PostgreSQL database."""
    try:
        source_json = json.dumps(source)  # Convert source (list/dict) to a JSON string
        msg_id_str = str(msg_id)  # Ensure msg_id is a string

        # Connect to PostgreSQL
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()

        # Insert the message
        query = """
        INSERT INTO messages (session_uuid, msg_id, user_query, response_content, source, created_at) 
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        # Execute query
        cursor.execute(query, (session_uuid, msg_id_str, user_query, response_content, source_json, datetime.datetime.utcnow()))

        # Commit and close
        conn.commit()
        cursor.close()
        conn.close()
        logging.info("Message logged successfully in PostgreSQL.")

    except Exception as e:
        logging.error("Database Error: %s", e, exc_info=True)

@app.websocket("/transcribe")
async def transcribe(websocket: WebSocket):
    await websocket.accept()
    # print("Headers received during handshake:", websocket.request_headers)
    # print("Response headers sent:", websocket.response_headers)
    client = TranscribeStreamingClient(region="us-east-1")
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="ogg-opus",
    )

    async def receive_audio():
        try:
            while True:
                data = await websocket.receive()
                # print("In receive audio fn:",data)
                if data.get("text") == '{"event":"close"}':
                    print("Closing WebSocket connection")
                    await stream.input_stream.end_stream()
                    break
                elif data.get("bytes"):
                    # Send the audio data to the Amazon Transcribe service
                    await stream.input_stream.send_audio_event(audio_chunk=data.get("bytes"))
        except Exception as e:
            print("WebSocket disconnected unexpectedly (receive audio after while)", str(e))
            await stream.input_stream.end_stream()

    handler = MyEventHandler(stream.output_stream, websocket)

    try:
        await asyncio.gather(receive_audio(), handler.handle_events())
    except Exception as e:
        print("WebSocket disconnected unexpectedly (receive audio after handler):", str(e))
    finally:
        print("Closing WebSocket connection")
        await websocket.close()
        print(websocket.headers)

@app.post("/session-transcript")
async def session_transcript_post(request: Request):
    # Get the session UUID from the cookie
    session_uuid = request.cookies.get(COOKIE_NAME) or request.state.client_cookie_disabled_uuid

    # Get all session history
    session_history = await memory.get_session_history_all(session_uuid)
    
    if not isinstance(session_history, (dict, list)):
        raise HTTPException(status_code=500, detail="Session history is not serializable")

    # Generate a unique filename for the S3 object
    filename = f"{session_uuid}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    object_key = f"session-transcript/{filename}"
    
    # Convert session history to plain text format
    session_text = ""
    for entry in session_history:
        session_text += f"Role: {entry['role']}\nContent: {entry['content']}\n\n"

    # Upload the session history to S3 as plain text
    # print(session_text)  # Print for debugging (optional)
    # print(TRANSCRIPT_BUCKET_NAME)  # Print for debugging (optional)
    await s3_manager.upload(key=object_key, body=session_text)

    # Generate a presigned URL for the S3 object
    url = await s3_manager.generate_presigned(key=object_key)

    return {'presigned_url': url}


# Route to handle ratings
@app.post('/submit_rating_api')
async def submit_rating_api_post(
        request: Request,
        message_id: str = Form(..., description="The ID of the message"),
        reaction: str = Form(None, description="Optional reaction to the message"),
        userComment: str = Form(None, description="Optional user comment")
    ):

    session_uuid = request.cookies.get(COOKIE_NAME) or request.state.client_cookie_disabled_uuid

    counter_uuid=await memory.get_message_count_uuid(session_uuid)
    message_uuid_combo=counter_uuid+"."+message_id
    await datastore.update_rating_fields(
        session_uuid=session_uuid,
        message_id=message_uuid_combo,
        reaction=reaction,
        userComment=userComment
    )
    

# Riverbot-specific sources API
@app.post('/riverbot_chat_sources_api')
async def riverbot_chat_sources_post(request: Request, background_tasks:BackgroundTasks):
    
    session_uuid = request.cookies.get(COOKIE_NAME) or request.state.client_cookie_disabled_uuid

    docs=await memory.get_latest_memory( session_id=session_uuid, read="documents")
    user_query=await memory.get_latest_memory( session_id=session_uuid, read="content")
    sources=await memory.get_latest_memory( session_id=session_uuid, read="sources")
    language = detect_language(user_query)

    memory_payload={
        "documents":docs,
        "sources":sources
    }
    
    formatted_source_list=await memory.format_sources_as_html(source_list=sources)

    generated_user_query = f'{custom_tags.tags["SOURCE_REQUEST"][0]}Provide me sources.{custom_tags.tags["SOURCE_REQUEST"][1]}'
    generated_user_query += f'{custom_tags.tags["OG_QUERY"][0]}{user_query}{custom_tags.tags["OG_QUERY"][1]}'

    bot_response=formatted_source_list

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"user","content":generated_user_query},
        source_list=memory_payload
    )
    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"assistant","content":bot_response},
        source_list=memory_payload
    )
    await memory.increment_message_count(session_uuid)

    # We do not include sources as this message is the actual sources; no AI generation involved.
    background_tasks.add_task(log_message,
        session_uuid=session_uuid,
        msg_id=await memory.get_message_count_uuid_combo(session_uuid), 
        user_query=generated_user_query, 
        response_content=bot_response,
        source=[] 
    )

    return {
        "resp":bot_response,
        "msgID": await memory.get_message_count(session_uuid)
    }

# User wants to see sources of previous message
@app.post('/chat_sources_api')
async def chat_sources_post(request: Request, background_tasks:BackgroundTasks):

    session_uuid = request.cookies.get(COOKIE_NAME) or request.state.client_cookie_disabled_uuid

    docs=await memory.get_latest_memory( session_id=session_uuid, read="documents")
    user_query=await memory.get_latest_memory( session_id=session_uuid, read="content")
    sources=await memory.get_latest_memory( session_id=session_uuid, read="sources")
    language = detect_language(user_query)

    memory_payload={
        "documents":docs,
        "sources":sources
    }
    
    formatted_source_list=await memory.format_sources_as_html(source_list=sources)

    generated_user_query = f'{custom_tags.tags["SOURCE_REQUEST"][0]}Provide me sources.{custom_tags.tags["SOURCE_REQUEST"][1]}'
    generated_user_query += f'{custom_tags.tags["OG_QUERY"][0]}{user_query}{custom_tags.tags["OG_QUERY"][1]}'

    bot_response=formatted_source_list

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"user","content":generated_user_query},
        source_list=memory_payload
    )
    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"assistant","content":bot_response},
        source_list=memory_payload
    )
    await memory.increment_message_count(session_uuid)

    # We do not include sources as this message is the actual sources; no AI generation involved.
    background_tasks.add_task(log_message,
        session_uuid=session_uuid,
        msg_id=await memory.get_message_count_uuid_combo(session_uuid), 
        user_query=generated_user_query, 
        response_content=bot_response,
        source=[] 
    )

    return {
        "resp":bot_response,
        "msgID": await memory.get_message_count(session_uuid)
    }
    

# Riverbot-specific action items API
@app.post('/riverbot_chat_actionItems_api')
async def riverbot_chat_action_items_api_post(request: Request, background_tasks:BackgroundTasks):
  
    session_uuid = request.cookies.get(COOKIE_NAME) or request.state.client_cookie_disabled_uuid

    docs=await memory.get_latest_memory( session_id=session_uuid, read="documents")
    sources=await memory.get_latest_memory( session_id=session_uuid, read="sources")

    memory_payload={
        "documents":docs,
        "sources":sources
    }

    user_query=await memory.get_latest_memory( session_id=session_uuid, read="content",travel=-2)
    bot_response=await memory.get_latest_memory( session_id=session_uuid, read="content")
    
    language = detect_language(user_query)
    
    if language == 'es':
        # print("Inside spanish chromaDB")
        doc_content_str = await knowledge_base_spanish.knowledge_to_string({"documents":docs})     
    else:
        # print("Inside english chromaDB")
        doc_content_str = await knowledge_base.knowledge_to_string({"documents":docs})

    llm_body=await llm_adapter.get_llm_nextsteps_body( kb_data=doc_content_str,user_query=user_query,bot_response=bot_response )
    response_content = await llm_adapter.generate_response(llm_body=llm_body)

    generated_user_query = f'{custom_tags.tags["NEXTSTEPS_REQUEST"][0]}Provide me the action items{custom_tags.tags["NEXTSTEPS_REQUEST"][1]}'
    generated_user_query += f'{custom_tags.tags["OG_QUERY"][0]}{user_query}{custom_tags.tags["OG_QUERY"][1]}'

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"user","content":generated_user_query},
        source_list=[]
    )
    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"assistant","content":response_content},
        source_list=memory_payload
    )
    await memory.increment_message_count(session_uuid)

    background_tasks.add_task(log_message,
        session_uuid=session_uuid,
        msg_id=await memory.get_message_count_uuid_combo(session_uuid), 
        user_query=generated_user_query, 
        response_content=response_content,
        source=sources
    )

    return {
        "resp":response_content,
        "msgID": await memory.increment_message_count(session_uuid)
    }

# Route to handle next steps interactions
@app.post('/chat_actionItems_api')
async def chat_action_items_api_post(request: Request, background_tasks:BackgroundTasks):

    session_uuid = request.cookies.get(COOKIE_NAME) or request.state.client_cookie_disabled_uuid

    docs=await memory.get_latest_memory( session_id=session_uuid, read="documents")
    sources=await memory.get_latest_memory( session_id=session_uuid, read="sources")

    memory_payload={
        "documents":docs,
        "sources":sources
    }


    user_query=await memory.get_latest_memory( session_id=session_uuid, read="content",travel=-2)
    bot_response=await memory.get_latest_memory( session_id=session_uuid, read="content")
    
    language = detect_language(user_query)
    
    if language == 'es':
        # print("Inside spanish chromaDB")
        doc_content_str = await knowledge_base_spanish.knowledge_to_string({"documents":docs})     
    else:
        # print("Inside english chromaDB")
        doc_content_str = await knowledge_base.knowledge_to_string({"documents":docs})

    llm_body=await llm_adapter.get_llm_nextsteps_body( kb_data=doc_content_str,user_query=user_query,bot_response=bot_response )
    response_content = await llm_adapter.generate_response(llm_body=llm_body)

    generated_user_query = f'{custom_tags.tags["NEXTSTEPS_REQUEST"][0]}Provide me the action items{custom_tags.tags["NEXTSTEPS_REQUEST"][1]}'
    generated_user_query += f'{custom_tags.tags["OG_QUERY"][0]}{user_query}{custom_tags.tags["OG_QUERY"][1]}'

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"user","content":generated_user_query},
        source_list=[]
    )
    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"assistant","content":response_content},
        source_list=memory_payload
    )
    await memory.increment_message_count(session_uuid)

    background_tasks.add_task(log_message,
        session_uuid=session_uuid,
        msg_id=await memory.get_message_count_uuid_combo(session_uuid), 
        user_query=generated_user_query, 
        response_content=response_content,
        source=sources
    )


    return {
        "resp":response_content,
        "msgID": await memory.increment_message_count(session_uuid)
    }

# Riverbot-specific detailed API
@app.post('/riverbot_chat_detailed_api')
async def riverbot_chat_detailed_api_post(request: Request, background_tasks:BackgroundTasks):
   
    session_uuid = request.cookies.get(COOKIE_NAME) or request.state.client_cookie_disabled_uuid

    docs=await memory.get_latest_memory( session_id=session_uuid, read="documents")
    sources=await memory.get_latest_memory( session_id=session_uuid, read="sources")

    memory_payload={
        "documents":docs,
        "sources":sources
    }

    user_query=await memory.get_latest_memory( session_id=session_uuid, read="content",travel=-2)
    bot_response=await memory.get_latest_memory( session_id=session_uuid, read="content")
    
    language = detect_language(user_query)

    if language == 'es':
        # print("Inside spanish chromaDB")
        doc_content_str = await knowledge_base_spanish.knowledge_to_string({"documents":docs})
    else:
        # print("Inside enlgish chromaDB")
        doc_content_str = await knowledge_base.knowledge_to_string({"documents":docs})

    llm_body=await llm_adapter.get_llm_detailed_body( kb_data=doc_content_str,user_query=user_query,bot_response=bot_response )
    response_content = await llm_adapter.generate_response(llm_body=llm_body)

    generated_user_query = f'{custom_tags.tags["MOREDETAIL_REQUEST"][0]}Provide me a more detailed response.{custom_tags.tags["MOREDETAIL_REQUEST"][1]}'
    generated_user_query += f'{custom_tags.tags["OG_QUERY"][0]}{user_query}{custom_tags.tags["OG_QUERY"][1]}'

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"user","content":generated_user_query},
        source_list=[]
    )
    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"assistant","content":response_content},
        source_list=memory_payload
    )
    await memory.increment_message_count(session_uuid)

    background_tasks.add_task(log_message,
        session_uuid=session_uuid,
        msg_id=await memory.get_message_count_uuid_combo(session_uuid), 
        user_query=generated_user_query, 
        response_content=response_content,
        source=sources
    )

    return {
        "resp":response_content,
        "msgID": await memory.get_message_count(session_uuid)
    }

# Route to handle next steps interactions
@app.post('/chat_detailed_api')
async def chat_detailed_api_post(request: Request, background_tasks:BackgroundTasks):
    session_uuid = request.cookies.get(COOKIE_NAME) or request.state.client_cookie_disabled_uuid

    docs=await memory.get_latest_memory( session_id=session_uuid, read="documents")
    sources=await memory.get_latest_memory( session_id=session_uuid, read="sources")

    memory_payload={
        "documents":docs,
        "sources":sources
    }

    user_query=await memory.get_latest_memory( session_id=session_uuid, read="content",travel=-2)
    bot_response=await memory.get_latest_memory( session_id=session_uuid, read="content")
    
    language = detect_language(user_query)

    if language == 'es':
        # print("Inside spanish chromaDB")
        doc_content_str = await knowledge_base_spanish.knowledge_to_string({"documents":docs})
    else:
        # print("Inside enlgish chromaDB")
        doc_content_str = await knowledge_base.knowledge_to_string({"documents":docs})

    llm_body=await llm_adapter.get_llm_detailed_body( kb_data=doc_content_str,user_query=user_query,bot_response=bot_response )
    response_content = await llm_adapter.generate_response(llm_body=llm_body)

    generated_user_query = f'{custom_tags.tags["MOREDETAIL_REQUEST"][0]}Provide me a more detailed response.{custom_tags.tags["MOREDETAIL_REQUEST"][1]}'
    generated_user_query += f'{custom_tags.tags["OG_QUERY"][0]}{user_query}{custom_tags.tags["OG_QUERY"][1]}'

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"user","content":generated_user_query},
        source_list=[]
    )
    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"assistant","content":response_content},
        source_list=memory_payload
    )
    await memory.increment_message_count(session_uuid)


    background_tasks.add_task(log_message,
        session_uuid=session_uuid,
        msg_id=await memory.get_message_count_uuid_combo(session_uuid), 
        user_query=generated_user_query, 
        response_content=response_content,
        source=sources
    )


    return {
        "resp":response_content,
        "msgID": await memory.get_message_count(session_uuid)
    }

# Route to handle chat interactions
@app.post('/chat_api')
async def chat_api_post(request: Request, user_query: Annotated[str, Form()], background_tasks:BackgroundTasks ):
    user_query=user_query

    session_uuid = request.cookies.get(COOKIE_NAME) or request.state.client_cookie_disabled_uuid

    await memory.create_session(session_uuid)
        
    moderation_result,intent_result = await llm_adapter.safety_checks(user_query)

    user_intent=1
    prompt_injection=1
    unrelated_topic=1
    not_handled="I am sorry, your request cannot be handled."
    try:
        data = json.loads(intent_result)
        user_intent=data["user_intent"]
        prompt_injection=data["prompt_injection"]
        unrelated_topic=data["unrelated_topic"]
    except Exception as e:
        print(intent_result)
        print("ERROR", str(e))


    if( moderation_result or (prompt_injection or unrelated_topic)):
        response_content= "I am sorry, your request is inappropriate and I cannot answer it." if moderation_result else not_handled

        await memory.increment_message_count(session_uuid)

        generated_user_query = f'{custom_tags.tags["SECURITY_CHECK"][0]}{data}{custom_tags.tags["SECURITY_CHECK"][1]}'
        generated_user_query += f'{custom_tags.tags["OG_QUERY"][0]}{user_query}{custom_tags.tags["OG_QUERY"][1]}'

        background_tasks.add_task(log_message,
            session_uuid=session_uuid,
            msg_id=await memory.get_message_count_uuid_combo(session_uuid), 
            user_query=generated_user_query, 
            response_content=response_content,
            source=[]
        )

        return {
            "resp":response_content,
            "msgID": await memory.get_message_count(session_uuid)
        }

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"user","content":user_query},
        source_list=[]
    )
    
    language = detect_language(user_query)
    
    if language == 'es':
        # print("Inside spanish chromaDB")
        docs = await knowledge_base_spanish.ann_search(user_query)
        doc_content_str = await knowledge_base_spanish.knowledge_to_string(docs)
    else:
        #  print("Inside english chromaDB")
         docs = await knowledge_base.ann_search(user_query)
         doc_content_str = await knowledge_base.knowledge_to_string(docs)
    
    # Use default system prompt for index.html
    logging.info("Using default system prompt for index.html")
    
    llm_body = await llm_adapter.get_llm_body( 
        chat_history=await memory.get_session_history_all(session_uuid), 
        kb_data=doc_content_str,
        temperature=.5,
        max_tokens=500,
        endpoint_type="default" )

    response_content = await llm_adapter.generate_response(llm_body=llm_body)

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"assistant","content":response_content},
        source_list=docs
    )

    await memory.increment_message_count(session_uuid)
    # Log the message to postgres
    background_tasks.add_task(log_message,
        session_uuid=session_uuid,
        msg_id=await memory.get_message_count_uuid_combo(session_uuid), 
        user_query=user_query, 
        response_content=response_content,
        source=docs["sources"]
    )

    return {
        "resp": response_content.replace('\n\n', '</p><p>').replace('\n', '<br>'),
        "msgID": await memory.get_message_count(session_uuid)
    }

# Route to handle riverbot chat interactions
@app.post('/riverbot_chat_api')
async def riverbot_chat_api_post(request: Request, user_query: Annotated[str, Form()], background_tasks:BackgroundTasks ):
    
    user_query=user_query

    session_uuid = request.cookies.get(COOKIE_NAME) or request.state.client_cookie_disabled_uuid

    await memory.create_session(session_uuid)
        
    moderation_result,intent_result = await llm_adapter.safety_checks(user_query)

    user_intent=1
    prompt_injection=1
    unrelated_topic=1
    not_handled="I am sorry, your request cannot be handled."
    try:
        data = json.loads(intent_result)
        user_intent=data["user_intent"]
        prompt_injection=data["prompt_injection"]
        unrelated_topic=data["unrelated_topic"]
    except Exception as e:
        print(intent_result)
        print("ERROR", str(e))

    if( moderation_result or (prompt_injection or unrelated_topic)):
        response_content= "I am sorry, your request is inappropriate and I cannot answer it." if moderation_result else not_handled

        await memory.increment_message_count(session_uuid)

        generated_user_query = f'{custom_tags.tags["SECURITY_CHECK"][0]}{data}{custom_tags.tags["SECURITY_CHECK"][1]}'
        generated_user_query += f'{custom_tags.tags["OG_QUERY"][0]}{user_query}{custom_tags.tags["OG_QUERY"][1]}'

        background_tasks.add_task(log_message,
            session_uuid=session_uuid,
            msg_id=await memory.get_message_count_uuid_combo(session_uuid), 
            user_query=generated_user_query, 
            response_content=response_content,
            source=[]
        )

        return {
            "resp":response_content,
            "msgID": await memory.get_message_count(session_uuid)
        }

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"user","content":user_query},
        source_list=[]
    )
    
    language = detect_language(user_query)
    
    if language == 'es':
        # print("Inside spanish chromaDB")
        docs = await knowledge_base_spanish.ann_search(user_query)
        doc_content_str = await knowledge_base_spanish.knowledge_to_string(docs)
    else:
        #  print("Inside english chromaDB")
         docs = await knowledge_base.ann_search(user_query)
         doc_content_str = await knowledge_base.knowledge_to_string(docs)
    
    # Use riverbot system prompt
    logging.info("Using riverbot system prompt")
    
    llm_body = await llm_adapter.get_llm_body( 
        chat_history=await memory.get_session_history_all(session_uuid), 
        kb_data=doc_content_str,
        temperature=.5,
        max_tokens=500,
        endpoint_type="riverbot" )

    response_content = await llm_adapter.generate_response(llm_body=llm_body)

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"assistant","content":response_content},
        source_list=docs
    )

    await memory.increment_message_count(session_uuid)
    # Log the message to postgres
    background_tasks.add_task(log_message,
        session_uuid=session_uuid,
        msg_id=await memory.get_message_count_uuid_combo(session_uuid), 
        user_query=user_query, 
        response_content=response_content,
        source=docs["sources"]
    )

    return {
        "resp": response_content.replace('\n\n', '</p><p>').replace('\n', '<br>'),
        "msgID": await memory.get_message_count(session_uuid)
    }

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)