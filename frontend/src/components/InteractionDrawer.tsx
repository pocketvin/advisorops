import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  api,
  type IntentLevel,
  type InteractionPayload,
  type RelationshipStage,
} from "../api";

interface Props {
  workItemId: number;
  customerId: string;
  onClose: () => void;
}

const stageOptions: Array<[RelationshipStage, string]> = [
  ["new", "新客户"],
  ["contacted", "已联系"],
  ["interested", "有明确兴趣"],
  ["considering", "考虑中"],
  ["rejected", "近期明确拒绝"],
  ["dormant", "长期沉默"],
];

const intentOptions: Array<[IntentLevel, string]> = [
  ["unknown", "未知"],
  ["low", "低"],
  ["medium", "中"],
  ["high", "高"],
];

function toLocalInput(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  const pad = (number: number) => String(number).padStart(2, "0");
  return [
    date.getFullYear(),
    "-",
    pad(date.getMonth() + 1),
    "-",
    pad(date.getDate()),
    "T",
    pad(date.getHours()),
    ":",
    pad(date.getMinutes()),
  ].join("");
}

function toIso(value: string): string | null {
  if (!value) return null;
  return new Date(value).toISOString();
}

export default function InteractionDrawer({
  workItemId,
  customerId,
  onClose,
}: Props) {
  const queryClient = useQueryClient();
  const detailQuery = useQuery({
    queryKey: ["customer", customerId],
    queryFn: () => api.customer(customerId),
  });

  const customer = detailQuery.data?.customer;
  const [rawContent, setRawContent] = useState("");
  const [summary, setSummary] = useState("");
  const [feedback, setFeedback] = useState("");
  const [actionTaken, setActionTaken] = useState("电话回访");
  const [stage, setStage] = useState<RelationshipStage>("contacted");
  const [intent, setIntent] = useState<IntentLevel>("medium");
  const [need, setNeed] = useState("");
  const [obstacle, setObstacle] = useState("");
  const [nextStep, setNextStep] = useState("");
  const [nextContact, setNextContact] = useState("");
  const [channel, setChannel] = useState<InteractionPayload["channel"]>("phone");
  const [outcome, setOutcome] =
    useState<InteractionPayload["outcome"]>("completed");
  const [waitingOn, setWaitingOn] =
    useState<InteractionPayload["waiting_on"]>("none");

  useEffect(() => {
    if (!customer) return;
    setStage(customer.relationship_stage);
    setIntent(customer.intent_level);
    setNeed(customer.current_need);
    setObstacle(customer.current_obstacle);
    setNextStep(customer.next_step);
    setNextContact(toLocalInput(customer.next_contact_at));
  }, [customer]);

  const mutation = useMutation({
    mutationFn: (payload: InteractionPayload) =>
      api.recordInteraction(workItemId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["workbench"] }),
        queryClient.invalidateQueries({ queryKey: ["customer", customerId] }),
      ]);
      onClose();
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (outcome === "waiting" && waitingOn === "none") {
      return;
    }

    mutation.mutate({
      raw_content: rawContent,
      structured_summary: summary,
      customer_feedback: feedback,
      action_taken: actionTaken,
      relationship_stage: stage,
      intent_level: intent,
      current_need: need,
      current_obstacle: obstacle,
      next_step: nextStep,
      next_contact_at: toIso(nextContact),
      channel,
      outcome,
      waiting_on: outcome === "waiting" ? waitingOn : "none",
    });
  }

  return (
    <div className="drawer-backdrop" role="presentation" onMouseDown={onClose}>
      <aside
        className="drawer drawer-wide"
        aria-label="记录客户沟通"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="drawer-header">
          <div>
            <p className="eyebrow">记录经营进展</p>
            <h2>{customer?.name ?? "正在读取客户…"}</h2>
            <p className="muted">
              当前为人工确认模式。后续 AI 会先自动填充这些字段，再由客户经理确认。
            </p>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </header>

        {detailQuery.isLoading ? (
          <div className="drawer-body">正在读取客户状态…</div>
        ) : (
          <form className="drawer-body interaction-form" onSubmit={submit}>
            <section className="form-section">
              <div className="section-heading">
                <span>01</span>
                <div>
                  <h3>刚刚发生了什么</h3>
                  <p>原始记录会完整保留，不能被结构化字段替代。</p>
                </div>
              </div>

              <label className="field">
                <span>原始沟通记录</span>
                <textarea
                  required
                  rows={5}
                  value={rawContent}
                  onChange={(event) => setRawContent(event.target.value)}
                  placeholder="例如：刚刚给张总打了电话，他说方案看过了，但是还想再考虑三天……"
                />
              </label>

              <div className="field-grid">
                <label className="field">
                  <span>渠道</span>
                  <select
                    value={channel}
                    onChange={(event) =>
                      setChannel(event.target.value as InteractionPayload["channel"])
                    }
                  >
                    <option value="phone">电话</option>
                    <option value="wecom">企业微信</option>
                    <option value="meeting">线下</option>
                    <option value="app">App</option>
                    <option value="other">其他</option>
                  </select>
                </label>
                <label className="field">
                  <span>本次动作</span>
                  <input
                    value={actionTaken}
                    onChange={(event) => setActionTaken(event.target.value)}
                  />
                </label>
              </div>
            </section>

            <section className="form-section">
              <div className="section-heading">
                <span>02</span>
                <div>
                  <h3>确认系统要沉淀的经营信息</h3>
                  <p>这一层未来由 AI 预填，但现在先验证状态逻辑。</p>
                </div>
              </div>

              <label className="field">
                <span>结构化经营摘要</span>
                <textarea
                  required
                  rows={3}
                  value={summary}
                  onChange={(event) => setSummary(event.target.value)}
                  placeholder="一句话说明本次沟通结果和当前进展。"
                />
              </label>

              <label className="field">
                <span>客户反馈</span>
                <textarea
                  rows={2}
                  value={feedback}
                  onChange={(event) => setFeedback(event.target.value)}
                  placeholder="尽量保留客户原意。"
                />
              </label>

              <div className="field-grid">
                <label className="field">
                  <span>关系阶段</span>
                  <select
                    value={stage}
                    onChange={(event) =>
                      setStage(event.target.value as RelationshipStage)
                    }
                  >
                    {stageOptions.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>当前意向</span>
                  <select
                    value={intent}
                    onChange={(event) =>
                      setIntent(event.target.value as IntentLevel)
                    }
                  >
                    {intentOptions.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <label className="field">
                <span>当前需求</span>
                <input value={need} onChange={(event) => setNeed(event.target.value)} />
              </label>

              <label className="field">
                <span>当前障碍</span>
                <input
                  value={obstacle}
                  onChange={(event) => setObstacle(event.target.value)}
                  placeholder="例如：近期可能有资金使用安排"
                />
              </label>
            </section>

            <section className="form-section">
              <div className="section-heading">
                <span>03</span>
                <div>
                  <h3>下一步怎么走</h3>
                  <p>完成后退出今日待处理；等待中则继续留在工作区。</p>
                </div>
              </div>

              <label className="field">
                <span>下一步动作</span>
                <input
                  value={nextStep}
                  onChange={(event) => setNextStep(event.target.value)}
                  placeholder="例如：三天后按约定回访"
                />
              </label>

              <label className="field">
                <span>下一次检查 / 联系时间</span>
                <input
                  type="datetime-local"
                  value={nextContact}
                  onChange={(event) => setNextContact(event.target.value)}
                />
              </label>

              <div className="choice-row">
                <button
                  type="button"
                  className={outcome === "completed" ? "choice active" : "choice"}
                  onClick={() => {
                    setOutcome("completed");
                    setWaitingOn("none");
                  }}
                >
                  <strong>本次已完成</strong>
                  <span>退出当前工作区，未来到期再发现</span>
                </button>
                <button
                  type="button"
                  className={outcome === "waiting" ? "choice active" : "choice"}
                  onClick={() => {
                    setOutcome("waiting");
                    if (waitingOn === "none") setWaitingOn("customer");
                  }}
                >
                  <strong>继续等待</strong>
                  <span>留在工作区，不重复进入发现区</span>
                </button>
              </div>

              {outcome === "waiting" && (
                <label className="field">
                  <span>现在在等谁 / 什么</span>
                  <select
                    value={waitingOn}
                    onChange={(event) =>
                      setWaitingOn(
                        event.target.value as InteractionPayload["waiting_on"],
                      )
                    }
                  >
                    <option value="customer">等待客户</option>
                    <option value="manager">待我继续处理</option>
                    <option value="internal">等待内部资料</option>
                    <option value="scheduled_time">等待约定时间</option>
                  </select>
                </label>
              )}
            </section>

            {mutation.error && (
              <div className="error-banner">{mutation.error.message}</div>
            )}

            <footer className="form-actions">
              <button type="button" className="button secondary" onClick={onClose}>
                取消
              </button>
              <button
                type="submit"
                className="button primary"
                disabled={
                  mutation.isPending ||
                  !rawContent.trim() ||
                  !summary.trim() ||
                  (outcome === "waiting" && waitingOn === "none")
                }
              >
                {mutation.isPending ? "正在保存…" : "确认并更新客户"}
              </button>
            </footer>
          </form>
        )}
      </aside>
    </div>
  );
}
