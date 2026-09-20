import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api";
import BatchDeleteDialog from "./BatchDeleteDialog";
import CustomerImportDialog from "./CustomerImportDialog";

interface Props {
  onOpenCustomer: (customerId: string) => void;
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
  unknown: "未知",
  low: "低",
  medium: "中",
  high: "高",
};

function formatTime(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(value));
}

export default function CustomerListView({ onOpenCustomer }: Props) {
  const [search, setSearch] = useState("");
  const [stage, setStage] = useState("");
  const [risk, setRisk] = useState("");
  const [intent, setIntent] = useState("");
  const [assetBand, setAssetBand] = useState("");
  const [sortBy, setSortBy] = useState("priority");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [importOpen, setImportOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const query = useQuery({
    queryKey: ["customers", search, stage, risk, intent, assetBand, sortBy],
    queryFn: () =>
      api.customers({
        search,
        stage,
        risk_level: risk,
        intent,
        total_assets_band: assetBand,
        sort_by: sortBy,
      }),
  });

  const visibleIds = useMemo(
    () => query.data?.map((item) => item.customer.customer_id) ?? [],
    [query.data],
  );

  useEffect(() => {
    const visible = new Set(visibleIds);
    setSelected((current) => {
      const next = new Set(
        [...current].filter((customerId) => visible.has(customerId)),
      );
      if (
        next.size === current.size &&
        [...next].every((item) => current.has(item))
      ) {
        return current;
      }
      return next;
    });
  }, [visibleIds]);

  const allVisibleSelected =
    visibleIds.length > 0 &&
    visibleIds.every((customerId) => selected.has(customerId));

  const selectedNames = useMemo(() => {
    const selectedSet = selected;
    return (
      query.data
        ?.filter((item) => selectedSet.has(item.customer.customer_id))
        .map((item) => item.customer.name) ?? []
    );
  }, [query.data, selected]);

  function toggleCustomer(customerId: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(customerId)) {
        next.delete(customerId);
      } else {
        next.add(customerId);
      }
      return next;
    });
  }

  function toggleAllVisible() {
    setSelected((current) => {
      const next = new Set(current);
      if (allVisibleSelected) {
        visibleIds.forEach((customerId) => next.delete(customerId));
      } else {
        visibleIds.forEach((customerId) => next.add(customerId));
      }
      return next;
    });
  }

  return (
    <section className="customer-list-page">
      <div className="section-title-row customer-page-heading">
        <div>
          <p className="eyebrow">CUSTOMER BOOK</p>
          <h2>全部客户</h2>
          <p className="muted">
            查看、筛选和批量维护客户档案；导入数据会先标准化预览再确认。
          </p>
        </div>
        <div className="customer-admin-actions">
          {selected.size > 0 && (
            <span className="selected-count">已选 {selected.size} 位</span>
          )}
          <button
            className="button secondary"
            onClick={() => setImportOpen(true)}
          >
            批量导入 CSV
          </button>
          <button
            className="button danger"
            disabled={selected.size === 0}
            onClick={() => setDeleteOpen(true)}
          >
            删除已选{selected.size ? " " + selected.size : ""}
          </button>
          <span className="section-count">{query.data?.length ?? 0} 位</span>
        </div>
      </div>

      <div className="filter-bar filter-bar-six">
        <label className="search-box">
          <span>搜索</span>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="姓名 / 编号 / 需求 / 职业 / 地区 / 兴趣"
          />
        </label>
        <label>
          <span>关系阶段</span>
          <select value={stage} onChange={(event) => setStage(event.target.value)}>
            <option value="">全部</option>
            <option value="new">新客户</option>
            <option value="contacted">已联系</option>
            <option value="interested">有明确兴趣</option>
            <option value="considering">考虑中</option>
            <option value="rejected">近期明确拒绝</option>
            <option value="dormant">长期沉默</option>
          </select>
        </label>
        <label>
          <span>风险等级</span>
          <select value={risk} onChange={(event) => setRisk(event.target.value)}>
            <option value="">全部</option>
            <option value="C1">C1</option>
            <option value="C2">C2</option>
            <option value="C3">C3</option>
            <option value="C4">C4</option>
            <option value="C5">C5</option>
          </select>
        </label>
        <label>
          <span>当前意向</span>
          <select value={intent} onChange={(event) => setIntent(event.target.value)}>
            <option value="">全部</option>
            <option value="unknown">未知</option>
            <option value="low">低</option>
            <option value="medium">中</option>
            <option value="high">高</option>
          </select>
        </label>
        <label>
          <span>资产区间</span>
          <select
            value={assetBand}
            onChange={(event) => setAssetBand(event.target.value)}
          >
            <option value="">全部</option>
            <option value="10-30万">10-30万</option>
            <option value="30-80万">30-80万</option>
            <option value="80-150万">80-150万</option>
            <option value="150-300万">150-300万</option>
            <option value="300万以上">300万以上</option>
          </select>
        </label>
        <label>
          <span>排序</span>
          <select
            value={sortBy}
            onChange={(event) => setSortBy(event.target.value)}
          >
            <option value="priority">当前经营优先级</option>
            <option value="recent">最近联系</option>
            <option value="name">姓名</option>
          </select>
        </label>
      </div>

      {query.error && (
        <div className="error-banner">读取客户列表失败：{query.error.message}</div>
      )}

      <div className="customer-table-wrap">
        <table className="customer-table">
          <thead>
            <tr>
              <th className="select-column">
                <input
                  type="checkbox"
                  aria-label="全选当前列表"
                  checked={allVisibleSelected}
                  onChange={toggleAllVisible}
                />
              </th>
              <th>客户</th>
              <th>状态</th>
              <th>当前需求</th>
              <th>最近联系</th>
              <th>下一步</th>
              <th>当前队列</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {query.data?.map((item) => {
              const customer = item.customer;
              const checked = selected.has(customer.customer_id);
              return (
                <tr
                  key={customer.customer_id}
                  className={checked ? "selected-row" : ""}
                >
                  <td className="select-column">
                    <input
                      type="checkbox"
                      aria-label={"选择 " + customer.name}
                      checked={checked}
                      onChange={() => toggleCustomer(customer.customer_id)}
                    />
                  </td>
                  <td>
                    <div className="table-customer">
                      <strong>{customer.name}</strong>
                      <span>
                        {customer.customer_id} · 服务 {customer.customer_level} ·{" "}
                        {customer.risk_level} · {customer.total_assets_band}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="table-status">
                      <span>{stageLabels[customer.relationship_stage]}</span>
                      <small>{intentLabels[customer.intent_level]}意向</small>
                    </div>
                  </td>
                  <td className="truncate-cell">
                    {customer.current_need || "暂无明确记录"}
                  </td>
                  <td>{formatTime(customer.last_contact_at)}</td>
                  <td className="truncate-cell">
                    {customer.next_step || "尚未安排"}
                  </td>
                  <td>
                    {item.active_work_item ? (
                      <span className="queue-badge work">
                        {item.active_work_item.status === "waiting"
                          ? "工作区·等待"
                          : "工作区·待处理"}
                      </span>
                    ) : item.discovery ? (
                      <span className="queue-badge discovery">
                        发现区 · {item.discovery.score}
                      </span>
                    ) : customer.cooldown_until ? (
                      <span className="queue-badge cooldown">冷静期</span>
                    ) : (
                      <span className="queue-badge quiet">当前无需动作</span>
                    )}
                  </td>
                  <td>
                    <button
                      className="text-button"
                      onClick={() => onOpenCustomer(customer.customer_id)}
                    >
                      详情 →
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {query.isLoading && (
          <div className="table-loading">正在读取客户档案…</div>
        )}
        {!query.isLoading && query.data?.length === 0 && (
          <div className="table-loading">没有符合当前筛选条件的客户。</div>
        )}
      </div>

      {importOpen && (
        <CustomerImportDialog onClose={() => setImportOpen(false)} />
      )}

      {deleteOpen && selected.size > 0 && (
        <BatchDeleteDialog
          customerIds={[...selected]}
          customerNames={selectedNames}
          onClose={() => setDeleteOpen(false)}
          onDeleted={() => setSelected(new Set())}
        />
      )}
    </section>
  );
}
