import { describe, expect, it } from "vitest";
import { appendExchange, boundConversation, MAX_EXCHANGES, MAX_MESSAGES } from "./conversation";
import type { ConversationMessage } from "../api/types";

function exchanges(n: number): ConversationMessage[] {
  const messages: ConversationMessage[] = [];
  for (let i = 0; i < n; i++) {
    messages.push({ role: "user", content: `question ${i}` });
    messages.push({ role: "assistant", content: `answer ${i}` });
  }
  return messages;
}

describe("boundConversation", () => {
  it("returns short history unchanged", () => {
    const history = exchanges(1);
    expect(boundConversation(history)).toEqual(history);
  });

  it("keeps exactly six exchanges untouched", () => {
    const history = exchanges(MAX_EXCHANGES);
    expect(boundConversation(history)).toEqual(history);
    expect(boundConversation(history)).toHaveLength(MAX_MESSAGES);
  });

  it("drops the oldest exchange once a seventh is added", () => {
    const history = exchanges(MAX_EXCHANGES + 1);
    const bounded = boundConversation(history);
    expect(bounded).toHaveLength(MAX_MESSAGES);
    expect(bounded[0].content).toBe("question 1");
    expect(bounded[bounded.length - 1].content).toBe("answer 6");
  });

  it("never exceeds twelve messages no matter how long the history", () => {
    expect(boundConversation(exchanges(50))).toHaveLength(12);
  });
});

describe("appendExchange", () => {
  it("appends a user question then an assistant answer, in order", () => {
    const result = appendExchange([], "Why did my range drop?", "Because of aggressive driving.");
    expect(result).toEqual([
      { role: "user", content: "Why did my range drop?" },
      { role: "assistant", content: "Because of aggressive driving." },
    ]);
  });

  it("bounds the result after appending", () => {
    const history = exchanges(MAX_EXCHANGES);
    const result = appendExchange(history, "one more?", "yes.");
    expect(result).toHaveLength(MAX_MESSAGES);
    expect(result[result.length - 1].content).toBe("yes.");
    expect(result[0].content).toBe("question 1");
  });

  it("does not mutate the original history array", () => {
    const history = exchanges(1);
    const copy = [...history];
    appendExchange(history, "x", "y");
    expect(history).toEqual(copy);
  });
});
