import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type DiscoveryItem, type WorkItem } from "../api";
import DeferDialog from "./DeferDialog";
import WorkLifecycleDialog from "./WorkLifecycleDialog";

interface Props {
  onOpenCustomer: (customerId: string) => void;
  onRecordWork: (workItemId: number, customerId: string) => void;
}

function formatTime(value: string | null | undefined): string {
  if (!value) return "未安排";
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
  unknown: "意向未知",
  low: "低意向",
  medium: "中意向",
  high: "高意向",
};

function Metric({
  label,
  value,
  note,
}: {
  label: string;
  value: number;
  note: string;
}) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{note}</p>
    </div>
  );
}

function WorkCard({
  item,
  variant,
  onRecord,
  onDetail,
  onCancel,
  onComplete,
  lifecyclePending,
}: {
  item: WorkItem;
  variant: "action" | "waiting";
  onRecord: () => void;
  onDetail: () => void;
  onCancel: () => void;
  onComplete: () => void;
  lifecyclePending: boolean;
}) {
  return (
    <article className="work-card">
      <div className="work-card-head">
        <div>
          <div className="identity-line">
            <h3>{item.name ?? item.customer_id}</h3>
            <span>{"服务·" + (item.customer_level ?? "未设置")}</span>
          </div>
          <p className="muted small">
            {stageLabels[item.relationship_stage ?? ""] ?? item.relationship_stage} ·{" "}
            {intentLabels[item.intent_level ?? ""] ?? item.intent_level}
          </p>
        </div>
        <span className={variant === "waiting" ? "status-pill waiting" : "status-pill"}>
          {variant === "waiting" ? "等待中" : "待我处理"}
        </span>
      </div>

      <div className="work-progress">
        <span>当前进展</span>
        <p>{item.current_progress || item.customer_progress || "已进入今日工作区"}</p>
      </div>

      <div className="next-action-row">
        <div>
          <span>下一步</span>
          <strong>{item.next_action || item.customer_next_step || "继续推进"}</strong>
        </div>
        <div className="right-align">
          <span>{variant === "waiting" ? "检查时间" : "计划时间"}</span>
          <strong>{formatTime(item.due_at)}</strong>
        </div>
      </div>

      {variant === "waiting" && (
        <div className="waiting-note">
          当前责任方：
          {item.waiting_on === "customer"
            ? "客户"
            : item.waiting_on === "internal"
              ? "内部资料"
              : item.waiting_on}
        </div>
      )}

      <div className="card-actions work-card-actions">
        <button className="button ghost" onClick={onDetail}>
          查看详情
        </button>
        <div className="work-terminal-actions">
          <button
            className="text-button work-cancel-button"
            onClick={onCancel}
            disabled={lifecyclePending}
          >
            取消跟进
          </button>
          <button
            className="button secondary compact"
            onClick={onComplete}
            disabled={lifecyclePending}
          >
            结束跟进
          </button>
          <button
            className="button primary compact"
            onClick={onRecord}
            disabled={lifecyclePending}
          >
            记录进展
          </button>
        </div>
      </div>
    </article>
  );
}

