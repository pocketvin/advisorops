import { ChangeEvent, useRef, useState } from "react";

import type { ImageAttachmentInput } from "../api";
import {
  attachmentPreviewUrl,
  prepareImageAttachments,
} from "../imageAttachments";

interface Props {
  attachments: ImageAttachmentInput[];
  onChange: (attachments: ImageAttachmentInput[]) => void;
}

export default function ImageAttachmentPicker({ attachments, onChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState("");

  async function handleFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = event.target.files;
    if (!files?.length) return;
    try {
      setError("");
      const prepared = await prepareImageAttachments(files, attachments.length);
      onChange([...attachments, ...prepared]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "图片处理失败");
    } finally {
      event.target.value = "";
    }
  }

  return (
    <div className="attachment-picker">
      <input
        ref={inputRef}
        className="attachment-input"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        onChange={handleFiles}
      />

      <button
        type="button"
        className="attachment-add"
        onClick={() => inputRef.current?.click()}
        disabled={attachments.length >= 4}
      >
        <span>＋</span>
        上传图片
      </button>

      {attachments.map((attachment, index) => (
        <div className="attachment-thumb" key={attachment.name + index}>
          <img
            src={attachmentPreviewUrl(attachment)}
            alt={attachment.name}
          />
          <button
            type="button"
            aria-label={"移除 " + attachment.name}
            onClick={() =>
              onChange(attachments.filter((_, itemIndex) => itemIndex !== index))
            }
          >
            ×
          </button>
        </div>
      ))}

      {error && <span className="attachment-error">{error}</span>}
      {attachments.length > 0 && (
        <span className="attachment-hint">
          图片会和文字一起参与整理；确认后才写入客户记录。
        </span>
      )}
    </div>
  );
}
