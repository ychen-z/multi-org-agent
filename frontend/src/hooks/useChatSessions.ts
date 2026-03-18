/**
 * 会话管理 Hook - 支持多会话、LocalStorage 持久化
 */

import { useState, useCallback, useRef, useEffect } from "react";
import {
  Message,
  ThinkStep,
  ChatSession,
  ChatStorage,
  SSEEventType,
  ParsedSSEEvent,
  MAX_SESSIONS,
  TITLE_MAX_LENGTH,
  SESSIONS_STORAGE_KEY,
} from "../types/chat";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// 生成唯一 ID
const generateId = () =>
  `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// 创建空会话
const createEmptySession = (): ChatSession => ({
  id: generateId(),
  title: "新对话",
  messages: [],
  createdAt: Date.now(),
  updatedAt: Date.now(),
});

// 截取标题
const truncateTitle = (text: string): string => {
  if (text.length <= TITLE_MAX_LENGTH) return text;
  return text.slice(0, TITLE_MAX_LENGTH) + "...";
};

export function useChatSessions() {
  // 会话状态
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  // 流式状态
  const [currentThinking, setCurrentThinking] = useState<ThinkStep[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [error, setError] = useState<string | undefined>();

  // 输入控制
  const [inputValue, setInputValue] = useState("");

  const abortControllerRef = useRef<AbortController | null>(null);

  // 获取当前会话
  const activeSession = sessions.find((s) => s.id === activeSessionId) || null;
  const messages = activeSession?.messages || [];

  // ============== LocalStorage 读写 ==============

  // 加载
  useEffect(() => {
    try {
      const saved = localStorage.getItem(SESSIONS_STORAGE_KEY);
      if (saved) {
        const data: ChatStorage = JSON.parse(saved);
        setSessions(data.sessions || []);
        setActiveSessionId(data.activeSessionId);
      }
    } catch (e) {
      console.warn("Failed to load chat sessions:", e);
    }
  }, []);

  // 保存
  useEffect(() => {
    const data: ChatStorage = { sessions, activeSessionId };
    localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(data));
  }, [sessions, activeSessionId]);

  // ============== 会话管理 ==============

  // 清理空会话
  const cleanupEmptySessions = useCallback(() => {
    setSessions((prev) =>
      prev.filter((s) => s.messages.length > 0 || s.id === activeSessionId),
    );
  }, [activeSessionId]);

  // 新建会话
  const createSession = useCallback(() => {
    // 清理当前空会话
    cleanupEmptySessions();

    const newSession = createEmptySession();

    setSessions((prev) => {
      let updated = [newSession, ...prev];
      // 限制数量
      if (updated.length > MAX_SESSIONS) {
        updated = updated.slice(0, MAX_SESSIONS);
      }
      return updated;
    });

    setActiveSessionId(newSession.id);
    setInputValue("");
  }, [cleanupEmptySessions]);

  // 切换会话
  const switchSession = useCallback(
    (id: string) => {
      if (id === activeSessionId) return;

      // 清理当前空会话（如果不是要切换到的会话）
      setSessions((prev) =>
        prev.filter((s) => s.messages.length > 0 || s.id === id),
      );

      setActiveSessionId(id);
      setInputValue("");
      setCurrentThinking([]);
      setStreamingContent("");
    },
    [activeSessionId],
  );

  // 删除会话
  const deleteSession = useCallback(
    (id: string) => {
      setSessions((prev) => {
        const updated = prev.filter((s) => s.id !== id);

        // 如果删除的是当前会话，切换到最新的
        if (id === activeSessionId && updated.length > 0) {
          setActiveSessionId(updated[0].id);
        } else if (updated.length === 0) {
          setActiveSessionId(null);
        }

        return updated;
      });
    },
    [activeSessionId],
  );

  // ============== SSE 解析 ==============

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

  // ============== 发送消息 ==============

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isStreaming) return;

      // 确保有活跃会话
      let sessionId = activeSessionId;
      if (!sessionId) {
        const newSession = createEmptySession();
        setSessions((prev) => [newSession, ...prev].slice(0, MAX_SESSIONS));
        sessionId = newSession.id;
        setActiveSessionId(sessionId);
      }

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

      // 更新会话
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== sessionId) return s;

          const isFirst = s.messages.length === 0;
          return {
            ...s,
            title: isFirst ? truncateTitle(content.trim()) : s.title,
            messages: [...s.messages, userMessage],
            updatedAt: Date.now(),
          };
        }),
      );

      // 重置状态
      setCurrentThinking([]);
      setIsStreaming(true);
      setStreamingContent("");
      setError(undefined);
      setInputValue("");

      // 准备历史
      const history = messages.slice(-10).map((m) => ({
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
                setCurrentThinking((prev) => [...prev, step]);
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
                setCurrentThinking((prev) => [...prev, step]);
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
                  content: data.action,
                  step: data.step,
                  agent: data.agent || undefined,
                  action: data.action,
                  timestamp: Date.now(),
                };
                thinkingSteps.push(step);
                setCurrentThinking((prev) => [...prev, step]);
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
                setCurrentThinking((prev) => [...prev, step]);
                break;
              }

              case "content": {
                const data = parsed.data as { delta: string };
                fullContent += data.delta;
                setStreamingContent(fullContent);
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

        // 创建助手消息并更新会话
        const assistantMessage: Message = {
          id: generateId(),
          role: "assistant",
          content: fullContent,
          timestamp: Date.now(),
          thinking: thinkingSteps,
          suggestions,
        };

        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId
              ? {
                  ...s,
                  messages: [...s.messages, assistantMessage],
                  updatedAt: Date.now(),
                }
              : s,
          ),
        );

        setCurrentThinking([]);
        setIsStreaming(false);
        setStreamingContent("");
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          setIsStreaming(false);
          return;
        }

        console.error("Chat error:", err);
        setIsStreaming(false);
        setError((err as Error).message || "发送失败");
      }
    },
    [activeSessionId, isStreaming, messages, parseSSEEvent],
  );

  // 停止生成
  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  // 清除错误
  const clearError = useCallback(() => {
    setError(undefined);
  }, []);

  return {
    // 会话管理
    sessions,
    activeSession,
    createSession,
    switchSession,
    deleteSession,

    // 消息相关
    messages,
    sendMessage,

    // 流式状态
    isStreaming,
    streamingContent,
    currentThinking,
    stopGeneration,

    // 输入控制
    inputValue,
    setInputValue,

    // 错误处理
    error,
    clearError,
  };
}
