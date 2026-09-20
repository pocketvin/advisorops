import { useQuery } from "@tanstack/react-query";

import { api } from "../api";

interface Props {
  customerId: string;
  onClose: () => void;
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

export default function CustomerDrawer({ customerId, onClose }: Props) {
  const query = useQuery({
    queryKey: ["customer", customerId],
    queryFn: () => api.customer(customerId),
  });

  return (
    <div className="drawer-backdrop" role="presentation" onMouseDown={onClose}>
      <aside
        className="drawer"
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
                    <span>客户等级</span>
                    <strong>{query.data.customer.customer_level}</strong>
                  </div>
                  <div>
                    <span>风险等级</span>
                    <strong>{query.data.customer.risk_level}</strong>
                  </div>
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
              </section>

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
                    {query.data.field_changes.slice(0, 8).map((change) => (
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
      </aside>
    </div>
  );
}
