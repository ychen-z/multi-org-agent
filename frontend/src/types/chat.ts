/**
 * 对话式 AI 洞察类型定义
 */

// ============== 基础类型 ==============

export interface ThinkStep {
  type: "thought" | "action" | "observation" | "plan";
  content: string;
  data?: Record<string, unknown>;
  timestamp?: number;
  // action 专用
  step?: number;
  agent?: string;
  action?: string;
  // observation 专用
  result?: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  thinking?: ThinkStep[];
  suggestions?: string[];
}

export interface ChatState {
  messages: Message[];
  currentThinking: ThinkStep[];
  isStreaming: boolean;
  streamingContent: string;
  error?: string;
}

// ============== SSE 事件类型 ==============

export type SSEEventType =
  | "think"
  | "plan"
  | "action"
  | "observation"
  | "content"
  | "done"
  | "error";

export interface SSEThinkEvent {
  type: "thought";
  content: string;
}

export interface SSEPlanEvent {
  reasoning: string;
  steps: Array<{
    step: number;
    agent: string | null;
    action: string;
    depends_on: number[];
  }>;
}

export interface SSEActionEvent {
  step: number;
  action: string;
  agent: string | null;
}

export interface SSEObservationEvent {
  step: number;
  result: string;
}

export interface SSEContentEvent {
  delta: string;
}

export interface SSEDoneEvent {
  suggestions: string[];
}

export interface SSEErrorEvent {
  error: string;
}

export type SSEEventData =
  | SSEThinkEvent
  | SSEPlanEvent
  | SSEActionEvent
  | SSEObservationEvent
  | SSEContentEvent
  | SSEDoneEvent
  | SSEErrorEvent;

export interface ParsedSSEEvent {
  event: SSEEventType;
  data: SSEEventData;
}

// ============== API 请求/响应类型 ==============

export interface ChatRequest {
  message: string;
  history?: Array<{
    role: "user" | "assistant";
    content: string;
  }>;
}

export interface ChatResponse {
  success: boolean;
  data?: {
    message: string;
    thinking: ThinkStep[];
    suggestions: string[];
  };
  error?: string;
}

// ============== 会话类型 ==============

export interface ChatSession {
  id: string; // UUID
  title: string; // 自动截取 or "新对话"
  messages: Message[]; // 消息列表
  createdAt: number; // 创建时间戳
  updatedAt: number; // 最后更新时间戳
}

export interface ChatStorage {
  sessions: ChatSession[]; // 所有会话（按 updatedAt 降序）
  activeSessionId: string | null;
}

// ============== 常量 ==============

export const MAX_HISTORY_ROUNDS = 20;
export const MAX_HISTORY_MESSAGES = MAX_HISTORY_ROUNDS * 2;
export const CHAT_STORAGE_KEY = "org-intelligence-chat-history";

// 会话管理常量
export const MAX_SESSIONS = 20;
export const TITLE_MAX_LENGTH = 20;
export const SESSIONS_STORAGE_KEY = "hr-chat-sessions";
