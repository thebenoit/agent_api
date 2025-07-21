# server.py
import os
import uvicorn
from agents.ian import graph
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
from langchain_core.messages import HumanMessage, AIMessage

app = FastAPI()

class ChatRequest(BaseModel):
    system_prompt:str
    message: str
    chat_history: Optional[List[dict]] = None

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
    
    response = await graph.ainvoke(input_data,config)
    
    return {"response": response}

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