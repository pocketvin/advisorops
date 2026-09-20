# 端到端流程

## 1. 总流程

```text
外部系统 / 人工记录
        ↓
   客户动态入口
        ↓
统一 ActivityEvent
        ↓
   AI / 规则理解
        ↓
 ChangeProposal
        ↓
    人工确认
        ↓
 CustomerSnapshot
        ↓
 DiscoveryService
        ↓
      发现区
        ↓
    开始跟进
        ↓
     WorkItem
        ↓
      工作区
        ↓
  记录本次沟通
        ↓
   新 ActivityEvent
        ↓
状态更新 / 下一次时间
        ↓
未来到期后重新进入发现区
```

## 2. 客户动态同步流程

### 触发

- 用户点击“立即刷新”
- 可选周期同步
- 未来 webhook

### 流程

```text
读取 SyncState.cursor
→ Connector.fetch_since(cursor)
→ normalize(raw)
→ 检查 (source, source_event_id)
→ 写入 ActivityEvent
→ 识别确定事实
→ AI 提取解释性候选变化
→ 建立 ChangeProposal
→ 成功后更新 cursor
```

UI 显示：

- 最近同步时间
- 正在同步 / 成功 / 部分失败
- 新增动态数
- 需要人工确认数

某数据源失败不阻止其他来源刷新。

## 3. 人工记录电话 / 线下沟通

入口：

> 记录客户动态

客户经理选择渠道后，可直接输入自然语言：

> 刚刚给张总打电话……

保存前：

1. 原话作为 raw content 暂存
2. AI 生成结构化记录
3. 展示可编辑 Preview
4. 展示状态变化 Proposal
5. 客户经理确认
6. 同一事务内：
   - 写 ActivityEvent
   - 应用确认字段
   - 写 FieldChangeAudit
   - 更新 WorkItem
   - 重新计算发现条件

即使 AI 失败，也允许“保存原始记录 + 手工填写最小必要字段”。

AI 不能成为记录客户沟通的单点故障。

## 4. 发现区流程

```text
所有客户
→ 排除 active WorkItem
→ 排除今日已完成且无新事件
→ 排除未到期 cooldown
→ 查找 actionable reason
→ 产生候选
→ rule-based score
→ 排序
→ 展示原因与建议动作
```

### actionable reason 优先级来源

- overdue follow-up
- due follow-up
- new meaningful signal
- active intent without next action
- service review due

发现区卡片展示：

- 姓名 / 服务层级（模拟）
- 当前阶段
- 最近沟通
- 发现原因
- 建议下一步
- 为什么排这里
- 开始跟进
- 稍后跟进：明天 / 3 天后 / 1 周后 / 自定义时间
- 查看详情

### 图片附件

人工记录客户动态时可以附 JPEG / PNG / WebP 图片：

1. 浏览器校验类型与数量，必要时压缩图片；
2. 图片与文字一起送入视觉模型进行候选整理；
3. 客户经理确认后，原图落到本地 `work/attachments/`；
4. Activity 只保存附件元数据、哈希和访问地址；
5. 客户时间线显示附件缩略图；
6. 附件不进入 Git。

默认记录界面只展示文字、图片、渠道和“智能整理”；结构化字段折叠到高级修改区。

## 5. 开始跟进

点击“开始跟进”：

1. 创建 WorkItem
2. status = action_required
3. 记录 work_started Activity
4. 客户从发现区消失
5. 工作区出现

不要求用户再执行“加入工作区”和“开始”两次操作。

## 6. 工作区流程

### 待我处理

例如：

- 今天回访
- 补资料
- 确认需求
- 处理客户问题

### 等待中

记录：

- waiting_on
- 等待什么
- 预计检查时间

例如：

> waiting_on = customer
> 已发送资料，等待客户反馈
> 明天 16:00 检查

等待超时后只提高工作区提示，不把客户重复放回发现区。

### 今日完成

完成本次动作后：

- 写完整 ActivityEvent
- WorkItem = completed_today
- 如果有未来联系时间，则保存 next_contact_at
- 今天不再重复进入发现区

次日：

- 纯“已完成”不再占据工作区主要位置
- 若 next_contact_at 未到，不出现
- 到期后重新形成发现候选

## 7. 明确拒绝

客户反馈：

> 近期没有需求。

确认后：

- relationship_stage → rejected
- intent_level → low
- 设置 cooldown_until
- active WorkItem 完成本次
- 当天进入今日完成
- 冷静期内不进入发现区

冷静期结束后不是自动变成高优先级，而是允许形成：

> 服务关系复核

这种低打扰类型的候选。

## 8. 再考虑

客户：

> 我再考虑三天。

确认后：

- relationship_stage → considering
- next_contact_at = +3 days
- active WorkItem 完成本次
- 未来三天不进入发现区

到期：

- follow_up_state → due
- 自动形成发现候选
- 原因：“今天到达客户约定回访时间”

逾期：

- follow_up_state → overdue
- 紧迫度上升

不需要后台任务修改客户字段。

## 9. 新行为信号

外部来源：

> 近期资产变化明显 / 新增关注 / 新咨询主题

流程：

1. ActivityEvent 自动记录事实
2. 规则判断是否达到 meaningful signal
3. 若达到且无 active WorkItem：
   - 进入发现区
4. 若已有 active WorkItem：
   - 给工作区追加“新动态”提示

建议动作只到：

> 先核实需求变化

不直接生成金融产品推荐。

## 10. 客户详情

详情由四部分组成：

### 当前快照

- 当前阶段
- 意向
- 当前需求
- 当前障碍
- 下一步
- 下次联系

### 当前工作

- WorkItem
- 当前责任方
- due time

### 经营时间线

展示完整 ActivityEvent。

结构化摘要默认展示，原始记录可展开。

### 状态来源

例如点击：

> 当前阶段：考虑中

可看到：

> 09/20 电话沟通
> 客户表示近期存在资金使用计划，希望十月后再联系。
> 因此 interested → considering。

## 11. AI 经营摘要

触发：

- 打开客户详情时按需生成或读取短期缓存
- 用户点击重新整理

输入：

- CustomerSnapshot
- 最近 N 条 Activity
- 当前 WorkItem

输出：

- 最近经营概况
- 客户主要关注
- 当前障碍
- 尚未解决的问题
- 本次最值得确认的事项

不把摘要当作权威事实覆盖原始记录。

## 12. AI 咨询上下文

点击：

> 生成 AI 咨询上下文

流程：

```text
选取必要客户事实
→ 最近活动裁剪
→ 直接标识符移除
→ 精确数值降级为区间
→ 生成上下文
→ Preview
→ 用户复制
```

默认内容：

- 客户代号
- 年龄段
- 风险等级
- 资产区间
- 当前阶段 / 意向
- 当前需求 / 障碍
- 最近 5 次沟通
- 已采取措施
- 当前下一步
- 希望 AI 帮助的问题

默认排除：

- 姓名
- 手机号
- 身份证
- 证券账号
- 住址
- 密码 / 凭证
- 未必要的精确交易流水

## 13. Reset Demo

求职 Demo 必须提供：

> 重置演示数据

重置后恢复固定 30～50 个模拟客户和固定场景。

这样每次面试都能稳定演示同一条链路。
