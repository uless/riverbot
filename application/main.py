import uvicorn
import uuid
import secrets

from typing import Annotated

from fastapi import FastAPI, BackgroundTasks
from fastapi import Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from starlette.middleware.sessions import SessionMiddleware

from managers.memory_manager import MemoryManager
from managers.dynamodb_manager import DynamoDBManager
from managers.chroma_manager import ChromaManager

from adapters.claude import BedrockClaudeAdapter
from adapters.openai import OpenAIAdapter

from dotenv import load_dotenv

import os

# Take environment variables from .env
load_dotenv()  

# FastaAPI startup
app = FastAPI()
templates = Jinja2Templates(directory='templates')
app.mount("/static", StaticFiles(directory="static"), name="static")

# Middleware management
secret_key=secrets.token_urlsafe(32)
app.add_middleware(SessionMiddleware, secret_key=secret_key)

MESSAGES_TABLE=os.getenv("MESSAGES_TABLE")
# adapter choices
ADAPTERS = {
    "claude.haiku":BedrockClaudeAdapter("anthropic.claude-3-haiku-20240307-v1:0"),
    "claude.sonnet":BedrockClaudeAdapter("anthropic.claude-3-sonnet-20240229-v1:0"),
    "openai-gpt3.5":OpenAIAdapter("gpt-3.5-turbo")
}

# Set adapter choice
llm_adapter=ADAPTERS["claude.haiku"]
embeddings = llm_adapter.get_embeddings()


# Manager classes
memory = MemoryManager()  # Assuming you have a MemoryManager class
datastore = DynamoDBManager(messages_table=MESSAGES_TABLE)
vectordb = ChromaManager(persist_directory="docs/chroma/", embedding_function=embeddings)

message_count = {}



@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# User wants to see sources of previous message
@app.post('/chat_sources_api')
async def chat_sources(request: Request):
    session = request.session

    user_query,source_list=await memory.get_latest_source_list( session_id=session["uuid"] )
    formatted_source_list=await memory.format_sources_as_html(source_list=source_list)

    print(source_list)
    user_query = "<SOURCE_REQUEST>"+user_query+"</SOURCE_REQUEST>"
    print(user_query)
    bot_response=formatted_source_list
    print(bot_response)

    await memory.add_message_to_session( 
        session_id=session["uuid"], 
        message={"role":"user","content":user_query},
        source_list=[]
    )
    await memory.add_message_to_session( 
        session_id=session["uuid"], 
        message={"role":"assistant","content":bot_response},
        source_list=[]
    )
    session["message_count"]+=1

    return {
        "resp":bot_response,
        "msgID": session["message_count"]
    }
    

# Route to handle next steps interactions
@app.post('/next_steps_api')
async def next_steps_api_post(request: Request):
    pass

# Route to handle chat interactions
@app.post('/chat_api')
async def chat_api_post(request: Request, user_query: Annotated[str, Form()], background_tasks:BackgroundTasks ):
    user_query=user_query

    session = request.session
    session_uuid = session.get("uuid")
    if session_uuid is None:
        session_uuid = str(uuid.uuid4())
        session["uuid"] = session_uuid
        session["message_count"] = 0
        await memory.create_session(session_uuid)
        
    moderation_result,intent_result = await llm_adapter.safety_checks(user_query)
    if( moderation_result or intent_result != "<b>SUCCESS</b>"):
        msg= "I am sorry, your request is inappropriate and I cannot answer it." if moderation_result else intent_result
        return {
            "resp":msg,
            "msgID": session["message_count"]
        }

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"user","content":user_query},
        source_list=[]
    )
    

    docs = await vectordb.similarity_search(user_query)
    doc_content_str = await vectordb.knowledge_to_string(docs)
    
    llm_body = await llm_adapter.get_llm_body( 
        chat_history=await memory.get_session_history_all(session_uuid), 
        kb_data=doc_content_str,
        temperature=.5,
        max_tokens=500 )

    response_content = await llm_adapter.generate_response(llm_body=llm_body)

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"assistant","content":response_content},
        source_list=docs
    )

    session["message_count"]+=1

    source=""
    background_tasks.add_task( datastore.write_msg,
        session_uuid=session_uuid,
        msg_id=session["message_count"], 
        user_query=user_query, 
        response_content=response_content,
        source=source 
    )

    return {
        "resp":response_content,
        "msgID": session["message_count"] 
    }

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)