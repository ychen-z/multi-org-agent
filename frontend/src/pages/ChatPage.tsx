/**
 * AI 对话页面 - 支持多会话管理
 */

import React, { useState, useRef, useEffect } from "react";
import { useChatSessions } from "../hooks/useChatSessions";
import { ChatSidebar } from "../components/chat";
import { Message, ThinkStep } from "../types/chat";

// ============== 思维链组件 ==============

interface ThinkingChainProps {
  steps: ThinkStep[];
  isExpanded?: boolean;
}

const ThinkingChain: React.FC<ThinkingChainProps> = ({
  steps,
  isExpanded: initialExpanded = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(initialExpanded);

  if (steps.length === 0) return null;

  return (
    <div className="mb-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        <span className="text-lg">{isExpanded ? "🔽" : "▶️"}</span>
        <span>思维过程 ({steps.length} 步)</span>
      </button>

      {isExpanded && (
        <div className="mt-2 pl-4 border-l-2 border-gray-200 space-y-2">
          {steps.map((step, index) => (
            <ThinkingStep key={index} step={step} />
          ))}
        </div>
      )}
    </div>
  );
};

interface ThinkingStepProps {
  step: ThinkStep;
}

const ThinkingStep: React.FC<ThinkingStepProps> = ({ step }) => {
  const getIcon = () => {
    switch (step.type) {
      case "thought":
        return "💭";
      case "action":
        return "🔍";
      case "observation":
        return "📊";
      case "plan":
        return "📋";
      default:
        return "•";
    }
  };

  const getLabel = () => {
    switch (step.type) {
      case "thought":
        return "思考";
      case "action":
        return step.agent ? `调用 ${step.agent}` : "执行";
      case "observation":
        return "观察";
      case "plan":
        return "规划";
      default:
        return "";
    }
  };

  return (
    <div className="flex items-start gap-2 text-sm">
      <span className="text-lg flex-shrink-0">{getIcon()}</span>
      <div className="flex-1 min-w-0">
        <span className="text-gray-500 text-xs">[{getLabel()}]</span>
        <p className="text-gray-700 break-words">
          {step.content.length > 200
            ? step.content.slice(0, 200) + "..."
            : step.content}
        </p>
      </div>
    </div>
  );
};

// ============== 消息组件 ==============

interface UserMessageProps {
  message: Message;
}

const UserMessage: React.FC<UserMessageProps> = ({ message }) => (
  <div className="flex justify-end mb-4">
    <div className="max-w-[80%] bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-3">
      <p className="whitespace-pre-wrap">{message.content}</p>
    </div>
  </div>
);

interface AssistantMessageProps {
  message: Message;
  isStreaming?: boolean;
  streamingContent?: string;
  currentThinking?: ThinkStep[];
  onSuggestionSelect?: (suggestion: string) => void;
}

const AssistantMessage: React.FC<AssistantMessageProps> = ({
  message,
  isStreaming,
  streamingContent,
  currentThinking,
  onSuggestionSelect,
}) => {
  const content = isStreaming ? streamingContent : message.content;
  const thinking = isStreaming ? currentThinking : message.thinking;

  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[85%]">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-2xl">🤖</span>
          <span className="text-sm text-gray-500">AI 助手</span>
        </div>

        {/* 思维链 */}
        {thinking && thinking.length > 0 && (
          <ThinkingChain steps={thinking} isExpanded={isStreaming} />
        )}

        {/* 回复内容 */}
        <div className="bg-gray-100 rounded-2xl rounded-tl-md px-4 py-3">
          {content ? (
            <div className="prose prose-sm max-w-none">
              <p className="whitespace-pre-wrap">{content}</p>
            </div>
          ) : isStreaming ? (
            <div className="flex items-center gap-2 text-gray-500">
              <div className="animate-pulse">●</div>
              <span>正在思考...</span>
            </div>
          ) : null}

          {/* 流式光标 */}
          {isStreaming && content && (
            <span className="inline-block w-2 h-4 bg-gray-400 animate-pulse ml-1" />
          )}
        </div>

        {/* 建议问题 - 点击填充到输入框 */}
        {!isStreaming &&
          message.suggestions &&
          message.suggestions.length > 0 && (
            <SuggestionChips
              suggestions={message.suggestions}
              onSelect={onSuggestionSelect}
            />
          )}
      </div>
    </div>
  );
};

// ============== 建议问题组件 ==============

interface SuggestionChipsProps {
  suggestions: string[];
  onSelect?: (suggestion: string) => void;
}

