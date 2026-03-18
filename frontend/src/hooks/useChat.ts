/**
 * 对话 Hook - 管理 SSE 通信和状态
 */

import { useState, useCallback, useRef, useEffect } from "react";
import {
  Message,
  ThinkStep,
  ChatState,
  SSEEventType,
  ParsedSSEEvent,
  MAX_HISTORY_MESSAGES,
  CHAT_STORAGE_KEY,
} from "../types/chat";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

console.log("API_BASE:", API_BASE);
// 生成唯一 ID
const generateId = () =>
  `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// ============== useChat Hook ==============

export function useChat() {
  const [state, setState] = useState<ChatState>({
    messages: [],
    currentThinking: [],
    isStreaming: false,
    streamingContent: "",
    error: undefined,
  });

  const abortControllerRef = useRef<AbortController | null>(null);

  // 从 LocalStorage 加载历史
  useEffect(() => {
    try {
      const saved = localStorage.getItem(CHAT_STORAGE_KEY);
      if (saved) {
        const messages = JSON.parse(saved) as Message[];
        setState((prev) => ({ ...prev, messages }));
      }
    } catch (e) {
      console.warn("Failed to load chat history:", e);
    }
  }, []);

  // 保存到 LocalStorage
  useEffect(() => {
    if (state.messages.length > 0) {
      // 限制保存的消息数量
      const toSave = state.messages.slice(-MAX_HISTORY_MESSAGES);
      localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(toSave));
    }
  }, [state.messages]);

  // 解析 SSE 事件
  const parseSSEEvent = useCallback(
    (eventText: string): ParsedSSEEvent | null => {
      const lines = eventText.trim().split("\n");
      let eventType: SSEEventType | null = null;
      let dataStr = "";

      for (const line of lines) {
        if (line.startsWith("event:")) {
          eventType = line.slice(6).trim() as SSEEventType;
        } else if (line.startsWith("data:")) {
          dataStr = line.slice(5).trim();
        }
      }

      if (!eventType || !dataStr) return null;

      try {
        const data = JSON.parse(dataStr);
        return { event: eventType, data };
      } catch {
        return null;
      }
    },
    [],
  );

  // 发送消息
  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || state.isStreaming) return;

      // 取消之前的请求
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      // 创建用户消息
      const userMessage: Message = {
        id: generateId(),
        role: "user",
        content: content.trim(),
        timestamp: Date.now(),
      };

      // 更新状态
      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
        currentThinking: [],
        isStreaming: true,
        streamingContent: "",
        error: undefined,
      }));

      // 准备历史（只取最近的消息）
      const history = state.messages.slice(-10).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      try {
        const response = await fetch(`${API_BASE}/api/v1/chat/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({
            message: content.trim(),
            history,
          }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";
        let fullContent = "";
        const thinkingSteps: ThinkStep[] = [];
        let suggestions: string[] = [];

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // 按双换行分割事件
          const events = buffer.split("\n\n");
          buffer = events.pop() || "";

          for (const eventText of events) {
            if (!eventText.trim()) continue;

            const parsed = parseSSEEvent(eventText);
            if (!parsed) continue;

            switch (parsed.event) {
              case "think": {
                const data = parsed.data as { type: string; content: string };
                const step: ThinkStep = {
                  type: "thought",
                  content: data.content,
                  timestamp: Date.now(),
                };
                thinkingSteps.push(step);
                setState((prev) => ({
                  ...prev,
                  currentThinking: [...prev.currentThinking, step],
                }));
                break;
              }

              case "plan": {
                const data = parsed.data as {
                  reasoning: string;
                  steps: unknown[];
                };
                const step: ThinkStep = {
                  type: "plan",
                  content: data.reasoning,
                  data: { steps: data.steps },
                  timestamp: Date.now(),
                };
                thinkingSteps.push(step);
                setState((prev) => ({
                  ...prev,
                  currentThinking: [...prev.currentThinking, step],
                }));
                break;
              }

              case "action": {
                const data = parsed.data as {
                  step: number;
                  action: string;
                  agent: string | null;
                };
                const step: ThinkStep = {
                  type: "action",
                  content: `${data.action}`,
                  step: data.step,
                  agent: data.agent || undefined,
                  action: data.action,
                  timestamp: Date.now(),
                };
                thinkingSteps.push(step);
                setState((prev) => ({
                  ...prev,
                  currentThinking: [...prev.currentThinking, step],
                }));
                break;
              }

              case "observation": {
                const data = parsed.data as { step: number; result: string };
                const step: ThinkStep = {
                  type: "observation",
                  content: data.result,
                  step: data.step,
                  result: data.result,
                  timestamp: Date.now(),
                };
                thinkingSteps.push(step);
                setState((prev) => ({
                  ...prev,
                  currentThinking: [...prev.currentThinking, step],
                }));
                break;
              }

              case "content": {
                const data = parsed.data as { delta: string };
                fullContent += data.delta;
                setState((prev) => ({
                  ...prev,
                  streamingContent: fullContent,
                }));
                break;
              }

              case "done": {
                const data = parsed.data as { suggestions: string[] };
                suggestions = data.suggestions || [];
                break;
              }

              case "error": {
                const data = parsed.data as { error: string };
                throw new Error(data.error);
              }
            }
          }
        }

        // 创建助手消息
        const assistantMessage: Message = {
          id: generateId(),
          role: "assistant",
          content: fullContent,
          timestamp: Date.now(),
          thinking: thinkingSteps,
          suggestions,
        };

        setState((prev) => ({
          ...prev,
          messages: [...prev.messages, assistantMessage],
          currentThinking: [],
          isStreaming: false,
          streamingContent: "",
        }));
      } catch (error) {
        if ((error as Error).name === "AbortError") {
          // 用户取消，忽略
          setState((prev) => ({
            ...prev,
            isStreaming: false,
          }));
          return;
        }

        console.error("Chat error:", error);
        setState((prev) => ({
          ...prev,
          isStreaming: false,
          error: (error as Error).message || "发送失败",
        }));
      }
    },
    [state.isStreaming, state.messages, parseSSEEvent],
  );

  // 停止生成
  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setState((prev) => ({
      ...prev,
      isStreaming: false,
    }));
  }, []);

  // 清空历史
  const clearHistory = useCallback(() => {
    setState({
      messages: [],
      currentThinking: [],
      isStreaming: false,
      streamingContent: "",
      error: undefined,
    });
    localStorage.removeItem(CHAT_STORAGE_KEY);
  }, []);

  // 清除错误
  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: undefined }));
  }, []);

  return {
    messages: state.messages,
    currentThinking: state.currentThinking,
    isStreaming: state.isStreaming,
    streamingContent: state.streamingContent,
    error: state.error,
    sendMessage,
    stopGeneration,
    clearHistory,
    clearError,
  };
}
