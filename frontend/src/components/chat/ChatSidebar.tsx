/**
 * 会话侧边栏组件
 */

import React from "react";
import { ChatSession } from "../../types/chat";

// ============== 时间分组工具 ==============

type TimeGroup = "today" | "yesterday" | "earlier";

const getTimeGroup = (timestamp: number): TimeGroup => {
  const now = new Date();
  const date = new Date(timestamp);

  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);

  if (date >= today) return "today";
  if (date >= yesterday) return "yesterday";
  return "earlier";
};

const groupSessions = (
  sessions: ChatSession[],
): Record<TimeGroup, ChatSession[]> => {
  const groups: Record<TimeGroup, ChatSession[]> = {
    today: [],
    yesterday: [],
    earlier: [],
  };

  // 按 updatedAt 降序排列
  const sorted = [...sessions].sort((a, b) => b.updatedAt - a.updatedAt);

  for (const session of sorted) {
    const group = getTimeGroup(session.updatedAt);
    groups[group].push(session);
  }

  return groups;
};

const formatTime = (timestamp: number): string => {
  const date = new Date(timestamp);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);

  if (date >= today) {
    return date.toLocaleTimeString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }
  if (date >= yesterday) {
    return "昨天";
  }
  return date.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
};

// ============== SessionItem 组件 ==============

interface SessionItemProps {
  session: ChatSession;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

const SessionItem: React.FC<SessionItemProps> = ({
  session,
  isActive,
  onSelect,
  onDelete,
}) => {
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete();
  };

  return (
    <div
      onClick={onSelect}
      className={`
        group relative flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer
        transition-colors
        ${
          isActive
            ? "bg-blue-50 text-blue-700"
            : "hover:bg-gray-100 text-gray-700"
        }
      `}
    >
      <span className="text-lg flex-shrink-0">💬</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{session.title}</p>
        <p className="text-xs text-gray-400">{formatTime(session.updatedAt)}</p>
      </div>

      {/* 删除按钮 - hover 显示 */}
      <button
        onClick={handleDelete}
        className={`
          flex-shrink-0 p-1 rounded text-gray-400 hover:text-red-500 hover:bg-red-50
          transition-all
          ${isActive ? "opacity-100" : "opacity-0 group-hover:opacity-100"}
        `}
        title="删除对话"
      >
        ✕
      </button>
    </div>
  );
};

// ============== SessionGroup 组件 ==============

interface SessionGroupProps {
  label: string;
  sessions: ChatSession[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

const SessionGroup: React.FC<SessionGroupProps> = ({
  label,
  sessions,
  activeId,
  onSelect,
  onDelete,
}) => {
  if (sessions.length === 0) return null;

  return (
    <div className="mb-4">
      <div className="px-3 py-1 text-xs text-gray-400 font-medium">{label}</div>
      <div className="space-y-1">
        {sessions.map((session) => (
          <SessionItem
            key={session.id}
            session={session}
            isActive={session.id === activeId}
            onSelect={() => onSelect(session.id)}
            onDelete={() => onDelete(session.id)}
          />
        ))}
      </div>
    </div>
  );
};

// ============== ChatSidebar 主组件 ==============

interface ChatSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onCreateSession: () => void;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({
  sessions,
  activeSessionId,
  onCreateSession,
  onSelectSession,
  onDeleteSession,
}) => {
  const groups = groupSessions(sessions);

  return (
    <div className="w-60 h-full bg-gray-50 border-r border-gray-200 flex flex-col">
      {/* 新建按钮 */}
      <div className="p-3">
        <button
          onClick={onCreateSession}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          <span>+</span>
          <span>新建对话</span>
        </button>
      </div>

      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto px-2">
        <SessionGroup
          label="今天"
          sessions={groups.today}
          activeId={activeSessionId}
          onSelect={onSelectSession}
          onDelete={onDeleteSession}
        />
        <SessionGroup
          label="昨天"
          sessions={groups.yesterday}
          activeId={activeSessionId}
          onSelect={onSelectSession}
          onDelete={onDeleteSession}
        />
        <SessionGroup
          label="更早"
          sessions={groups.earlier}
          activeId={activeSessionId}
          onSelect={onSelectSession}
          onDelete={onDeleteSession}
        />

        {/* 空状态 */}
        {sessions.length === 0 && (
          <div className="text-center py-8 text-gray-400 text-sm">
            暂无对话记录
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatSidebar;
