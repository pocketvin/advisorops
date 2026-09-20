import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  api,
  type ImageAttachmentInput,
  type IntentLevel,
  type InteractionPayload,
  type RelationshipStage,
} from "../api";
import ImageAttachmentPicker from "./ImageAttachmentPicker";
import WorkLifecycleDialog from "./WorkLifecycleDialog";

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

function stageLabel(value: RelationshipStage): string {
  return stageOptions.find(([key]) => key === value)?.[1] ?? value;
}

function intentLabel(value: IntentLevel): string {
  return intentOptions.find(([key]) => key === value)?.[1] ?? value;
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
  const [attachments, setAttachments] = useState<ImageAttachmentInput[]>([]);
  const [summary, setSummary] = useState("");
  const [feedback, setFeedback] = useState("");
  const [actionTaken, setActionTaken] = useState("客户跟进");
  const [stage, setStage] = useState<RelationshipStage>("contacted");
  const [intent, setIntent] = useState<IntentLevel>("medium");
  const [need, setNeed] = useState("");
  const [obstacle, setObstacle] = useState("");
  const [managerNote, setManagerNote] = useState("");
  const [nextStep, setNextStep] = useState("");
  const [nextContact, setNextContact] = useState("");
  const [channel, setChannel] =
    useState<InteractionPayload["channel"]>("phone");
  const [outcome, setOutcome] =
    useState<InteractionPayload["outcome"]>("completed");
  const [waitingOn, setWaitingOn] =
    useState<InteractionPayload["waiting_on"]>("none");
  const [proposalId, setProposalId] = useState<number | null>(null);
  const [reviewReady, setReviewReady] = useState(false);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [completeConfirmOpen, setCompleteConfirmOpen] = useState(false);

  useEffect(() => {
    if (!customer) return;
    setStage(customer.relationship_stage);
    setIntent(customer.intent_level);
    setNeed(customer.current_need);
    setObstacle(customer.current_obstacle);
    setManagerNote(customer.manager_note);
    setNextStep(customer.next_step);
    setNextContact(toLocalInput(customer.next_contact_at));
  }, [customer]);

  function invalidateReview() {
    setReviewReady(false);
    setProposalId(null);
    setConfidence(null);
  }

  const aiMutation = useMutation({
    mutationFn: () =>
      api.aiExtract(customerId, {
        raw_content: rawContent,
        channel,
        attachments,
      }),
    onSuccess: (result) => {
      const suggestion = result.suggested_interaction;
      setProposalId(result.proposal.id);
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
      setConfidence(suggestion.confidence);
      setReviewReady(true);
    },
  });

  const completeMutation = useMutation({
    mutationFn: () => api.completeWork(workItemId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["workbench"] }),
        queryClient.invalidateQueries({ queryKey: ["customer", customerId] }),
        queryClient.invalidateQueries({ queryKey: ["activities"] }),
        queryClient.invalidateQueries({ queryKey: ["customers"] }),
      ]);
      setCompleteConfirmOpen(false);
      onClose();
    },
  });

  const mutation = useMutation({
    mutationFn: (payload: InteractionPayload) =>
      api.recordInteraction(workItemId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["workbench"] }),
        queryClient.invalidateQueries({ queryKey: ["customer", customerId] }),
        queryClient.invalidateQueries({ queryKey: ["activities"] }),
        queryClient.invalidateQueries({ queryKey: ["customers"] }),
      ]);
      onClose();
    },
  });

  function useManualFallback() {
    setSummary(rawContent.trim() || "已上传图片记录，待后续补充说明。");
    setFeedback("");
    setProposalId(null);
    setConfidence(null);
    setReviewReady(true);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!reviewReady) return;

    mutation.mutate({
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
      proposal_id: proposalId,
      attachments,
    });
  }

  const canOrganize =
    rawContent.trim().length > 0 || attachments.length > 0;

  return (
    <div className="drawer-backdrop" role="presentation" onMouseDown={onClose}>
      <aside
        className="drawer drawer-progress"
        aria-label="记录客户进展"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="drawer-header">
          <div>
            <p className="eyebrow">PROGRESS CAPTURE</p>
            <h2>记录进展 · {customer?.name ?? "正在读取…"}</h2>
            <p className="muted">
              说清发生了什么，或直接上传聊天截图；其余字段由系统先整理。
            </p>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </header>

        <form className="drawer-body progress-capture-form" onSubmit={submit}>
          <section className="conversation-capture">
            <textarea
              autoFocus
              rows={6}
              value={rawContent}
              onChange={(event) => {
                setRawContent(event.target.value);
                invalidateReview();
              }}
              placeholder="例如：刚刚电话聊了 10 分钟，他说资料看过了，但需要和家里人商量，明天下午回复。也可以只上传截图。"
            />

            <div className="conversation-toolbar">
              <ImageAttachmentPicker
                attachments={attachments}
                onChange={(value) => {
                  setAttachments(value);
                  invalidateReview();
                }}
              />
              <div className="conversation-actions">
                <select
                  value={channel}
                  onChange={(event) => {
                    setChannel(
                      event.target.value as InteractionPayload["channel"],
                    );
                    invalidateReview();
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
                  disabled={!canOrganize || aiMutation.isPending}
                  onClick={() => aiMutation.mutate()}
                >
                  {aiMutation.isPending ? "正在整理…" : "智能整理"}
                </button>
              </div>
            </div>
          </section>

          {aiMutation.error && (
            <div className="error-banner inline-error-actions">
              <span>
                智能整理暂时失败：{aiMutation.error.message}
              </span>
              <button
                type="button"
                className="button secondary compact"
                onClick={useManualFallback}
              >
                直接用原始记录
              </button>
            </div>
          )}

          {reviewReady && (
            <>
              <section className="record-review-card">
                <div className="record-review-head">
                  <div>
                    <span>识别结果</span>
                    <strong>{summary}</strong>
                  </div>
                  {confidence != null && (
                    <span className="review-ready">
                      置信度 {Math.round(confidence * 100)}%
                    </span>
                  )}
                </div>

                {feedback && (
                  <div className="record-review-summary">
                    <span>客户反馈</span>
                    <blockquote>{feedback}</blockquote>
                  </div>
                )}

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
                    <span>结果</span>
                    <strong>
                      {outcome === "waiting" ? "记录后继续等待" : "记录后结束本轮"}
                    </strong>
                  </div>
                </div>
              </section>

              <details className="advanced-record-editor">
                <summary>需要修改？展开详细字段</summary>
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
                      <strong>记录后结束本轮</strong>
                      <span>保存这次沟通，并进入今日完成</span>
                    </button>
                    <button
                      type="button"
                      className={outcome === "waiting" ? "choice active" : "choice"}
                      onClick={() => {
                        setOutcome("waiting");
                        if (waitingOn === "none") setWaitingOn("customer");
                      }}
                    >
                      <strong>记录后继续等待</strong>
                      <span>保存这次沟通，并继续留在工作区</span>
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
            </>
          )}

          {mutation.error && (
            <div className="error-banner">{mutation.error.message}</div>
          )}
          {completeMutation.error && (
            <div className="error-banner">{completeMutation.error.message}</div>
          )}

          <footer className="form-actions progress-form-actions">
            <div className="progress-terminal-action">
              <button
                type="button"
                className="button secondary"
                disabled={completeMutation.isPending || mutation.isPending}
                onClick={() => setCompleteConfirmOpen(true)}
              >
                结束本轮跟进
              </button>
              <span>没有新的沟通需要记录时，可以直接结束今天这一轮。</span>
            </div>
            <div className="progress-save-actions">
              <button
                type="button"
                className="button ghost"
                onClick={onClose}
                disabled={completeMutation.isPending || mutation.isPending}
              >
                返回
              </button>
              <button
                type="submit"
                className="button primary"
                disabled={
                  !reviewReady ||
                  !summary.trim() ||
                  mutation.isPending ||
                  completeMutation.isPending
                }
              >
                {mutation.isPending ? "正在保存…" : "确认记录"}
              </button>
            </div>
          </footer>
        </form>

        {completeConfirmOpen && (
          <WorkLifecycleDialog
            mode="complete"
            customerName={customer?.name ?? customerId}
            pending={completeMutation.isPending}
            onClose={() => setCompleteConfirmOpen(false)}
            onConfirm={() => completeMutation.mutate()}
          />
        )}
      </aside>
    </div>
  );
}
