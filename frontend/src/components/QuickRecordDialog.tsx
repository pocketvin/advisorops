import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  api,
  type IntentLevel,
  type InteractionPayload,
  type QuickRecordPreparation,
  type RelationshipStage,
} from "../api";

interface Props {
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

function futureLocalInput(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
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

export default function QuickRecordDialog({ onClose }: Props) {
  const queryClient = useQueryClient();
  const [rawContent, setRawContent] = useState("");
  const [channel, setChannel] =
    useState<InteractionPayload["channel"]>("phone");
  const [prepared, setPrepared] = useState<QuickRecordPreparation | null>(null);

  const [summary, setSummary] = useState("");
  const [feedback, setFeedback] = useState("");
  const [actionTaken, setActionTaken] = useState("客户沟通");
  const [stage, setStage] = useState<RelationshipStage>("contacted");
  const [intent, setIntent] = useState<IntentLevel>("medium");
  const [need, setNeed] = useState("");
  const [obstacle, setObstacle] = useState("");
  const [managerNote, setManagerNote] = useState("");
  const [nextStep, setNextStep] = useState("");
  const [nextContact, setNextContact] = useState("");
  const [outcome, setOutcome] =
    useState<InteractionPayload["outcome"]>("completed");
  const [waitingOn, setWaitingOn] =
    useState<InteractionPayload["waiting_on"]>("none");

  function clearPrepared() {
    setPrepared(null);
  }

  const prepareMutation = useMutation({
    mutationFn: () =>
      api.quickRecordPrepare({
        raw_content: rawContent,
        channel,
      }),
    onSuccess: (result) => {
      const suggestion = result.suggested_interaction;
      setPrepared(result);
      setSummary(suggestion.structured_summary);
      setFeedback(suggestion.customer_feedback);
      setStage(suggestion.relationship_stage);
      setIntent(suggestion.intent_level);
      setNeed(suggestion.current_need);
      setObstacle(suggestion.current_obstacle);
      setNextStep(suggestion.next_step);
      setNextContact(toLocalInput(suggestion.next_contact_at));
      setOutcome(suggestion.outcome);
      setWaitingOn(
        suggestion.outcome === "waiting" ? suggestion.waiting_on : "none",
      );
    },
  });

  const saveMutation = useMutation({
    mutationFn: async (payload: InteractionPayload) => {
      if (!prepared) throw new Error("请先识别客户并整理记录");
      const work = await api.manualWork(prepared.customer.customer_id);
      return api.recordInteraction(work.id, payload);
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["workbench"] }),
        queryClient.invalidateQueries({ queryKey: ["customers"] }),
        queryClient.invalidateQueries({ queryKey: ["activities"] }),
        queryClient.invalidateQueries({ queryKey: ["customer"] }),
      ]);
      onClose();
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!prepared) return;
    if (outcome === "waiting" && waitingOn === "none") return;

