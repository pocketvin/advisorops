import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type JudgmentItem, type SavedAttachment } from "../api";

interface Props {
  customerId: string;
  onClose: () => void;
  onRecordWork: (workItemId: number, customerId: string) => void;
}

function formatTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

const stageLabels: Record<string, string> = {
  new: "新客户",
  contacted: "已联系",
  interested: "有明确兴趣",
  considering: "考虑中",
  rejected: "近期明确拒绝",
  dormant: "长期沉默",
};

const intentLabels: Record<string, string> = {
  unknown: "未知",
  low: "低",
  medium: "中",
  high: "高",
};

function listText(value: string[] | undefined): string {
  return value?.length ? value.join("、") : "未记录";
}

function activityAttachments(
  metadata: Record<string, unknown> | undefined,
): SavedAttachment[] {
  const value = metadata?.attachments;
  return Array.isArray(value) ? (value as SavedAttachment[]) : [];
}

function JudgmentBlock({
  label,
  item,
  tone = "default",
}: {
  label: string;
  item: JudgmentItem;
  tone?: "default" | "attention" | "avoid";
}) {
  return (
    <article className={"judgment-block " + tone}>
      <span className="judgment-label">{label}</span>
      <strong>{item.text}</strong>
      {item.evidence.length > 0 && (
        <details className="judgment-evidence">
          <summary>查看判断依据</summary>
          <div>
            {item.evidence.map((evidence, index) => (
              <p key={evidence.source + index}>
                <span
                  className={
                    evidence.kind === "hypothesis"
                      ? "evidence-source hypothesis"
                      : "evidence-source"
                  }
                >
                  {evidence.source}
                  {evidence.kind === "hypothesis" ? " · 待验证" : ""}
                </span>
                {evidence.text}
              </p>
            ))}
          </div>
        </details>
      )}
    </article>
  );
}


function ProfileItem({
  label,
  value,
}: {
  label: string;
  value: string | undefined;
}) {
  return (
    <div className="panorama-item">
      <span>{label}</span>
      <strong>{value || "未记录"}</strong>
    </div>
  );
}

