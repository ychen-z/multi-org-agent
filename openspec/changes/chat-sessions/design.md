# Chat Sessions 设计

## 数据结构

```typescript
// 会话元数据
interface ChatSession {
  id: string; // UUID
  title: string; // 自动截取 or "新对话"
  messages: Message[]; // 消息列表
  createdAt: number; // 创建时间戳
  updatedAt: number; // 最后更新时间戳
}

// LocalStorage 结构
interface ChatStorage {
  sessions: ChatSession[]; // 所有会话（按 updatedAt 降序）
  activeSessionId: string | null;
}

// 常量
const MAX_SESSIONS = 20;
const TITLE_MAX_LENGTH = 20;
const STORAGE_KEY = "hr-chat-sessions";
```

## UI 布局

```
┌───────────────────────────┬──────────────────────────────────────────────────────┐
│   ChatSidebar (w-60)      │                    ChatMain (flex-1)                 │
│                           │                                                      │
│  ┌─────────────────────┐  │  ┌────────────────────────────────────────────────┐  │
│  │  [+] 新建对话       │  │  │  AI 对话                              [清空]  │  │
│  └─────────────────────┘  │  │  多轮对话分析，支持跨领域问题                 │  │
│                           │  └────────────────────────────────────────────────┘  │
│  ┈┈┈ 今天 ┈┈┈            │                                                      │
│  ┌─────────────────────┐  │  消息列表...                                        │
│  │ 💬 技术部门离职风险  │  │                                                      │
│  │    10:30         [×] │  │  建议问题 → 点击填充到输入框                        │
│  └─────────────────────┘  │                                                      │
│                           │  ┌────────────────────────────────────────────────┐  │
│  ┈┈┈ 昨天 ┈┈┈            │  │ [填充的建议内容█                    ] [发送]    │  │
│  ┌─────────────────────┐  │  └────────────────────────────────────────────────┘  │
│  │ 💬 招聘渠道分析      │  │                                                      │
│  │    Yesterday     [×] │  │                                                      │
│  └─────────────────────┘  │                                                      │
└───────────────────────────┴──────────────────────────────────────────────────────┘
```

## 组件结构

```
ChatPage
├── ChatSidebar
│   ├── NewChatButton
│   └── SessionList
│       ├── SessionGroup (今天)
│       │   └── SessionItem × N
│       ├── SessionGroup (昨天)
│       └── SessionGroup (更早)
│
└── ChatMain
    ├── ChatHeader
    ├── MessageList / EmptyState
    │   └── AssistantMessage
    │       └── SuggestionChips (点击填充)
    └── InputBox (受控组件)
```

## Hook API

```typescript
interface UseChatSessionsReturn {
  // 会话管理
  sessions: ChatSession[];
  activeSession: ChatSession | null;
  createSession: () => void;
  switchSession: (id: string) => void;
  deleteSession: (id: string) => void;

  // 消息相关
  messages: Message[];
  sendMessage: (content: string) => Promise<void>;

  // 流式状态
  isStreaming: boolean;
  streamingContent: string;
  currentThinking: ThinkStep[];
  stopGeneration: () => void;

  // 输入控制
  inputValue: string;
  setInputValue: (v: string) => void;

  // 错误处理
  error: string | undefined;
  clearError: () => void;
}
```

## 交互逻辑

1. **新建对话**: 清理当前空会话 → 创建新 Session → 检查数量限制
2. **切换会话**: 清理当前空会话 → 更新 activeSessionId
3. **删除会话**: 直接删除 → 如果是当前会话则切换到最新的
4. **发送首条消息**: 更新 title = message.slice(0, 20)
5. **建议点击**: setInputValue(suggestion) → focus 输入框

## 文件变更

```
frontend/src/
├── types/chat.ts              # 新增 ChatSession, ChatStorage 类型
├── hooks/useChatSessions.ts   # 新增：会话管理 hook
├── pages/ChatPage.tsx         # 重构：拆分为 Sidebar + Main
└── components/chat/           # 新增目录
    ├── ChatSidebar.tsx
    ├── SessionItem.tsx
    ├── ChatMain.tsx
    └── index.ts
```