const SuggestionChips: React.FC<SuggestionChipsProps> = ({
  suggestions,
  onSelect,
}) => (
  <div className="flex flex-wrap gap-2 mt-3">
    {suggestions.map((suggestion, index) => (
      <button
        key={index}
        onClick={() => onSelect?.(suggestion)}
        className="px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-full hover:bg-gray-50 hover:border-gray-400 transition-colors"
        title="点击填充到输入框"
      >
        {suggestion}
      </button>
    ))}
  </div>
);

// ============== 输入框组件（受控） ==============

interface InputBoxProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onStop?: () => void;
  isStreaming?: boolean;
  disabled?: boolean;
}

const InputBox: React.FC<InputBoxProps> = ({
  value,
  onChange,
  onSend,
  onStop,
  isStreaming,
  disabled,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim() && !disabled && !isStreaming) {
      onSend();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // 自动调整高度
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [value]);

  return (
    <form onSubmit={handleSubmit} className="flex gap-3 items-end">
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入你的问题..."
          disabled={disabled || isStreaming}
          rows={1}
          className="w-full px-4 py-3 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
        />
      </div>

      {isStreaming ? (
        <button
          type="button"
          onClick={onStop}
          className="px-4 py-3 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors flex items-center gap-2"
        >
          <span>■</span>
          <span>停止</span>
        </button>
      ) : (
        <button
          type="submit"
          disabled={!value.trim() || disabled}
          className="px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <span>发送</span>
          <span>↑</span>
        </button>
      )}
    </form>
  );
};

// ============== 空状态组件 ==============

const EmptyState: React.FC<{ onSelect: (suggestion: string) => void }> = ({
  onSelect,
}) => {
  const suggestions = [
    "技术部离职率为什么高？",
    "分析招聘渠道 ROI",
    "组织健康度如何？",
    "绩效分布是否合理？",
  ];

  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
      <div className="text-6xl mb-4">🤖</div>
      <h2 className="text-2xl font-semibold text-gray-800 mb-2">
        组织智能分析助手
      </h2>
      <p className="text-gray-500 mb-8 max-w-md">
        我可以帮你分析人才风险、招聘效能、绩效分布、组织健康等问题。
        支持多轮对话和跨领域分析。
      </p>
      <div className="flex flex-wrap gap-3 justify-center max-w-lg">
        {suggestions.map((suggestion, index) => (
          <button
            key={index}
            onClick={() => onSelect(suggestion)}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-colors text-sm"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
};

// ============== 主页面组件 ==============

const ChatPage: React.FC = () => {
  const {
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
  } = useChatSessions();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentThinking, streamingContent]);

  // 处理建议点击 - 填充到输入框
  const handleSuggestionSelect = (suggestion: string) => {
    setInputValue(suggestion);
  };

  // 处理发送
  const handleSend = () => {
    if (inputValue.trim()) {
      sendMessage(inputValue);
    }
  };

  return (
    <div className="flex h-[calc(100vh-73px)]">
      {/* 左侧会话列表 */}
      <ChatSidebar
        sessions={sessions}
        activeSessionId={activeSession?.id || null}
        onCreateSession={createSession}
        onSelectSession={switchSession}
        onDeleteSession={deleteSession}
      />

      {/* 右侧对话区域 */}
      <div className="flex-1 flex flex-col bg-white">
        {/* 头部 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h1 className="text-xl font-semibold text-gray-800">
              {activeSession?.title || "AI 对话"}
            </h1>
            <p className="text-sm text-gray-500">
              多轮对话分析，支持跨领域问题
            </p>
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between">
            <span className="text-red-600 text-sm">{error}</span>
            <button
              onClick={clearError}
              className="text-red-400 hover:text-red-600"
            >
              ✕
            </button>
          </div>
        )}

        {/* 消息区域 */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {messages.length === 0 && !isStreaming ? (
            <EmptyState onSelect={handleSuggestionSelect} />
          ) : (
            <div className="max-w-3xl mx-auto">
              {messages.map((message) =>
                message.role === "user" ? (
                  <UserMessage key={message.id} message={message} />
                ) : (
                  <AssistantMessage
                    key={message.id}
                    message={message}
                    onSuggestionSelect={handleSuggestionSelect}
                  />
                ),
              )}

              {/* 流式生成中的消息 */}
              {isStreaming && (
                <AssistantMessage
                  message={{
                    id: "streaming",
                    role: "assistant",
                    content: "",
                    timestamp: Date.now(),
                  }}
                  isStreaming={true}
                  streamingContent={streamingContent}
                  currentThinking={currentThinking}
                />
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 输入区域 */}
        <div className="border-t border-gray-200 px-6 py-4">
          <div className="max-w-3xl mx-auto">
            <InputBox
              value={inputValue}
              onChange={setInputValue}
              onSend={handleSend}
              onStop={stopGeneration}
              isStreaming={isStreaming}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
