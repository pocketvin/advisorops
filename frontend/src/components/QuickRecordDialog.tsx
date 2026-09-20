import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  api,
  type ImageAttachmentInput,
  type IntentLevel,
  type InteractionPayload,
  type QuickRecordPreparation,
  type RelationshipStage,
} from "../api";
import ImageAttachmentPicker from "./ImageAttachmentPicker";

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

function stageLabel(value: RelationshipStage): string {
  return stageOptions.find(([key]) => key === value)?.[1] ?? value;
}

function intentLabel(value: IntentLevel): string {
  return intentOptions.find(([key]) => key === value)?.[1] ?? value;
}

export default function QuickRecordDialog({ onClose }: Props) {
  const queryClient = useQueryClient();
  const [rawContent, setRawContent] = useState("");
  const [attachments, setAttachments] = useState<ImageAttachmentInput[]>([]);
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

  function invalidatePrepared() {
    setPrepared(null);
  }

  const prepareMutation = useMutation({
    mutationFn: () =>
      api.quickRecordPrepare({
        raw_content: rawContent,
        channel,
        attachments,
      }),
    onSuccess: (result) => {
      const suggestion = result.suggested_interaction;
      setPrepared(result);
      setSummary(
        suggestion.structured_summary ||
          rawContent.trim() ||
          "本次沟通包含图片附件。",
      );
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
      attachments,
    });
  }

  const canPrepare = rawContent.trim().length > 0;

  return (
    <div className="quick-record-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="quick-record-dialog quick-record-dialog-simple"
        role="dialog"
        aria-modal="true"
        aria-label="全局记录客户进展"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="quick-record-header">
          <div>
            <p className="eyebrow">QUICK RECORD</p>
            <h2>记录进展</h2>
            <p>
              直接写“周婷刚刚……”并可附聊天截图。系统先确认客户，再帮你整理；
              默认不需要填业务表格。
            </p>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </header>

        <form className="quick-record-body" onSubmit={submit}>
          <section className="conversation-capture">
            <textarea
              autoFocus
              rows={5}
              value={rawContent}
              onChange={(event) => {
                setRawContent(event.target.value);
                invalidatePrepared();
              }}
              placeholder="例如：周婷刚刚电话说资料看过了，今晚和家里人商量，明天下午回复我。"
            />

            <div className="conversation-toolbar">
              <ImageAttachmentPicker
                attachments={attachments}
                onChange={(value) => {
                  setAttachments(value);
                  invalidatePrepared();
                }}
              />
              <div className="conversation-actions">
                <select
                  value={channel}
                  onChange={(event) => {
                    setChannel(
                      event.target.value as InteractionPayload["channel"],
                    );
                    invalidatePrepared();
                  }}
                >
                  <option value="phone">电话</option>
                  <option value="wecom">企业微信</option>
                  <option value="meeting">线下</option>
                  <option value="app">App</option>
                  <option value="other">其他</option>
                </select>
                <button
                  type="button"
                  className="button primary"
                  disabled={!canPrepare || prepareMutation.isPending}
                  onClick={() => prepareMutation.mutate()}
                >
                  {prepareMutation.isPending ? "正在整理…" : "智能整理"}
                </button>
              </div>
            </div>

            {prepareMutation.error && (
              <div className="error-banner">{prepareMutation.error.message}</div>
            )}
          </section>

          {prepared && (
            <>
              <section className="record-review-card">
                <div className="record-review-head">
                  <div>
                    <span>已识别客户</span>
                    <strong>{prepared.customer.name}</strong>
                    <small>
                      {prepared.customer.customer_id} · 服务{" "}
                      {prepared.customer.customer_level}
                    </small>
                  </div>
                  <span className="review-ready">
                    {prepared.ai_ready ? "已整理，等待确认" : "已识别客户"}
                  </span>
                </div>

                {prepared.warning && (
                  <div className="warning-banner">{prepared.warning}</div>
                )}

                <div className="record-review-summary">
                  <span>本次进展</span>
                  <p>{summary || "尚未生成摘要"}</p>
                  {feedback && <blockquote>{feedback}</blockquote>}
                </div>

                <div className="review-facts">
                  <div>
                    <span>状态</span>
                    <strong>{stageLabel(stage)} · {intentLabel(intent)}意向</strong>
                  </div>
                  <div>
                    <span>下一步</span>
                    <strong>{nextStep || "暂无明确下一步"}</strong>
                  </div>
                  <div>
                    <span>时间</span>
                    <strong>
                      {nextContact
                        ? new Date(nextContact).toLocaleString("zh-CN", {
                            month: "2-digit",
                            day: "2-digit",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "未设置"}
                    </strong>
                  </div>
                  <div>
                    <span>本次结果</span>
                    <strong>{outcome === "waiting" ? "继续等待" : "本次完成"}</strong>
                  </div>
                </div>
              </section>

              <details className="advanced-record-editor">
                <summary>识别不准确？展开修改详细字段</summary>
                <div className="advanced-record-grid">
                  <label className="field wide">
                    <span>结构化摘要</span>
                    <textarea
                      rows={3}
                      value={summary}
                      onChange={(event) => setSummary(event.target.value)}
                    />
                  </label>
                  <label className="field wide">
                    <span>客户反馈</span>
                    <textarea
                      rows={2}
                      value={feedback}
                      onChange={(event) => setFeedback(event.target.value)}
                    />
                  </label>
                  <label className="field">
                    <span>关系阶段</span>
                    <select
                      value={stage}
                      onChange={(event) =>
                        setStage(event.target.value as RelationshipStage)
                      }
                    >
                      {stageOptions.map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
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
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field wide">
                    <span>当前需求</span>
                    <input value={need} onChange={(event) => setNeed(event.target.value)} />
                  </label>
                  <label className="field wide">
                    <span>当前障碍</span>
                    <input
                      value={obstacle}
                      onChange={(event) => setObstacle(event.target.value)}
                    />
                  </label>
                  <label className="field">
                    <span>本次动作</span>
                    <input
                      value={actionTaken}
                      onChange={(event) => setActionTaken(event.target.value)}
                    />
                  </label>
                  <label className="field">
                    <span>下次联系时间</span>
                    <input
                      type="datetime-local"
                      value={nextContact}
                      onChange={(event) => setNextContact(event.target.value)}
                    />
                  </label>
                  <label className="field wide">
                    <span>下一步动作</span>
                    <input
                      value={nextStep}
                      onChange={(event) => setNextStep(event.target.value)}
                    />
                  </label>
                  <label className="field wide">
                    <span>客户经理备注</span>
                    <textarea
                      rows={2}
                      value={managerNote}
                      onChange={(event) => setManagerNote(event.target.value)}
                    />
                  </label>

                  <div className="advanced-outcome wide">
                    <button
                      type="button"
                      className={outcome === "completed" ? "choice active" : "choice"}
                      onClick={() => {
                        setOutcome("completed");
                        setWaitingOn("none");
                      }}
                    >
                      <strong>本次已完成</strong>
                      <span>退出当前工作项</span>
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
                    <label className="field wide">
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
                </div>
              </details>

              {saveMutation.error && (
                <div className="error-banner">{saveMutation.error.message}</div>
              )}
            </>
          )}

          <footer className="quick-record-footer">
            <span>
              {prepared
                ? "将记录到：" + prepared.customer.name
                : "请在文字中写明客户姓名或编号。"}
            </span>
            <div>
              <button type="button" className="button secondary" onClick={onClose}>
                取消
              </button>
              <button
                type="submit"
                className="button primary"
                disabled={!prepared || !summary.trim() || saveMutation.isPending}
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
