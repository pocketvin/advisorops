import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../api";

interface Props {
  onOpenCustomer: (customerId: string) => void;
}

function formatTime(value: string | null | undefined): string {
  if (!value) return "尚未同步";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

const sourceLabels: Record<string, string> = {
  mock_wecom: "企业微信（模拟）",
  mock_behavior: "行为数据（模拟）",
  mock_crm: "CRM（模拟）",
  manual: "人工记录",
};

export default function ActivityFeedView({ onOpenCustomer }: Props) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["activities"],
    queryFn: api.activityFeed,
  });

  const refresh = useMutation({
    mutationFn: api.refreshSources,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["activities"] }),
        queryClient.invalidateQueries({ queryKey: ["workbench"] }),
        queryClient.invalidateQueries({ queryKey: ["customers"] }),
      ]);
    },
  });

  const applyProposal = useMutation({
    mutationFn: api.applyProposal,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["activities"] }),
        queryClient.invalidateQueries({ queryKey: ["workbench"] }),
        queryClient.invalidateQueries({ queryKey: ["customers"] }),
        queryClient.invalidateQueries({ queryKey: ["customer"] }),
      ]);
    },
  });

  const rejectProposal = useMutation({
    mutationFn: api.rejectProposal,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["activities"] });
    },
  });

  return (
    <section className="activity-page">
      <div className="section-title-row customer-page-heading">
        <div>
          <p className="eyebrow">CUSTOMER ACTIVITY INBOX</p>
          <h2>客户动态</h2>
          <p className="muted">
            外部信息先变成完整 Activity；确定事实自动记录，AI 解释性变化等待人工确认。
          </p>
        </div>
        <button
          className="button primary"
          onClick={() => refresh.mutate()}
          disabled={refresh.isPending}
        >
          {refresh.isPending ? "正在同步并识别…" : "立即刷新"}
        </button>
      </div>

      <div className="sync-grid">
        {query.data?.sync.sources.map((source) => (
          <article className="sync-card" key={source.source}>
            <div>
              <span>{sourceLabels[source.source] ?? source.source}</span>
              <strong>
                {source.last_error ? "同步异常" : "正常"}
              </strong>
            </div>
            <p>最近成功：{formatTime(source.last_success_at)}</p>
            <small>cursor {source.cursor}</small>
          </article>
        ))}
      </div>

      {refresh.data && (
        <div className="success-banner">
          本次新增 {refresh.data.new_count} 条动态，
          新建 {refresh.data.pending_proposals_created} 条待确认状态变化。
        </div>
      )}
      {refresh.error && (
        <div className="error-banner">
          刷新失败：{refresh.error.message}
        </div>
      )}

      <div className="activity-layout">
        <section className="proposal-lane">
          <div className="section-title-row compact-heading">
            <div>
              <p className="eyebrow">NEEDS CONFIRMATION</p>
              <h3>待确认变化</h3>
            </div>
            <span className="section-count">
              {query.data?.pending_proposals.length ?? 0}
            </span>
          </div>

          <div className="proposal-stack">
            {query.data?.pending_proposals.map((proposal) => (
              <article className="proposal-card inbox" key={proposal.id}>
                <div className="proposal-head">
                  <div>
                    <button
                      className="proposal-customer-link"
                      onClick={() => onOpenCustomer(proposal.customer_id)}
                    >
                      {proposal.customer_name ?? proposal.customer_id}
                    </button>
                    <span>
                      {sourceLabels[proposal.source.replace("sync:", "")] ??
                        proposal.source}
                    </span>
                  </div>
                  <span className="confidence-pill">
                    {proposal.confidence == null
                      ? "AI"
                      : String(Math.round(proposal.confidence * 100)) + "%"}
                  </span>
                </div>

                <strong className="proposal-summary">
                  {proposal.extraction_summary}
                </strong>

                <div className="proposal-raw">
                  <span>原始信息</span>
                  <p>{proposal.raw_content}</p>
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

            {!query.isLoading &&
              (query.data?.pending_proposals.length ?? 0) === 0 && (
                <div className="empty-state positive">
                  <strong>没有待确认的状态变化。</strong>
                  <p>点击“立即刷新”可以拉取下一批模拟外部事件。</p>
                </div>
              )}
          </div>
        </section>

        <section className="activity-lane">
          <div className="section-title-row compact-heading">
            <div>
              <p className="eyebrow">FULL ACTIVITY LOG</p>
              <h3>最近动态</h3>
            </div>
            <span className="section-count">
              {query.data?.activities.length ?? 0}
            </span>
          </div>

          <div className="activity-stream">
            {query.data?.activities.map((activity) => (
              <article className="activity-row" key={activity.id}>
                <div className="activity-source-dot" />
                <div className="activity-row-main">
                  <div className="activity-row-head">
                    <button
                      onClick={() => onOpenCustomer(activity.customer_id)}
                      className="activity-customer"
                    >
                      {activity.name ?? activity.customer_id}
                    </button>
                    <span>
                      {sourceLabels[activity.source] ?? activity.source} ·{" "}
                      {formatTime(activity.occurred_at)}
                    </span>
                  </div>
                  <strong>
                    {activity.structured_summary || activity.action_taken}
                  </strong>
                  {activity.raw_content && (
                    <p>{activity.raw_content}</p>
                  )}
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
