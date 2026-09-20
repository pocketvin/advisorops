import { ChangeEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, type CustomerImportPreview } from "../api";

interface Props {
  onClose: () => void;
}

export default function CustomerImportDialog({ onClose }: Props) {
  const queryClient = useQueryClient();
  const [fileName, setFileName] = useState("");
  const [csvText, setCsvText] = useState("");
  const [preview, setPreview] = useState<CustomerImportPreview | null>(null);
  const [fileError, setFileError] = useState("");

  const previewMutation = useMutation({
    mutationFn: (value: string) => api.previewCustomerImport(value),
    onSuccess: (result) => setPreview(result),
  });

  const commitMutation = useMutation({
    mutationFn: () => api.commitCustomerImport(csvText),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["customers"] }),
        queryClient.invalidateQueries({ queryKey: ["workbench"] }),
        queryClient.invalidateQueries({ queryKey: ["activities"] }),
      ]);
      onClose();
    },
  });

  async function loadFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setFileError("目前只支持 CSV。Excel 请先另存为 CSV UTF-8 后再导入。");
      setPreview(null);
      setCsvText("");
      return;
    }
    if (file.size > 2_000_000) {
      setFileError("CSV 文件不能超过 2MB。");
      setPreview(null);
      setCsvText("");
      return;
    }

    try {
      const text = await file.text();
      setFileName(file.name);
      setCsvText(text);
      setFileError("");
      setPreview(null);
      previewMutation.mutate(text);
    } catch {
      setFileError("读取 CSV 文件失败。");
    }
  }

  const rows = preview?.rows ?? [];
  const visibleRows = rows.slice(0, 20);

  return (
    <div className="quick-record-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="customer-import-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="批量导入客户"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="quick-record-header">
          <div>
            <p className="eyebrow">BULK CUSTOMER IMPORT</p>
            <h2>批量导入客户</h2>
            <p>
              上传 CSV 后先做字段别名归一化、枚举/时间校验和重复检查。
              预览确认后才真正写入客户档案。
            </p>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </header>

        <div className="customer-import-body">
          <section className="import-guide-card">
            <div>
              <strong>统一格式原则</strong>
              <p>
                “姓名/客户姓名”“客户等级/服务层级”“高意向/high”等常见写法会自动归一。
                不认识的列会忽略并提示；关系阶段、意向和日期无法识别时该行不会导入。
              </p>
            </div>
            <div className="import-guide-actions">
              <a
                className="button secondary"
                href="/api/customers/import-template"
                download
              >
                下载标准模板
              </a>
              <a
                className="button ghost"
                href="/api/customers/import-sample"
                download
              >
                下载示例
              </a>
            </div>
          </section>

          <label className="import-dropzone">
            <input type="file" accept=".csv,text/csv" onChange={loadFile} />
            <span>选择 CSV 文件</span>
            <strong>{fileName || "点击选择，或把 Excel 另存为 CSV UTF-8"}</strong>
            <small>单次最多 500 位客户 · 最大 2MB</small>
          </label>

          {fileError && <div className="error-banner">{fileError}</div>}
          {previewMutation.error && (
            <div className="error-banner">
              预览失败：{previewMutation.error.message}
            </div>
          )}

          {previewMutation.isPending && (
            <div className="table-loading">正在统一字段并检查数据…</div>
          )}

          {preview && (
            <>
              <div className="import-summary-grid">
                <div>
                  <span>总行数</span>
                  <strong>{preview.summary.total}</strong>
                </div>
                <div className="positive">
                  <span>可导入</span>
                  <strong>{preview.summary.valid}</strong>
                </div>
                <div className={preview.summary.invalid ? "negative" : ""}>
                  <span>需修正</span>
                  <strong>{preview.summary.invalid}</strong>
                </div>
                <div>
                  <span>提醒</span>
                  <strong>{preview.summary.warnings}</strong>
                </div>
              </div>

              {preview.ignored_columns.length > 0 && (
                <div className="warning-banner">
                  已忽略未识别列：{preview.ignored_columns.join("、")}
                </div>
              )}

              <div className="import-preview-table-wrap">
                <table className="import-preview-table">
                  <thead>
                    <tr>
                      <th>行</th>
                      <th>状态</th>
                      <th>客户</th>
                      <th>标准化结果</th>
                      <th>问题 / 提醒</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleRows.map((row) => (
                      <tr key={row.row_number}>
                        <td>{row.row_number}</td>
                        <td>
                          <span
                            className={
                              row.status === "valid"
                                ? "import-status valid"
                                : "import-status invalid"
                            }
                          >
                            {row.status === "valid" ? "可导入" : "需修正"}
                          </span>
                        </td>
                        <td>
                          <strong>{row.normalized.name}</strong>
                          <small>{row.normalized.customer_id}</small>
                        </td>
                        <td>
                          <span>
                            {row.normalized.customer_level} ·{" "}
                            {row.normalized.risk_level}
                          </span>
                          <small>
                            {row.normalized.relationship_stage} ·{" "}
                            {row.normalized.intent_level}
                          </small>
                        </td>
                        <td>
                          {row.errors.map((item) => (
                            <p className="import-error-text" key={item}>
                              {item}
                            </p>
                          ))}
                          {row.warnings.map((item) => (
                            <p className="import-warning-text" key={item}>
                              {item}
                            </p>
                          ))}
                          {row.errors.length === 0 &&
                            row.warnings.length === 0 && <span>—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {rows.length > visibleRows.length && (
                  <div className="table-loading">
                    预览只显示前 {visibleRows.length} 行；确认时会处理全部{" "}
                    {rows.length} 行。
                  </div>
                )}
              </div>
            </>
          )}

          {commitMutation.error && (
            <div className="error-banner">
              导入失败：{commitMutation.error.message}
            </div>
          )}
        </div>

        <footer className="quick-record-footer import-footer">
          <span>
            {preview
              ? "将导入 " +
                preview.summary.valid +
                " 位，跳过 " +
                preview.summary.invalid +
                " 行"
              : "先上传 CSV 并完成预览。"}
          </span>
          <div>
            <button className="button secondary" onClick={onClose}>
              取消
            </button>
            <button
              className="button primary"
              disabled={
                !preview ||
                preview.summary.valid === 0 ||
                commitMutation.isPending
              }
              onClick={() => commitMutation.mutate()}
            >
              {commitMutation.isPending
                ? "正在导入…"
                : "确认导入 " + (preview?.summary.valid ?? 0) + " 位"}
            </button>
          </div>
        </footer>
      </section>
    </div>
  );
}
