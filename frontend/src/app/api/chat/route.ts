import { NextRequest, NextResponse } from 'next/server';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  const { stream, sessionId } = await request.json();

  if(stream){

    const encoder = new TextEncoder();
 
    const stream = new ReadableStream({
      async start(controller) {
        //basic api call to the fastapi server
        const response = await fetch(`${FASTAPI_URL}/chat/stream`, {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({
            ...request.body,
            sessionId: sessionId // Transmettre la sessionId au backend
          })
        });
        //permet de lire les données qui arricent progressivement
        const reader = response.body?.getReader();
        if(reader){
          while(true){
            const {done,value} = await reader.read();
            if(done) break;
            //decode the chunk and enqueue it to the controller
            const chunk = new TextDecoder().decode(value);
            controller.enqueue(encoder.encode(chunk));
          }
        }
        controller.close();
      }
    });

    return new Response(stream,{
      headers: {'Content-Type': 'text/plain; charset=utf-8'}
    })

  }

  try {
    const { message, chatHistory = [], sessionId } = await request.json();

    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    // Préparer l'historique des messages pour FastAPI
    const formattedHistory = chatHistory.map((msg: { sender: string; text: string }) => ({
      role: msg.sender === 'user' ? 'user' : 'assistant',
      content: msg.text
    }));

    const response = await fetch(`${FASTAPI_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        system_prompt: "Tu es un assistant IA utile et bienveillant. Réponds de manière claire et concise en français.",
        message: message,
        chat_history: formattedHistory,
        sessionId: sessionId // Inclure la sessionId dans la requête
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Erreur de communication avec le serveur');
    }

    // Extraire le contenu de la réponse de LangGraph
    let responseText = "Désolé, je n'ai pas pu générer une réponse.";
    
    if (data.response) {
      // Si c'est un objet avec des messages
      if (data.response.messages && Array.isArray(data.response.messages)) {
        // Prendre le dernier message de l'assistant
        const lastMessage = data.response.messages[data.response.messages.length - 1];
        if (lastMessage && lastMessage.content) {
          responseText = lastMessage.content;
        }
      }
      // Si c'est directement une chaîne
      else if (typeof data.response === 'string') {
        responseText = data.response;
      }
      // Si c'est un objet avec une propriété content
      else if (data.response.content) {
        responseText = data.response.content;
      }
      // Si c'est un objet avec une propriété text
      else if (data.response.text) {
        responseText = data.response.text;
      }
    }

    return NextResponse.json({ response: responseText });
  } catch (error) {
    console.error('FastAPI error:', error);
    return NextResponse.json(
      { error: 'Erreur lors de la communication avec le serveur FastAPI. Vérifiez que le serveur est démarré sur le port 8000.' },
      { status: 500 }
    );
  }
} 