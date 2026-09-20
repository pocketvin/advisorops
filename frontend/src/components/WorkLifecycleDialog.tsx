interface Props {
  mode: "cancel" | "complete";
  customerName: string;
  pending: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

export default function WorkLifecycleDialog({
  mode,
  customerName,
  pending,
  onClose,
  onConfirm,
}: Props) {
  const cancelling = mode === "cancel";

  return (
    <div
      className="mini-dialog-backdrop"
      role="presentation"
      onMouseDown={onClose}
    >
      <section
        className="mini-dialog work-lifecycle-dialog"
        role="dialog"
        aria-modal="true"
        aria-label={cancelling ? "取消跟进" : "结束跟进"}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="mini-dialog-head">
          <div>
            <p className="eyebrow">
              {cancelling ? "CANCEL FOLLOW-UP" : "CLOSE FOLLOW-UP"}
            </p>
            <h3>
              {cancelling ? "取消这次跟进？" : "结束本轮跟进？"}
            </h3>
            <p>{customerName}</p>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </div>

        <div
          className={
            cancelling
              ? "work-lifecycle-note cancel"
              : "work-lifecycle-note complete"
          }
        >
          {cancelling ? (
            <>
              <strong>相当于撤销这次“开始跟进”。</strong>
              <p>
                当前工作项会退出工作区，但不会修改客户阶段、意向、下一次联系时间等客户状态。
                如果客户仍满足发现规则，他会重新回到发现区。
              </p>
            </>
          ) : (
            <>
              <strong>表示今天这一轮工作先到这里。</strong>
              <p>
                工作项会记为“今日完成”，今天不再重复推荐。不会伪造一次客户沟通，
                也不会修改客户阶段、意向或已有的下次联系时间。
              </p>
            </>
          )}
        </div>

        <div className="mini-dialog-actions">
          <button className="button secondary" onClick={onClose} disabled={pending}>
            返回
          </button>
          <button
            className={cancelling ? "button danger" : "button primary"}
            onClick={onConfirm}
            disabled={pending}
          >
            {pending
              ? cancelling
                ? "正在取消…"
                : "正在结束…"
              : cancelling
                ? "确认取消跟进"
                : "确认结束跟进"}
          </button>
        </div>
      </section>
    </div>
  );
}
