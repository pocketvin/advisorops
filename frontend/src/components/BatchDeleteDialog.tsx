import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "../api";

interface Props {
  customerIds: string[];
  customerNames: string[];
  onClose: () => void;
  onDeleted: () => void;
}

export default function BatchDeleteDialog({
  customerIds,
  customerNames,
  onClose,
  onDeleted,
}: Props) {
  const queryClient = useQueryClient();
  const [acknowledged, setAcknowledged] = useState(false);

  const mutation = useMutation({
    mutationFn: () => api.bulkDeleteCustomers(customerIds),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["customers"] }),
        queryClient.invalidateQueries({ queryKey: ["workbench"] }),
        queryClient.invalidateQueries({ queryKey: ["activities"] }),
        queryClient.invalidateQueries({ queryKey: ["customer"] }),
      ]);
      onDeleted();
      onClose();
    },
  });

  return (
    <div className="mini-dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="mini-dialog delete-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="批量删除客户"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="mini-dialog-head">
          <div>
            <p className="eyebrow">BULK DELETE</p>
            <h3>删除 {customerIds.length} 位客户</h3>
            <p>
              删除会级联移除该客户的 WorkItem、Activity、Field Audit 和待确认 Proposal。
              仅被这些客户引用的本地图片附件也会一起清理。
            </p>
          </div>
          <button type="button" className="icon-button" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="delete-customer-list">
          {customerNames.slice(0, 8).map((name) => (
            <span key={name}>{name}</span>
          ))}
          {customerNames.length > 8 && (
            <span>另 {customerNames.length - 8} 位</span>
          )}
        </div>

        <label className="delete-confirm-check">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(event) => setAcknowledged(event.target.checked)}
          />
          <span>
            我确认这些客户应从当前本地 Demo 数据中删除，并理解历史记录也会一起删除。
          </span>
        </label>

        {mutation.error && (
          <div className="error-banner">删除失败：{mutation.error.message}</div>
        )}

        <div className="mini-dialog-actions">
          <button className="button secondary" onClick={onClose}>
            取消
          </button>
          <button
            className="button danger"
            disabled={!acknowledged || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "正在删除…" : "确认删除"}
          </button>
        </div>
      </section>
    </div>
  );
}
