"use client";

import { use } from "react";
import { ChatView } from "@/components/chat/chat-view";

interface ChatDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function ChatDetailPage({ params }: ChatDetailPageProps) {
  const { id } = use(params);
  return <ChatView conversationId={id} />;
}
