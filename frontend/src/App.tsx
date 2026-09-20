import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";
import ActivityFeedView from "./components/ActivityFeedView";
import CustomerDrawer from "./components/CustomerDrawer";
import CustomerListView from "./components/CustomerListView";
import InteractionDrawer from "./components/InteractionDrawer";
import QuickRecordDialog from "./components/QuickRecordDialog";
import WorkbenchView from "./components/WorkbenchView";

type View = "workbench" | "customers" | "activities";

function formatDemoTime(value: string | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function App() {
  const queryClient = useQueryClient();
  const [view, setView] = useState<View>("workbench");
  const [detailCustomerId, setDetailCustomerId] = useState<string | null>(null);
  const [composer, setComposer] = useState<{
    workItemId: number;
    customerId: string;
  } | null>(null);
  const [demoOpen, setDemoOpen] = useState(false);
  const [quickRecordOpen, setQuickRecordOpen] = useState(false);

  const metaQuery = useQuery({
    queryKey: ["meta"],
    queryFn: api.meta,
  });

  const resetMutation = useMutation({
    mutationFn: api.resetDemo,
    onSuccess: async () => {
      setComposer(null);
      setDetailCustomerId(null);
      setView("workbench");
      setDemoOpen(false);
      await queryClient.invalidateQueries();
    },
  });

  const timeMutation = useMutation({
    mutationFn: (days: number) => api.advanceDemoTime(days),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["workbench"] }),
        queryClient.invalidateQueries({ queryKey: ["customers"] }),
        queryClient.invalidateQueries({ queryKey: ["meta"] }),
      ]);
      setDemoOpen(false);
    },
  });

  const navItems: Array<[View, string, string]> = [
    ["workbench", "今日工作台", "工作 / 发现"],
    ["customers", "全部客户", "客户档案"],
    ["activities", "客户动态", "信息收件箱"],
  ];

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <div className="brand-mark">经</div>
          <div>
            <p className="eyebrow">CLIENT OPERATIONS WORKBENCH</p>
            <h1>客户经营工作台</h1>
          </div>
        </div>

        <nav className="main-nav" aria-label="主导航">
          {navItems.map(([id, label, note]) => (
            <button
              key={id}
              className={view === id ? "nav-item active" : "nav-item"}
              onClick={() => setView(id)}
            >
              <strong>{label}</strong>
              <span>{note}</span>
            </button>
          ))}
        </nav>

        <div className="topbar-actions">
          <button
            className="button primary topbar-record-button"
            onClick={() => setQuickRecordOpen(true)}
          >
            记录进展
          </button>

          <div className="demo-menu-wrap">
            <button
              className="button secondary"
              onClick={() => setDemoOpen((value) => !value)}
            >
              演示工具
            </button>
            {demoOpen && (
              <div className="demo-menu">
                <div className="demo-time-row">
                  <span>当前演示时间</span>
                  <strong>{formatDemoTime(metaQuery.data?.demo_time)}</strong>
                </div>
                <button
                  onClick={() => timeMutation.mutate(1)}
                  disabled={timeMutation.isPending}
                >
                  时间推进 +1 天
                </button>
                <button
                  onClick={() => timeMutation.mutate(3)}
                  disabled={timeMutation.isPending}
                >
                  时间推进 +3 天
                </button>
                <button
                  onClick={() => resetMutation.mutate()}
                  disabled={resetMutation.isPending}
                >
                  重置全部演示数据
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="page">
        {view === "workbench" && (
          <WorkbenchView
            onOpenCustomer={setDetailCustomerId}
            onRecordWork={(workItemId, customerId) =>
              setComposer({ workItemId, customerId })
            }
          />
        )}

        {view === "customers" && (
          <CustomerListView onOpenCustomer={setDetailCustomerId} />
        )}

        {view === "activities" && (
          <ActivityFeedView onOpenCustomer={setDetailCustomerId} />
        )}

        <footer className="page-footer">
          <p>
            当前仅使用模拟数据；不连接真实券商 CRM，不自动发送金融建议，
            不替代适当性流程或客户经理判断。
          </p>
        </footer>
      </main>

      {detailCustomerId && (
        <CustomerDrawer
          customerId={detailCustomerId}
          onClose={() => setDetailCustomerId(null)}
          onRecordWork={(workItemId, customerId) => {
            setDetailCustomerId(null);
            setComposer({ workItemId, customerId });
          }}
        />
      )}

      {quickRecordOpen && (
        <QuickRecordDialog onClose={() => setQuickRecordOpen(false)} />
      )}

      {composer && (
        <InteractionDrawer
          workItemId={composer.workItemId}
          customerId={composer.customerId}
          onClose={() => setComposer(null)}
        />
      )}
    </div>
  );
}
