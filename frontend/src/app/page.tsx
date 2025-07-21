"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { useStream } from "@langchain/langgraph-sdk/react";

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const currentMessage = inputText;
    setInputText('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: currentMessage }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Erreur de communication');
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: data.response,
        sender: 'assistant',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: "Désolé, une erreur s'est produite. Vérifiez que votre clé API OpenAI est configurée correctement dans le fichier .env",
        sender: 'assistant',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          // État initial sans messages
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <h1 className="text-2xl font-semibold text-gray-800 mb-2">Comment puis-je vous aider ?</h1>
              <p className="text-gray-500">Commencez une conversation en tapant votre message ci-dessous.</p>
            </div>
          </div>
        ) : (
          // Messages
          <div className="max-w-3xl mx-auto px-4 py-8">
            {messages.map((message) => (
              <div key={message.id} className="mb-8">
                <div className={`flex items-start gap-4 ${message.sender === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  {/* Avatar */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium ${message.sender === 'user' ? 'bg-gray-600' : 'bg-gray-400'
                    }`}>
                    {message.sender === 'user' ? 'U' : 'A'}
                  </div>

                  {/* Message Content */}
                  <div className={`flex-1 ${message.sender === 'user' ? 'text-right' : 'text-left'}`}>
                    <div className={`inline-block max-w-full ${message.sender === 'user'
                      ? 'bg-gray-600 text-white'
                      : 'bg-gray-50 text-gray-900'
                      } rounded-2xl px-4 py-3`}>
                      <p className="whitespace-pre-wrap">{message.text}</p>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      {message.timestamp.toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </p>
                  </div>
                </div>
              </div>
            ))}

            {/* Loading indicator */}
            {isLoading && (
              <div className="mb-8">
                <div className="flex items-start gap-4">
                  <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center text-white text-sm font-medium">
                    A
                  </div>
                  <div className="flex-1">
                    <div className="inline-block bg-gray-50 text-gray-900 rounded-2xl px-4 py-3">
                      <div className="flex items-center space-x-2">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                        <span className="text-sm text-gray-500">En train d&apos;écrire...</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area - Fixed at bottom */}
      <div className="border-t bg-white p-4">
        <div className="max-w-3xl mx-auto">
          <div className="relative">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Envoyez un message..."
              className="w-full resize-none border border-gray-200 rounded-xl px-4 py-4 pr-12 focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300 text-base placeholder-gray-400 shadow-sm"
              rows={1}
              style={{
                minHeight: '56px',
                maxHeight: '200px'
              }}
              disabled={isLoading}
            />

            {/* Send Button */}
            <Button
              onClick={handleSendMessage}
              disabled={!inputText.trim() || isLoading}
              className="absolute right-2 bottom-2 p-2 bg-black hover:bg-gray-800 text-white rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed disabled:bg-gray-400 flex items-center justify-center"
              size="icon"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 12h14m-7-7l7 7-7 7"
                  />
                </svg>
              )}
            </Button>
          </div>

          {/* Help text */}
          <p className="text-center text-xs text-gray-400 mt-2">
            Appuyez sur Entrée pour envoyer
          </p>
        </div>
      </div>
    </div>
  );
}