    saveMutation.mutate({
      raw_content: rawContent,
      structured_summary: summary,
      customer_feedback: feedback,
      action_taken: actionTaken,
      relationship_stage: stage,
      intent_level: intent,
      current_need: need,
      current_obstacle: obstacle,
      manager_note: managerNote,
      next_step: nextStep,
      next_contact_at: toIso(nextContact),
      channel,
      outcome,
      waiting_on: outcome === "waiting" ? waitingOn : "none",
    });
  }

  return (
    <div className="quick-record-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="quick-record-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="全局记录客户进展"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="quick-record-header">
          <div>
            <p className="eyebrow">GLOBAL QUICK RECORD</p>
            <h2>记录客户进展</h2>
            <p>
              直接写“周婷刚刚……”即可。系统先确定客户，再整理本次进展；
              不需要先进入客户详情。
            </p>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </header>

        <form className="quick-record-body" onSubmit={submit}>
          <section className="quick-record-input-card">
            <label className="field quick-record-main-field">
              <span>发生了什么</span>
              <textarea
                autoFocus
                required
                rows={5}
                value={rawContent}
                onChange={(event) => {
                  setRawContent(event.target.value);
                  clearPrepared();
                }}
                placeholder="例如：周婷刚刚电话说资料已经看过了，明天下午回复我。"
              />
            </label>

            <div className="quick-record-input-actions">
              <label className="field inline-field">
                <span>渠道</span>
                <select
                  value={channel}
                  onChange={(event) => {
                    setChannel(
                      event.target.value as InteractionPayload["channel"],
                    );
                    clearPrepared();
                  }}
                >
                  <option value="phone">电话</option>
                  <option value="wecom">企业微信</option>
                  <option value="meeting">线下</option>
                  <option value="app">App</option>
                  <option value="other">其他</option>
                </select>
              </label>
              <button
                type="button"
                className="button primary"
                disabled={!rawContent.trim() || prepareMutation.isPending}
                onClick={() => prepareMutation.mutate()}
              >
                {prepareMutation.isPending ? "正在识别并整理…" : "识别客户并整理"}
              </button>
            </div>

            {prepareMutation.error && (
              <div className="error-banner">
                {prepareMutation.error.message}
              </div>
            )}
          </section>

          {prepared && (
            <>
              <section className="quick-record-match">
                <div>
                  <span>已识别客户</span>
                  <strong>{prepared.customer.name}</strong>
                  <small>
                    {prepared.customer.customer_id} · 服务层级{" "}
                    {prepared.customer.customer_level} ·{" "}
                    {prepared.customer.risk_level}
                  </small>
                </div>
                <div className="quick-record-ai-status">
                  {prepared.ai_ready ? (
                    <>
                      <strong>智能整理完成</strong>
                      <span>
                        候选结果仅用于预填，确认保存后才会改变客户状态。
                      </span>
                    </>
                  ) : (
                    <>
                      <strong>已识别客户</strong>
                      <span>{prepared.warning}</span>
                    </>
                  )}
                </div>
              </section>

              <div className="quick-record-grid">
                <section className="quick-record-panel">
                  <div className="section-heading">
                    <span>01</span>
                    <div>
                      <h3>本次记录</h3>
                      <p>原话完整保留，结构化信息可以继续修改。</p>
                    </div>
                  </div>

                  <label className="field">
                    <span>结构化摘要</span>
                    <textarea
                      required
                      rows={3}
                      value={summary}
                      onChange={(event) => setSummary(event.target.value)}
                      placeholder="确认这次到底发生了什么。"
                    />
                  </label>

                  <label className="field">
                    <span>客户反馈</span>
                    <textarea
                      rows={2}
                      value={feedback}
                      onChange={(event) => setFeedback(event.target.value)}
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
                    <input
                      value={need}
                      onChange={(event) => setNeed(event.target.value)}
                    />
                  </label>

                  <label className="field">
                    <span>当前障碍</span>
                    <input
                      value={obstacle}
                      onChange={(event) => setObstacle(event.target.value)}
                    />
                  </label>
                </section>

                <section className="quick-record-panel">
                  <div className="section-heading">
                    <span>02</span>
                    <div>
                      <h3>下一步</h3>
                      <p>确认后直接写入档案和工作流。</p>
                    </div>
                  </div>

                  <label className="field">
                    <span>本次动作</span>
                    <input
                      value={actionTaken}
                      onChange={(event) => setActionTaken(event.target.value)}
                    />
                  </label>

                  <label className="field">
                    <span>下一步动作</span>
                    <input
                      value={nextStep}
                      onChange={(event) => setNextStep(event.target.value)}
                    />
                  </label>

                  <label className="field">
                    <span>下次检查 / 联系时间</span>
                    <input
                      type="datetime-local"
                      value={nextContact}
                      onChange={(event) => setNextContact(event.target.value)}
                    />
                  </label>

                  <label className="field">
                    <span>客户经理备注</span>
                    <textarea
                      rows={2}
                      value={managerNote}
                      onChange={(event) => setManagerNote(event.target.value)}
                      placeholder="只写需要长期保留的补充信息。"
                    />
                  </label>

                  <div className="quick-action-row">
                    <button
                      type="button"
                      className="quick-action reject"
                      onClick={() => {
                        setStage("rejected");
                        setIntent("low");
                        setOutcome("completed");
                        setWaitingOn("none");
                        setNextStep("");
                        setNextContact("");
                        if (!summary.trim()) {
                          setSummary("客户明确表示近期暂无需求，本次主动跟进结束。");
                        }
                      }}
                    >
                      明确拒绝
                    </button>
                    <button
                      type="button"
                      className="quick-action"
                      onClick={() => {
                        setStage("considering");
                        if (intent === "unknown" || intent === "low") {
                          setIntent("medium");
                        }
                        setOutcome("completed");
                        setWaitingOn("none");
                        setNextStep("三天后按约定回访");
                        setNextContact(futureLocalInput(3));
                      }}
                    >
                      再考虑 3 天
                    </button>
                  </div>

                  <div className="choice-row">
                    <button
                      type="button"
                      className={
                        outcome === "completed" ? "choice active" : "choice"
                      }
                      onClick={() => {
                        setOutcome("completed");
                        setWaitingOn("none");
                      }}
                    >
                      <strong>本次已完成</strong>
                      <span>后续按新的时间再次进入发现区</span>
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
                      <span>继续留在工作区</span>
                    </button>
                  </div>

                  {outcome === "waiting" && (
                    <label className="field">
                      <span>当前在等谁 / 什么</span>
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
              </div>

              {saveMutation.error && (
                <div className="error-banner">{saveMutation.error.message}</div>
              )}
            </>
          )}

          <footer className="quick-record-footer">
            <span>
              {prepared
                ? "将记录到：" + prepared.customer.name
                : "先写明客户姓名或客户编号。"}
            </span>
            <div>
              <button type="button" className="button secondary" onClick={onClose}>
                取消
              </button>
              <button
                type="submit"
                className="button primary"
                disabled={
                  !prepared ||
                  !summary.trim() ||
                  saveMutation.isPending ||
                  (outcome === "waiting" && waitingOn === "none")
                }
              >
                {saveMutation.isPending ? "正在记录…" : "确认记录"}
              </button>
            </div>
          </footer>
        </form>
      </section>
    </div>
  );
}
