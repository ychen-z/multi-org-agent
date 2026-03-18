# Chat Sessions 任务清单

## 1. 类型定义更新

- [x] 1.1 在 `chat.ts` 添加 `ChatSession` 接口
- [x] 1.2 在 `chat.ts` 添加 `ChatStorage` 接口
- [x] 1.3 在 `chat.ts` 添加常量 `MAX_SESSIONS=20`, `TITLE_MAX_LENGTH=20`

## 2. 创建 useChatSessions hook

- [x] 2.1 创建 `hooks/useChatSessions.ts` 基础结构
- [x] 2.2 实现 LocalStorage 读写逻辑（加载/保存）
- [x] 2.3 实现 `createSession`（含数量限制检查）
- [x] 2.4 实现 `switchSession`（含空会话清理）
- [x] 2.5 实现 `deleteSession`
- [x] 2.6 实现 `sendMessage`（首条消息更新 title）
- [x] 2.7 实现 `inputValue` 受控状态

## 3. 创建 ChatSidebar 组件

- [x] 3.1 创建 `components/chat/` 目录结构
- [x] 3.2 实现 `ChatSidebar.tsx` 基础布局
- [x] 3.3 实现 `NewChatButton` 新建按钮
- [x] 3.4 实现时间分组逻辑（今天/昨天/更早）
- [x] 3.5 实现 `SessionItem` 组件（含 hover 删除按钮）

## 4. 重构 ChatPage

- [x] 4.1 修改布局为左右结构（Sidebar + Main）
- [x] 4.2 集成 `useChatSessions` hook
- [x] 4.3 修改 `SuggestionChips` onClick 为填充输入框
- [x] 4.4 修改 `InputBox` 为受控组件
- [x] 4.5 添加组件导出文件 `index.ts`

## 5. 测试验证

- [ ] 5.1 测试新建/切换/删除会话
- [ ] 5.2 测试空会话自动清理
- [ ] 5.3 测试超过 20 个自动删除最老
- [ ] 5.4 测试建议点击填充输入框
- [ ] 5.5 测试刷新后状态恢复