export default function CustomerDrawer({
  customerId,
  onClose,
  onRecordWork,
}: Props) {
  const queryClient = useQueryClient();
  const [contextPreview, setContextPreview] = useState<string | null>(null);
  const [copyState, setCopyState] = useState("复制");
  const query = useQuery({
    queryKey: ["customer", customerId],
    queryFn: () => api.customer(customerId),
  });

  const briefMutation = useMutation({
    mutationFn: () => api.aiBrief(customerId),
  });

  const contextMutation = useMutation({
    mutationFn: () => api.contextPack(customerId),
    onSuccess: (result) => setContextPreview(result.text),
  });

  const manualWork = useMutation({
    mutationFn: () => api.manualWork(customerId),
    onSuccess: async (workItem) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["workbench"] }),
        queryClient.invalidateQueries({ queryKey: ["customers"] }),
        queryClient.invalidateQueries({ queryKey: ["customer", customerId] }),
      ]);
      onClose();
      onRecordWork(workItem.id, customerId);
    },
  });

  const pinMutation = useMutation({
    mutationFn: (pinned: boolean) => api.setPin(customerId, pinned),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["workbench"] }),
        queryClient.invalidateQueries({ queryKey: ["customers"] }),
        queryClient.invalidateQueries({ queryKey: ["customer", customerId] }),
      ]);
    },
  });

  const applyProposal = useMutation({
    mutationFn: api.applyProposal,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["customer", customerId] }),
        queryClient.invalidateQueries({ queryKey: ["workbench"] }),
        queryClient.invalidateQueries({ queryKey: ["customers"] }),
        queryClient.invalidateQueries({ queryKey: ["activities"] }),
      ]);
    },
  });

  const rejectProposal = useMutation({
    mutationFn: api.rejectProposal,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["customer", customerId] }),
        queryClient.invalidateQueries({ queryKey: ["activities"] }),
      ]);
    },
  });

  async function copyContext() {
    if (!contextPreview) return;
    try {
      await navigator.clipboard.writeText(contextPreview);
      setCopyState("已复制");
      window.setTimeout(() => setCopyState("复制"), 1600);
    } catch {
      setCopyState("复制失败");
    }
  }

  return (
    <div className="drawer-backdrop" role="presentation" onMouseDown={onClose}>
      <aside
        className="drawer drawer-customer-detail"
        aria-label="客户详情"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="drawer-header">
          <div>
            <p className="eyebrow">客户经营档案</p>
            <h2>{query.data?.customer.name ?? "正在读取…"}</h2>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </header>

        <div className="drawer-body">
          {query.isLoading && <p className="muted">正在读取完整经营记录…</p>}
          {query.error && <div className="error-banner">{query.error.message}</div>}

          {query.data && (
            <>
              <div className="customer-primary-actions">
                <button
                  className="button primary"
                  disabled={manualWork.isPending}
                  onClick={() => manualWork.mutate()}
                >
                  {manualWork.isPending ? "正在进入记录…" : "记录客户动态"}
                </button>
                <button
                  className="button secondary"
                  disabled={pinMutation.isPending}
                  onClick={() =>
                    pinMutation.mutate(!query.data!.customer.pinned)
                  }
                >
                  {query.data.customer.pinned ? "取消置顶" : "人工置顶"}
                </button>
              </div>

              <section className="operating-judgment-card">
                <div className="operating-judgment-head">
                  <div>
                    <p className="eyebrow">RELATIONSHIP MANAGER VIEW</p>
                    <h3>客户经营判断</h3>
                    <p>
                      先回答“现在怎么理解这个客户、下一次怎么沟通”，再展开看完整档案。
                      结论来自已确认状态、画像、工作项和最近沟通；待验证假设会单独标记。
                    </p>
                  </div>
                  <span className="judgment-mode">即时规则判断</span>
                </div>

                <div className="judgment-grid">
                  <JudgmentBlock
                    label="现在处于什么状态？"
                    item={query.data.operating_judgment.current_state}
                  />
                  <JudgmentBlock
                    label="当前真正关心什么？"
                    item={query.data.operating_judgment.core_concern}
                  />
                  <JudgmentBlock
                    label="最大的决策障碍是什么？"
                    item={query.data.operating_judgment.decision_barrier}
                    tone="attention"
                  />
                  <JudgmentBlock
                    label="下一次最该确认什么？"
                    item={query.data.operating_judgment.next_confirmation}
                    tone="attention"
                  />
                </div>

                <div className="judgment-wide-row">
                  <JudgmentBlock
                    label="更合适的沟通方式"
                    item={query.data.operating_judgment.communication_approach}
                  />
                  <JudgmentBlock
                    label="当前应该避免什么？"
                    item={query.data.operating_judgment.avoid_action}
                    tone="avoid"
                  />
                </div>
              </section>

              <section className="profile-card">
                <div className="profile-grid">
                  <div>
                    <span>关系阶段</span>
                    <strong>
                      {stageLabels[query.data.customer.relationship_stage] ??
                        query.data.customer.relationship_stage}
                    </strong>
                  </div>
                  <div>
                    <span>当前意向</span>
                    <strong>
                      {intentLabels[query.data.customer.intent_level] ??
                        query.data.customer.intent_level}
                    </strong>
                  </div>
                  <div>
                    <span>服务层级（模拟）</span>
                    <strong>{query.data.customer.customer_level}</strong>
                  </div>
                  <div>
                    <span>风险等级</span>
                    <strong>{query.data.customer.risk_level}</strong>
                  </div>
                </div>

                <div className="profile-block profile-facts">
                  <span>资产与持仓</span>
                  <p>
                    {query.data.customer.total_assets_band} · 可投资资金{" "}
                    {query.data.customer.investable_funds_band} ·{" "}
                    {query.data.customer.holdings_summary || "暂无持仓摘要"}
                  </p>
                </div>
                <div className="profile-block profile-facts">
                  <span>近期行为</span>
                  <p>
                    近30日资产变化{" "}
                    {query.data.customer.asset_change_30d_pct >= 0 ? "+" : ""}
                    {query.data.customer.asset_change_30d_pct.toFixed(1)}%
                    {" · "}
                    最近关注：
                    {query.data.customer.recent_product_interest || "无"}
                    {" · "}
                    最近咨询：
                    {query.data.customer.recent_consult_topic || "无"}
                  </p>
                </div>

                <div className="profile-block">
                  <span>当前需求</span>
                  <p>{query.data.customer.current_need || "暂无明确记录"}</p>
                </div>
                <div className="profile-block">
                  <span>当前障碍</span>
                  <p>{query.data.customer.current_obstacle || "暂无明显障碍"}</p>
                </div>
                <div className="profile-block">
                  <span>当前进展</span>
                  <p>{query.data.customer.current_progress || "暂无进展记录"}</p>
                </div>
                <div className="profile-block">
                  <span>下一步</span>
                  <p>{query.data.customer.next_step || "尚未安排"}</p>
                </div>

                <div className="profile-block">
                  <span>客户经理备注</span>
                  <p>{query.data.customer.manager_note || "暂无备注"}</p>
                </div>
              </section>

              <section className="panorama-card">
                <div className="section-title-row compact-heading">
                  <div>
                    <p className="eyebrow">CLIENT PANORAMA</p>
                    <h3>客户全景画像</h3>
                    <p className="muted">
                      已确认事实与经营偏好；精确住址等非必要敏感信息不进入演示数据。
                    </p>
                  </div>
                </div>

                <div className="panorama-group">
                  <h4>生活与职业</h4>
                  <div className="panorama-grid">
                    <ProfileItem
                      label="居住区域"
                      value={query.data.customer.profile.demographics?.residence_region}
                    />
                    <ProfileItem
                      label="职业"
                      value={query.data.customer.profile.demographics?.occupation}
                    />
                    <ProfileItem
                      label="行业"
                      value={query.data.customer.profile.demographics?.industry}
                    />
                    <ProfileItem
                      label="单位类型"
                      value={query.data.customer.profile.demographics?.employer_type}
                    />
                    <ProfileItem
                      label="家庭阶段"
                      value={query.data.customer.profile.family_and_life?.family_stage}
                    />
                    <ProfileItem
                      label="家庭责任"
                      value={query.data.customer.profile.family_and_life?.dependents_summary}
                    />
                  </div>
                  <div className="panorama-wide">
                    <span>未来重要安排</span>
                    <strong>
                      {query.data.customer.profile.family_and_life?.major_plan || "未记录"}
                    </strong>
                  </div>
                </div>

                <div className="panorama-group">
                  <h4>财务与投资背景</h4>
                  <div className="panorama-grid">
                    <ProfileItem
                      label="年收入区间"
                      value={query.data.customer.profile.financial_context?.annual_income_band}
                    />
                    <ProfileItem
                      label="负债区间"
                      value={query.data.customer.profile.financial_context?.liabilities_band}
                    />
                    <ProfileItem
                      label="现金流特征"
                      value={query.data.customer.profile.financial_context?.cash_flow_pattern}
                    />
                    <ProfileItem
                      label="流动性偏好"
                      value={query.data.customer.profile.financial_context?.liquidity_preference}
                    />
                    <ProfileItem
                      label="投资经验"
                      value={query.data.customer.profile.investment_context?.experience}
                    />
                    <ProfileItem
                      label="主要投资目标"
                      value={query.data.customer.profile.investment_context?.primary_goal}
                    />
                    <ProfileItem
                      label="投资期限"
                      value={query.data.customer.profile.investment_context?.investment_horizon}
                    />
                    <ProfileItem
                      label="信息偏好"
                      value={query.data.customer.profile.investment_context?.information_preference}
                    />
                  </div>
                </div>

                <div className="panorama-group">
                  <h4>沟通与关系画像</h4>
                  <div className="panorama-grid">
                    <ProfileItem
                      label="偏好渠道"
                      value={query.data.customer.profile.service_preferences?.preferred_channel}
                    />
                    <ProfileItem
                      label="偏好联系时间"
                      value={query.data.customer.profile.service_preferences?.preferred_contact_time}
                    />
                  </div>
                  <div className="panorama-wide">
                    <span>沟通偏好</span>
                    <strong>
                      {query.data.customer.profile.service_preferences?.communication_style || "未记录"}
                    </strong>
                  </div>
                  <div className="panorama-tags">
                    <div>
                      <span>兴趣</span>
                      <p>{listText(query.data.customer.profile.relationship_context?.interests)}</p>
                    </div>
                    <div>
                      <span>主要顾虑</span>
                      <p>{listText(query.data.customer.profile.relationship_context?.key_concerns)}</p>
                    </div>
                    <div>
                      <span>建立信任的因素</span>
                      <p>{listText(query.data.customer.profile.relationship_context?.trust_factors)}</p>
                    </div>
                  </div>
                </div>

                {query.data.customer.profile_hypotheses.length > 0 && (
                  <div className="hypothesis-panel">
                    <div>
                      <strong>待验证经营假设</strong>
                      <span>不是客户事实，只用于提示下一次沟通需要验证什么。</span>
                    </div>
                    {query.data.customer.profile_hypotheses.map((item) => (
                      <article key={item.key}>
                        <div>
                          <strong>{item.value}</strong>
                          <span>置信度 {Math.round(item.confidence * 100)}%</span>
                        </div>
                        <p>{item.basis}</p>
                      </article>
                    ))}
                  </div>
                )}
              </section>

              <section className="ai-tools-card">
                <div className="ai-tools-head">
                  <div>
                    <p className="eyebrow">INTELLIGENT ASSIST</p>
                    <h3>AI 经营辅助</h3>
                    <p className="muted">
                      摘要只读；咨询上下文默认脱敏后复制给更强 AI。
                    </p>
                  </div>
                  <div className="ai-tool-actions">
                    <button
                      className="button secondary"
                      disabled={briefMutation.isPending}
                      onClick={() => briefMutation.mutate()}
                    >
                      {briefMutation.isPending ? "正在整理…" : "30 秒摘要"}
                    </button>
                    <button
                      className="button ai-button"
                      disabled={contextMutation.isPending}
                      onClick={() => contextMutation.mutate()}
                    >
                      {contextMutation.isPending ? "正在生成…" : "AI 咨询上下文"}
                    </button>
                  </div>
                </div>

                {briefMutation.error && (
                  <div className="error-banner">
                    摘要失败：{briefMutation.error.message}
                  </div>
                )}

                {briefMutation.data && (
                  <div className="brief-result">
                    <strong>{briefMutation.data.summary}</strong>
                    <div className="brief-grid">
                      <div>
                        <span>当前关注</span>
                        <p>{briefMutation.data.main_focus}</p>
                      </div>
                      <div>
                        <span>当前障碍</span>
                        <p>{briefMutation.data.current_obstacle || "暂无"}</p>
                      </div>
                    </div>
                    <div className="brief-focus">
                      <span>下次最值得确认</span>
                      <p>{briefMutation.data.next_conversation_focus}</p>
                    </div>
                  </div>
                )}
              </section>

              {query.data.pending_proposals.length > 0 && (
                <section className="pending-section">
                  <div className="section-title-row compact-heading">
                    <div>
                      <p className="eyebrow">PENDING CHANGES</p>
                      <h3>待确认状态变化</h3>
                    </div>
                    <span className="section-count">
                      {query.data.pending_proposals.length}
                    </span>
                  </div>
                  <div className="proposal-stack">
                    {query.data.pending_proposals.map((proposal) => (
                      <article className="proposal-card" key={proposal.id}>
                        <div className="proposal-head">
                          <div>
                            <strong>{proposal.extraction_summary}</strong>
                            <span>
                              {proposal.confidence != null
                                ? "候选置信度 " + String(Math.round(proposal.confidence * 100)) + "%"
                                : "待确认"}
                            </span>
                          </div>
                        </div>
                        <div className="proposal-changes">
                          {Object.entries(proposal.proposed_changes).map(
                            ([field, change]) => (
                              <div key={field}>
                                <span>{field}</span>
                                <code>
                                  {String(change.from ?? "—")} →{" "}
                                  {String(change.to ?? "—")}
                                </code>
                              </div>
                            ),
                          )}
                        </div>
                        <div className="card-actions">
                          <button
                            className="button ghost"
                            disabled={rejectProposal.isPending}
                            onClick={() => rejectProposal.mutate(proposal.id)}
                          >
                            忽略
                          </button>
                          <button
                            className="button primary compact"
                            disabled={applyProposal.isPending}
                            onClick={() => applyProposal.mutate(proposal.id)}
                          >
                            确认更新
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
              )}

              {query.data.active_work_item && (
                <section className="active-work-callout">
                  <div>
                    <span>当前工作项</span>
                    <strong>{query.data.active_work_item.title}</strong>
                  </div>
                  <span className="status-pill">
                    {query.data.active_work_item.status === "waiting"
                      ? "等待中"
                      : "待我处理"}
                  </span>
                </section>
              )}

              <section className="timeline-section">
                <div className="section-title-row">
                  <div>
                    <p className="eyebrow">Activity Timeline</p>
                    <h3>经营时间线</h3>
                  </div>
                  <span className="muted">{query.data.activities.length} 条记录</span>
                </div>

                <div className="timeline">
                  {query.data.activities.map((activity) => (
                    <article className="timeline-item" key={activity.id}>
                      <div className="timeline-dot" />
                      <div className="timeline-content">
                        <div className="timeline-meta">
                          <span>{formatTime(activity.occurred_at)}</span>
                          <span>{activity.channel}</span>
                          <span>{activity.source}</span>
                        </div>
                        <h4>
                          {activity.action_taken ||
                            (activity.activity_type === "work_started"
                              ? "开始跟进"
                              : activity.activity_type)}
                        </h4>
                        <p>{activity.structured_summary || "暂无结构化摘要"}</p>
                        {activity.customer_feedback && (
                          <blockquote>{activity.customer_feedback}</blockquote>
                        )}
                        {activityAttachments(activity.metadata).length > 0 && (
                          <div className="timeline-attachments">
                            {activityAttachments(activity.metadata).map((attachment) => (
                              <a
                                key={attachment.id}
                                href={attachment.url}
                                target="_blank"
                                rel="noreferrer"
                                title={attachment.name}
                              >
                                <img src={attachment.url} alt={attachment.name} />
                              </a>
                            ))}
                          </div>
                        )}
                        {activity.raw_content && (
                          <details className="raw-record">
                            <summary>查看原始记录</summary>
                            <p>{activity.raw_content}</p>
                          </details>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              </section>

              {query.data.field_changes.length > 0 && (
                <section className="audit-section">
                  <div className="section-title-row">
                    <div>
                      <p className="eyebrow">Traceable State</p>
                      <h3>最近状态变化</h3>
                    </div>
                  </div>
                  <div className="audit-list">
                    {query.data.field_changes.slice(0, 10).map((change) => (
                      <div className="audit-row" key={change.id}>
                        <span>{change.field_name}</span>
                        <code>
                          {change.old_value || "—"} → {change.new_value || "—"}
                        </code>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </>
          )}
        </div>

        {contextPreview && (
          <div className="context-preview-panel">
            <div className="context-preview-head">
              <div>
                <p className="eyebrow">SAFE CONTEXT PACK</p>
                <h3>AI 咨询上下文预览</h3>
                <p>已去掉姓名等直接身份字段，再由你主动复制。</p>
              </div>
              <button
                className="icon-button"
                onClick={() => setContextPreview(null)}
              >
                ×
              </button>
            </div>
            <pre>{contextPreview}</pre>
            <div className="form-actions">
              <button className="button primary" onClick={copyContext}>
                {copyState}
              </button>
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}
