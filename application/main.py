from typing import Annotated
from fastapi import FastAPI, Form
import uvicorn
import uuid
import secrets
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from memory_manager import MemoryManager

from langchain_community.vectorstores import Chroma



from adapters.claude import BedrockClaudeAdapter
from adapters.openai import OpenAIAdapter

from dotenv import load_dotenv

import os

load_dotenv()  # take environment variables from .env.

app = FastAPI()
secret_key=secrets.token_urlsafe(32)
app.add_middleware(SessionMiddleware, secret_key=secret_key)

message_count = {}
memory = MemoryManager()  # Assuming you have a MemoryManager class


templates = Jinja2Templates(directory='templates')
app.mount("/static", StaticFiles(directory="static"), name="static")



#Adapter choices
adapter_claude_haiku=BedrockClaudeAdapter("anthropic.claude-3-haiku-20240307-v1:0")
adapter_claude_sonnet=BedrockClaudeAdapter("anthropic.claude-3-sonnet-20240229-v1:0")
adapter_openai=OpenAIAdapter("gpt-3.5-turbo")

#set adapter
ADAPTER=adapter_claude_haiku

embeddings = ADAPTER.get_embeddings()
vectordb = Chroma(persist_directory="docs/chroma/", embedding_function=embeddings)



@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Route to handle next steps interactions
@app.post('/next_steps_api')
async def next_steps_api_post(request: Request):
    pass

# Route to handle chat interactions
@app.post('/chat_api')
async def chat_api_post(request: Request, user_query: Annotated[str, Form()] ):
    user_query=user_query

    session = request.session

    session_uuid = session.get("uuid")
    if session_uuid is None:
        session_uuid = str(uuid.uuid4())
        session["uuid"] = session_uuid
        message_count[session_uuid] = 0
        memory.create_session(session_uuid)

    if session_uuid not in message_count:
        message_count[session_uuid] = 0
        
    moderation_result,intent_result = await ADAPTER.safety_checks(user_query)
    if( moderation_result or intent_result != "<b>SUCCESS</b>"):
        msg= "I am sorry, your request is inappropriate and I cannot answer it." if moderation_result else intent_result
        return {
            "resp":msg,
            "msgID": message_count[session['uuid']]
        }

    docs = vectordb.similarity_search(user_query)
    qdocs1 = " ".join([docs[i].page_content for i in range(len(docs))])


    memory.add_message_to_session( session_id=session_uuid, message={"role":"user","content":user_query} )
    llm_body = await ADAPTER.get_llm_body( 
        chat_history=memory.get_session_history(session_uuid), 
        kb_data=qdocs1,
        temperature=.5,
        max_tokens=500 )

    response_content = await ADAPTER.generate_response(llm_body=llm_body)

    memory.add_message_to_session( session_id=session_uuid, message={"role":"assistant","content":response_content} )
    message_count[session['uuid']] += 1

    return {
        "resp":response_content,
        "msgID": message_count[session['uuid']]
    }

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)