function DiscoveryCard({
  item,
  onStart,
  onDefer,
  onDetail,
  starting,
  deferring,
}: {
  item: DiscoveryItem;
  onStart: () => void;
  onDefer: () => void;
  onDetail: () => void;
  starting: boolean;
  deferring: boolean;
}) {
  const { customer, discovery } = item;
  const visibleFactors = discovery.factors.slice(0, 3);

  return (
    <article className="discovery-card">
      <div className="discovery-rank-block">
        <span className="score-label">今日优先级</span>
        <strong>{discovery.score}</strong>
        <span className={"priority-level " + discovery.level}>
          {discovery.level === "high"
            ? "高"
            : discovery.level === "medium"
              ? "中"
              : "常规"}
        </span>
      </div>

      <div className="discovery-main">
        <div className="discovery-head">
          <div>
            <div className="identity-line">
              <h3>{customer.name}</h3>
              <span>{"服务·" + customer.customer_level}</span>
              {customer.pinned && <span className="pin-tag">人工关注</span>}
            </div>
            <p className="muted small">
              {stageLabels[customer.relationship_stage]} ·{" "}
              {intentLabels[customer.intent_level]} · 上次联系{" "}
              {formatTime(customer.last_contact_at)}
            </p>
          </div>
          <button className="text-button" onClick={onDetail}>
            查看客户 →
          </button>
        </div>

        <div className="reason-callout">
          <span>为什么现在值得关注</span>
          <strong>{discovery.actionable_reason}</strong>
        </div>

        <div className="factor-list">
          {visibleFactors.map((factor) => (
            <div className="factor-row" key={factor.code}>
              <span>{factor.label}</span>
              <p>{factor.evidence}</p>
              <strong>{factor.points > 0 ? "+" : ""}{factor.points}</strong>
            </div>
          ))}
        </div>

        <div className="suggested-action">
          <div>
            <span>建议下一步</span>
            <p>{discovery.suggested_action}</p>
          </div>
          <div className="discovery-actions">
            <button
              className="button ghost compact"
              onClick={onDefer}
              disabled={deferring}
            >
              {deferring ? "正在设置…" : "稍后跟进"}
            </button>
            <button
              className="button primary"
              onClick={onStart}
              disabled={starting}
            >
              {starting ? "正在进入工作区…" : "开始跟进"}
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}

export default function WorkbenchView({ onOpenCustomer, onRecordWork }: Props) {
  const queryClient = useQueryClient();
  const [deferTarget, setDeferTarget] = useState<{ customerId: string; name: string } | null>(null);
  const [lifecycleTarget, setLifecycleTarget] = useState<{
    item: WorkItem;
    mode: "cancel" | "complete";
  } | null>(null);
  const workbenchQuery = useQuery({
    queryKey: ["workbench"],
    queryFn: api.workbench,
  });

  const deferMutation = useMutation({
    mutationFn: ({ customerId, payload }: {
      customerId: string;
      payload: { days?: number; next_contact_at?: string };
    }) => api.deferCustomer(customerId, payload),
    onSuccess: async (_, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["workbench"] }),
        queryClient.invalidateQueries({ queryKey: ["customers"] }),
        queryClient.invalidateQueries({ queryKey: ["customer", variables.customerId] }),
      ]);
      setDeferTarget(null);
    },
  });

  const lifecycleMutation = useMutation({
    mutationFn: async ({
      item,
      mode,
    }: {
      item: WorkItem;
      mode: "cancel" | "complete";
    }) => {
      return mode === "cancel"
        ? api.cancelWork(item.id)
        : api.completeWork(item.id);
    },
    onSuccess: async (result) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["workbench"] }),
        queryClient.invalidateQueries({ queryKey: ["customers"] }),
        queryClient.invalidateQueries({
          queryKey: ["customer", result.customer.customer_id],
        }),
        queryClient.invalidateQueries({ queryKey: ["activities"] }),
      ]);
      setLifecycleTarget(null);
    },
  });

  const startMutation = useMutation({
    mutationFn: api.startWork,
    onSuccess: async (workItem) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["workbench"] }),
        queryClient.invalidateQueries({ queryKey: ["customers"] }),
        queryClient.invalidateQueries({
          queryKey: ["customer", workItem.customer_id],
        }),
      ]);
      onRecordWork(workItem.id, workItem.customer_id);
    },
  });

  const data = workbenchQuery.data;
  const workCount = useMemo(
    () =>
      (data?.summary.action_required ?? 0) +
      (data?.summary.waiting ?? 0),
    [data],
  );

  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">TODAY · 经营执行</p>
          <h2>先把手上的事做完，再决定下一个联系谁。</h2>
          <p>
            工作区管理已经接下来的客户；发现区只展示当前真正存在新行动理由的客户，
            最近处理完的人不会混回来。
          </p>
        </div>
        <div className="hero-rule">
          <span>产品原则</span>
          <strong>AI 负责理解，规则负责约束，人负责决策。</strong>
        </div>
      </section>

      {workbenchQuery.error && (
        <div className="error-banner">
          无法读取工作台：{workbenchQuery.error.message}
        </div>
      )}

      <section className="metrics">
        <Metric
          label="待我处理"
          value={data?.summary.action_required ?? 0}
          note="下一步动作在我这边"
        />
        <Metric
          label="等待中"
          value={data?.summary.waiting ?? 0}
          note="正在等待客户或内部信息"
        />
        <Metric
          label="今日完成"
          value={data?.summary.completed_today ?? 0}
          note="今天已经形成闭环"
        />
        <Metric
          label="新发现"
          value={data?.summary.discovery ?? 0}
          note="当前值得新发起动作"
        />
      </section>

      <section className="workspace-section">
        <div className="section-title-row">
          <div>
            <p className="eyebrow">EXECUTION QUEUE</p>
            <h2>我的工作区</h2>
            <p className="muted">
              已经决定处理的事情不再参与发现区排序，避免重复推荐。
            </p>
          </div>
          <span className="section-count">{workCount} 个进行中</span>
        </div>

        {workbenchQuery.isLoading ? (
          <div className="empty-state">正在读取今天的工作…</div>
        ) : workCount === 0 ? (
          <div className="empty-state positive">
            <strong>现在没有未完成的工作项。</strong>
            <p>可以从下方发现区选择下一位客户开始处理。</p>
          </div>
        ) : (
          <div className="work-columns">
            <div>
              <div className="lane-heading">
                <span>待我处理</span>
                <strong>{data?.work_area.action_required.length ?? 0}</strong>
              </div>
              <div className="card-stack">
                {data?.work_area.action_required.map((item) => (
                  <WorkCard
                    key={item.id}
                    item={item}
                    variant="action"
                    onDetail={() => onOpenCustomer(item.customer_id)}
                    onRecord={() => onRecordWork(item.id, item.customer_id)}
                    onCancel={() =>
                      setLifecycleTarget({ item, mode: "cancel" })
                    }
                    onComplete={() =>
                      setLifecycleTarget({ item, mode: "complete" })
                    }
                    lifecyclePending={
                      lifecycleMutation.isPending &&
                      lifecycleMutation.variables?.item.id === item.id
                    }
                  />
                ))}
              </div>
            </div>

            <div>
              <div className="lane-heading">
                <span>等待中</span>
                <strong>{data?.work_area.waiting.length ?? 0}</strong>
              </div>
              <div className="card-stack">
                {data?.work_area.waiting.map((item) => (
                  <WorkCard
                    key={item.id}
                    item={item}
                    variant="waiting"
                    onDetail={() => onOpenCustomer(item.customer_id)}
                    onRecord={() => onRecordWork(item.id, item.customer_id)}
                    onCancel={() =>
                      setLifecycleTarget({ item, mode: "cancel" })
                    }
                    onComplete={() =>
                      setLifecycleTarget({ item, mode: "complete" })
                    }
                    lifecyclePending={
                      lifecycleMutation.isPending &&
                      lifecycleMutation.variables?.item.id === item.id
                    }
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {(data?.work_area.completed_today.length ?? 0) > 0 && (
          <details className="completed-panel">
            <summary>
              <span>今日已完成</span>
              <strong>{data?.work_area.completed_today.length}</strong>
            </summary>
            <div className="completed-list">
              {data?.work_area.completed_today.map((item) => (
                <button
                  className="completed-row"
                  key={item.id}
                  onClick={() => onOpenCustomer(item.customer_id)}
                >
                  <div>
                    <strong>{item.name ?? item.customer_id}</strong>
                    <span>{item.current_progress}</span>
                  </div>
                  <span>{formatTime(item.completed_at)}</span>
                </button>
              ))}
            </div>
          </details>
        )}
      </section>

      <section className="discovery-section">
        <div className="section-title-row">
          <div>
            <p className="eyebrow">DISCOVERY QUEUE</p>
            <h2>建议跟进客户</h2>
            <p className="muted">
              先判断“现在是否真的有行动理由”，再进行可解释排序。
            </p>
          </div>
          <div className="legend">
            <span>排序 ≠ 成交概率</span>
            <span>排序 ≠ 客户价值</span>
          </div>
        </div>

        <div className="discovery-list">
          {data?.discovery.map((item) => (
            <DiscoveryCard
              key={item.customer.customer_id}
              item={item}
              starting={
                startMutation.isPending &&
                startMutation.variables === item.customer.customer_id
              }
              deferring={
                deferMutation.isPending &&
                deferMutation.variables?.customerId === item.customer.customer_id
              }
              onDetail={() => onOpenCustomer(item.customer.customer_id)}
              onStart={() => startMutation.mutate(item.customer.customer_id)}
              onDefer={() =>
                setDeferTarget({
                  customerId: item.customer.customer_id,
                  name: item.customer.name,
                })
              }
            />
          ))}

          {!workbenchQuery.isLoading && (data?.discovery.length ?? 0) === 0 && (
            <div className="empty-state">
              当前没有新的可执行发现理由。
            </div>
          )}
        </div>

        {startMutation.error && (
          <div className="error-banner">{startMutation.error.message}</div>
        )}
        {lifecycleMutation.error && (
          <div className="error-banner">{lifecycleMutation.error.message}</div>
        )}
      </section>

      {lifecycleTarget && (
        <WorkLifecycleDialog
          mode={lifecycleTarget.mode}
          customerName={
            lifecycleTarget.item.name ?? lifecycleTarget.item.customer_id
          }
          pending={lifecycleMutation.isPending}
          onClose={() => setLifecycleTarget(null)}
          onConfirm={() =>
            lifecycleMutation.mutate({
              item: lifecycleTarget.item,
              mode: lifecycleTarget.mode,
            })
          }
        />
      )}

      {deferTarget && (
        <DeferDialog
          customerName={deferTarget.name}
          baseTime={data?.demo_time}
          pending={deferMutation.isPending}
          onClose={() => setDeferTarget(null)}
          onConfirm={(payload) =>
            deferMutation.mutate({
              customerId: deferTarget.customerId,
              payload,
            })
          }
        />
      )}
    </>
  );
}
