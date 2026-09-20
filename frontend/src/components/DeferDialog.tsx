import { FormEvent, useState } from "react";

interface Props {
  customerName: string;
  baseTime?: string;
  pending: boolean;
  onClose: () => void;
  onConfirm: (payload: { days?: number; next_contact_at?: string }) => void;
}

function toLocalInput(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
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

export default function DeferDialog({
  customerName,
  baseTime,
  pending,
  onClose,
  onConfirm,
}: Props) {
  const base = baseTime ? new Date(baseTime) : new Date();
  const tomorrow = new Date(base);
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(10, 0, 0, 0);

  const [mode, setMode] = useState<"1" | "3" | "7" | "custom">("3");
  const [customTime, setCustomTime] = useState(toLocalInput(tomorrow));
  const minimumTime = toLocalInput(base);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (mode === "custom") {
      onConfirm({ next_contact_at: new Date(customTime).toISOString() });
      return;
    }
    onConfirm({ days: Number(mode) });
  }

  return (
    <div className="mini-dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="mini-dialog"
        onSubmit={submit}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="mini-dialog-head">
          <div>
            <p className="eyebrow">FOLLOW UP LATER</p>
            <h3>稍后跟进 · {customerName}</h3>
            <p>这里只调整下一次经营时间，不代表客户意向下降。</p>
          </div>
          <button type="button" className="icon-button" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="defer-options">
          {[
            ["1", "明天"],
            ["3", "3 天后"],
            ["7", "1 周后"],
            ["custom", "自定义"],
          ].map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={mode === value ? "defer-option active" : "defer-option"}
              onClick={() => setMode(value as typeof mode)}
            >
              {label}
            </button>
          ))}
        </div>

        {mode === "custom" && (
          <label className="field">
            <span>具体跟进时间</span>
            <input
              type="datetime-local"
              min={minimumTime}
              value={customTime}
              onChange={(event) => setCustomTime(event.target.value)}
            />
          </label>
        )}

        <div className="mini-dialog-actions">
          <button type="button" className="button secondary" onClick={onClose}>
            取消
          </button>
          <button className="button primary" disabled={pending}>
            {pending ? "正在设置…" : "确认稍后跟进"}
          </button>
        </div>
      </form>
    </div>
  );
}
