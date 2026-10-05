// Client-side mirror of backend/app/ai/conversation.py's bounding rule.
// The backend re-enforces this independently (never trusts the client), but
// bounding here too keeps the UI's own history list small and keeps what we
// send the backend consistent with what the Ask screen displays.
import type { ConversationMessage } from "../api/types";

export const MAX_EXCHANGES = 6;
export const MAX_MESSAGES = MAX_EXCHANGES * 2;

export function boundConversation(messages: ConversationMessage[]): ConversationMessage[] {
  if (messages.length <= MAX_MESSAGES) return messages;
  return messages.slice(-MAX_MESSAGES);
}

/** Appends one user/assistant exchange and re-bounds the history. */
export function appendExchange(
  history: ConversationMessage[],
  question: string,
  answer: string,
): ConversationMessage[] {
  return boundConversation([
    ...history,
    { role: "user", content: question },
    { role: "assistant", content: answer },
  ]);
}
