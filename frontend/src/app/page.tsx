"use client";

import { useStream } from "@langchain/langgraph-sdk/react";
import { LoadExternalComponent } from "@langchain/langgraph-sdk/react-ui";
import Image from "next/image";

export default function Home() {
  const { thread, values } = useStream({
    apiUrl: "http://localhost:3000/",
    assistantId: "agent",
  });
  return (
    <div>
      {thread.messages.map((message) => (
        <div key={message.id}>
          {message.content}
          {values.ui
            ?.filter((ui) => ui.metadata?.message_id === message.id)
            .map((ui) => (
              <LoadExternalComponent key={ui.id} stream={thread} message={ui} />
            ))}
        </div>
      ))}

    </div>
  );
}
