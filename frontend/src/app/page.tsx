"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ApartmentResponse } from "@/components/ui/apartment-response";

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
      // Préparer l'historique des messages pour l'API
      const chatHistory = messages.map(msg => ({
        sender: msg.sender,
        text: msg.text
      }));

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: currentMessage,
          chatHistory: chatHistory
        }),
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
        text: "Désolé, une erreur s'est produite. Vérifiez que votre serveur FastAPI est démarré sur le port 8000.",
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

  const addToInput = (text: string) => {
    setInputText(prev => {
      const current = prev.trim();
      return current ? `${current}, ${text}` : text;
    });
  };

  const suggestionButtons = [
    // Première rangée
    "+ 2 chambres",
    "+ balcon",
    "+ proche métro",
    // Deuxième rangée
    "+ 800€ max",
    "+ 50m²",
    "+ ascenseur",
    "+ parking"
  ];

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <div className="border-b bg-white px-4 sm:px-6 md:px-8 lg:px-12 py-3 sm:py-4 md:py-6">
        <div className="w-full max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2 sm:gap-3">
            <img
              src="/Moveout_Logo2.svg"
              alt="MoveOutAI Logo"
              className="w-7 h-7 sm:w-8 sm:h-8 md:w-10 md:h-10"
            />
            <span className="font-semibold text-black text-xs sm:text-sm md:text-base">Moveout</span>
          </div>
          <div className="flex gap-2 sm:gap-3 md:gap-4">
            <button className="px-2 sm:px-4 md:px-6 py-1.5 sm:py-2 md:py-3 text-xs sm:text-sm md:text-base border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              Se connecter
            </button>
            <button className="px-2 sm:px-4 md:px-6 py-1.5 sm:py-2 md:py-3 text-xs sm:text-sm md:text-base bg-black text-white rounded-lg hover:bg-gray-800 transition-colors">
              Commencer
            </button>
          </div>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          // État initial sans messages - style Cupidly
          <div className="h-full flex items-center justify-center px-3 sm:px-4">
            <div className="text-center w-full max-w-2xl">
              <h1 className="text-2xl sm:text-3xl md:text-4xl font-semibold text-black mb-2 sm:mb-3">Que recherchez-vous ?</h1>
              <p className="text-gray-500 text-base sm:text-lg mb-6 sm:mb-8 px-2">Décrivez votre appartement idéal et laissez l&apos;IA vous aider à le trouver.</p>

              {/* Input centré style Cupidly */}
              <div className="relative w-full max-w-2xl mx-auto px-2">
                <textarea
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Décrivez votre appartement idéal..."
                  className="w-full resize-none border border-gray-200 rounded-2xl px-4 sm:px-6 py-3 sm:py-4 pr-12 sm:pr-16 focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300 text-sm sm:text-base placeholder-gray-400 shadow-lg"
                  rows={3}
                  style={{
                    minHeight: '100px',
                    maxHeight: '180px'
                  }}
                  disabled={isLoading}
                />

                {/* Bouton Send */}
                <Button
                  onClick={handleSendMessage}
                  disabled={!inputText.trim() || isLoading}
                  className="absolute bottom-3 sm:bottom-4 right-3 sm:right-4 w-7 h-7 sm:w-8 sm:h-8 bg-black hover:bg-gray-800 text-white rounded-full transition-colors disabled:opacity-30 disabled:cursor-not-allowed disabled:bg-gray-400 flex items-center justify-center"
                  size="icon"
                >
                  {isLoading ? (
                    <div className="w-3 h-3 sm:w-4 sm:h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <svg
                      className="w-3 h-3 sm:w-4 sm:h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                      />
                    </svg>
                  )}
                </Button>
              </div>

              {/* Boutons de suggestions */}
              <div className="mt-4 sm:mt-6 space-y-2 sm:space-y-3 px-2">
                {/* Première rangée */}
                <div className="flex flex-wrap justify-center gap-1.5 sm:gap-2">
                  {suggestionButtons.slice(0, 3).map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => addToInput(suggestion.replace('+ ', ''))}
                      className="flex items-center gap-1 px-2.5 sm:px-3 py-1.5 sm:py-2 bg-gray-100 hover:bg-gray-200 text-black text-xs sm:text-sm rounded-full transition-colors"
                    >
                      <span className="text-black font-medium">+</span>
                      <span>{suggestion.replace('+ ', '')}</span>
                    </button>
                  ))}
                </div>

                {/* Deuxième rangée */}
                <div className="flex flex-wrap justify-center gap-1.5 sm:gap-2">
                  {suggestionButtons.slice(3).map((suggestion, index) => (
                    <button
                      key={index + 3}
                      onClick={() => addToInput(suggestion.replace('+ ', ''))}
                      className="flex items-center gap-1 px-2.5 sm:px-3 py-1.5 sm:py-2 bg-gray-100 hover:bg-gray-200 text-black text-xs sm:text-sm rounded-full transition-colors"
                    >
                      <span className="text-black font-medium">+</span>
                      <span>{suggestion.replace('+ ', '')}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          // Messages
          <div className="w-full max-w-4xl mx-auto px-3 sm:px-4 py-4 sm:py-8">
            {messages.map((message) => (
              <div key={message.id} className="mb-4 sm:mb-6">
                <div className={`flex items-start gap-2 sm:gap-3 ${message.sender === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  {/* Avatar */}
                  <div className={`w-6 h-6 sm:w-8 sm:h-8 rounded-full flex items-center justify-center text-white text-xs sm:text-sm font-medium ${message.sender === 'user' ? 'bg-blue-600' : 'bg-gray-600'}`}>
                    {message.sender === 'user' ? 'U' : 'A'}
                  </div>
                  {/* Message Content */}
                  <div className={`flex-1 ${message.sender === 'user' ? 'text-right' : 'text-left'}`}>
                    <div className={`inline-block max-w-[85%] sm:max-w-[80%] break-words ${message.sender === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'} rounded-2xl px-3 sm:px-4 py-2 sm:py-3 text-sm`}>
                      {message.sender === 'assistant' ? (
                        <ApartmentResponse text={message.text} />
                      ) : (
                        <p className="whitespace-pre-wrap break-words">{message.text}</p>
                      )}
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
              <div className="mb-4 sm:mb-6">
                <div className="flex items-start gap-2 sm:gap-3">
                  <div className="w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-gray-600 flex items-center justify-center text-white text-xs sm:text-sm font-medium">A</div>
                  <div className="flex-1">
                    <div className="inline-block bg-gray-100 text-gray-900 rounded-2xl px-3 sm:px-4 py-2 sm:py-3">
                      <div className="flex items-center space-x-2">
                        <div className="flex space-x-1">
                          <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-gray-400 rounded-full animate-bounce"></div>
                          <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                        <span className="text-xs sm:text-sm text-gray-500">En train d&apos;écrire...</span>
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

      {/* Input Area - Fixed at bottom (seulement si des messages existent) */}
      {messages.length > 0 && (
        <div className="border-t bg-white p-4 sm:p-6">
          <div className="w-full max-w-4xl mx-auto">
            <div className="relative">
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Envoyez un message..."
                className="w-full resize-none border border-gray-200 rounded-xl px-4 sm:px-5 py-3 sm:py-4 pr-12 sm:pr-14 focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300 text-sm sm:text-base placeholder-gray-400 shadow-lg"
                rows={1}
                style={{
                  minHeight: '44px',
                  maxHeight: '120px'
                }}
                disabled={isLoading}
              />
              {/* Send Button */}
              <Button
                onClick={handleSendMessage}
                disabled={!inputText.trim() || isLoading}
                className="absolute right-2 sm:right-3 bottom-2 sm:bottom-3 w-8 h-8 sm:w-9 sm:h-9 bg-black hover:bg-gray-800 text-white rounded-full transition-colors disabled:opacity-30 disabled:cursor-not-allowed disabled:bg-gray-400 flex items-center justify-center"
                size="icon"
              >
                {isLoading ? (
                  <div className="w-4 h-4 sm:w-5 sm:h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <svg
                    className="w-4 h-4 sm:w-5 sm:h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                    />
                  </svg>
                )}
              </Button>
            </div>
            {/* Help text */}
            <p className="text-center text-xs text-gray-400 mt-3 sm:mt-4">
              Appuyez sur Entrée pour envoyer
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
