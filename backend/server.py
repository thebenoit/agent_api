# server.py
import os
import uvicorn
from agents.ian import graph
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
from langchain_core.messages import HumanMessage, AIMessage
from fastapi.responses import StreamingResponse

app = FastAPI()


class ChatRequest(BaseModel):
    system_prompt: str
    message: str
    chat_history: Optional[List[dict]] = None


class chatResponse(BaseModel):
    response: str
    response_type: str
    listings: Optional[List[dict]] = None
    map_data: Optional[dict] = None


# Route de santé (optionnelle, LangGraph a déjà ses endpoints)
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/chat")
async def chat(request: ChatRequest):
    # get the user message
    user_message = request.message

    # Initialize chat history if not provided
    if request.chat_history is None:
        chat_history = []
    else:
        chat_history = request.chat_history

    # get the chat history
    chat_history.append(HumanMessage(content=user_message))
    input_data = {
        "messages": chat_history,
    }
    config = {"configurable": {"thread_id": "123"}}

    response = await graph.ainvoke(input_data, config)

    return {"response": response}

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        user_message = request.message
        chat_history = request.chat_history or []
        #encapsule message dans un objet HumanMessage
        chat_history.append(HumanMessage(content=user_message))
        
        input_data = {"messages": chat_history}
        config ={"configurable": {"thread_id":"123"}}
        
        #for each event in graph.stream, we get the last message
        for event in graph.stream(input_data,config):
           for value in event.values():       
               if "message" in value:
                   message = value["message"][-1]
                   #permet de streamer la réponse
                   yield f"data: {json.dumps({'type':'message','content':message.content})}"
        
        return StreaminResponse(generate(), media_type="text/plain")
    

# def main():
#     print("Starting LangGraph server...")
#     port = int(os.getenv("PORT", "2024"))
#     uvicorn.run(
#         app,
#         host="0.0.0.0",
#         port=port,
#         reload=True,
#     )

# if __name__ == "__main__":
#     main()
