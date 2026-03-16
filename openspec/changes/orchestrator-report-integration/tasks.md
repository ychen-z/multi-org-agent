## 1. 缓存基础设施

- [x] 1.1 在 MongoDB 中创建 analysis_cache 集合
- [x] 1.2 创建 TTL 索引 (expires_at 字段)
- [x] 1.3 在 src/data/mongodb.py 中添加 analysis_cache 集合属性
- [x] 1.4 实现 CacheManager 类 (get_cache, set_cache, clear_cache)
- [x] 1.5 添加缓存统计记录 (hits, misses)

## 2. Orchestrator 进度回调

- [x] 2.1 修改 generate_strategic_report() 签名，添加 progress_callback 参数
- [x] 2.2 在每个分析阶段调用 progress_callback
- [x] 2.3 实现进度百分比计算逻辑
- [x] 2.4 确保 callback 是可选的，不影响无回调调用

## 3. 交叉归因缓存集成

- [x] 3.1 修改 cross_analysis() 添加 force_refresh 参数
- [x] 3.2 在 cross_analysis 开始时检查缓存
- [x] 3.3 缓存命中时直接返回，跳过 MongoDB 查询
- [x] 3.4 缓存未命中时执行查询并存入缓存
- [x] 3.5 生成缓存 key: cross*analysis*{YYYY-MM-DD-HH}

## 4. LLM 洞察生成

- [x] 4.1 设计交叉分析洞察的 system prompt
- [x] 4.2 在 cross_analysis 完成后调用 self.chat() 生成洞察
- [x] 4.3 设计 CEO 报告生成的 system prompt
- [x] 4.4 实现 \_generate_report_markdown() 方法调用 LLM
- [x] 4.5 实现 LLM 超时处理 (30秒)
- [x] 4.6 实现 LLM 失败回退逻辑 (规则模板)

## 5. API 异步报告生成

- [x] 5.1 修改 POST /reports/generate 返回 task_id
- [x] 5.2 实现 run_report_task() 后台函数
- [x] 5.3 集成 BackgroundTasks 启动后台任务
- [x] 5.4 实现进度回调到 WebSocket 推送
- [x] 5.5 任务完成后调用 ws_manager.complete_task()
- [x] 5.6 任务失败后调用 ws_manager.fail_task()

## 6. 任务状态管理

- [x] 6.1 实现任务状态存储 (内存字典或 MongoDB)
- [x] 6.2 实现 GET /reports/status/{task_id} 端点
- [x] 6.3 返回 running/completed/failed 状态
- [x] 6.4 处理 task_id 不存在的情况 (404)

## 7. WebSocket 增强

- [x] 7.1 确保 ws_manager.update_progress() 正确推送进度
- [x] 7.2 实现完成后保持连接 5 秒再关闭
- [x] 7.3 处理客户端断开重连场景

## 8. 数据导入缓存清理

- [x] 8.1 在 POST /data/import 成功后清除 analysis_cache
- [x] 8.2 在 POST /data/generate 成功后清除 analysis_cache

## 9. 配置与测试

- [x] 9.1 添加 ANALYSIS_CACHE_TTL 环境变量支持
- [x] 9.2 实现 GET /api/v1/system/cache-stats 端点
- [ ] 9.3 测试完整报告生成流程
- [ ] 9.4 测试 WebSocket 进度推送
- [ ] 9.5 测试缓存命中/未命中场景
- [ ] 9.6 测试 LLM 失败回退
