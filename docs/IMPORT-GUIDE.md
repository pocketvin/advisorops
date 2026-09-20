# AdvisorOps 客户批量导入

AdvisorOps 的批量导入采用 **CSV → 归一化预览 → 人工确认 → 事务写入**，选择文件后不会立即修改数据库。

## 推荐流程

1. 在“全部客户”点击 **批量导入 CSV**。
2. 下载标准模板或示例文件。
3. 用 Excel / WPS 填写后另存为 **CSV UTF-8**。
4. 上传文件并查看预览、错误和提醒。
5. 确认后只导入有效行；错误行会跳过。

当前限制：

- 仅支持 CSV；`.xlsx` 请先另存为 CSV UTF-8。
- 单文件最大 2MB。
- 单次最多 500 位客户。
- `name / 姓名 / 客户姓名` 是唯一必需列。
- `customer_id` 可为空，系统会生成稳定的 `IMP-XXXXXXXX` 编号。

## 字段别名

| 常见输入 | 内部字段 |
| --- | --- |
| 客户编号 / 客户ID / id | `customer_id` |
| 姓名 / 客户姓名 | `name` |
| 客户等级 / 服务层级 | `service_tier` |
| 风险等级 | `risk_level` |
| 关系阶段 / 客户阶段 | `relationship_stage` |
| 当前意向 / 意向 | `intent_level` |
| 总资产 / 资产区间 | `total_assets_band` |
| 可投资资金 | `investable_funds_band` |
| 居住区域 / 地区 / 住址 | `residence_region` |
| 职业 | `occupation` |
| 家庭阶段 | `family_stage` |
| 年收入 | `annual_income_band` |
| 负债 | `liabilities_band` |
| 投资目标 / 主要目标 | `primary_goal` |
| 沟通偏好 | `communication_style` |
| 兴趣 / 兴趣爱好 | `interests` |
| 主要顾虑 | `key_concerns` |

未识别列会显示在“已忽略列”中，不会偷偷进入数据库。

## 值归一化

### 关系阶段

- 新客户 / `new` → `new`
- 已联系 / 已沟通 / `contacted` → `contacted`
- 有兴趣 / 有明确兴趣 / `interested` → `interested`
- 考虑中 / 再考虑 / `considering` → `considering`
- 拒绝 / 近期明确拒绝 / `rejected` → `rejected`
- 沉默 / 长期沉默 / `dormant` → `dormant`

无法识别的关系阶段会使该行进入“需修正”，不会导入。

### 意向

- 未知 / `unknown` → `unknown`
- 低 / 低意向 / `low` → `low`
- 中 / 中意向 / `medium` → `medium`
- 高 / 高意向 / `high` → `high`

### 服务层级

演示标准层级为 Gold、Platinum、Black Gold、Diamond、Black Diamond。“金卡 / 铂金 / 黑金 / 钻石 / 黑钻”会自动映射。其他机构自己的层级不会被强行修改，会原样保留并给出提醒。

### 日期时间

支持 ISO 8601、`YYYY-MM-DD`、`YYYY/MM/DD`、`YYYY-MM-DD HH:MM`、`YYYY/MM/DD HH:MM`。无时区输入按 Asia/Shanghai 解释，数据库统一保存 UTC ISO 时间。

### 列表字段

`interests / key_concerns / trust_factors` 支持 `|`、`、`、`;`、`,` 分隔。

## 重复处理

V0.6 采用 **new-only import**：

- `customer_id` 已存在：该行报错并跳过。
- 同一 CSV 内 `customer_id` 重复：重复行报错。
- 姓名相同但编号不同：只提醒，不自动判定为同一客户。

同名客户在真实业务中可能存在，因此不做危险的自动覆盖。若未来需要更新型导入，应增加“按权威客户 ID 更新”的独立模式。

## 隐私边界

模板只设计粗粒度居住区域，例如“杭州·西湖”。如果检测到明显门牌格式会提醒。模板不设计手机号、身份证、证券账号、银行账号、精确地址或任何密钥字段。

## 导入后的数据走向

每个有效客户会：

1. 写入 `customers` Current Snapshot；
2. 写入一条 `source=import` 的 Activity；
3. Activity 保存 CSV 来源行号；
4. 后续正常参与发现区 / 工作区逻辑。

仓库内模板：

- `examples/customer-import-template.csv`
- `examples/customer-import-sample.csv`
