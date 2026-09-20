export type RelationshipStage =
  | "new"
  | "contacted"
  | "interested"
  | "considering"
  | "rejected"
  | "dormant";

export type IntentLevel = "unknown" | "low" | "medium" | "high";

export interface Customer {
  customer_id: string;
  name: string;
  age_band: string;
  customer_level: string;
  risk_level: string;
  total_assets_band: string;
  investable_funds_band: string;
  relationship_stage: RelationshipStage;
  intent_level: IntentLevel;
  current_need: string;
  current_obstacle: string;
  current_progress: string;
  next_step: string;
  next_contact_at: string | null;
  cooldown_until: string | null;
  pinned: boolean;
  last_contact_at: string | null;
  recent_signal: string;
}

export interface DiscoveryFactor {
  code: string;
  label: string;
  points: number;
  evidence: string;
}

export interface Discovery {
  score: number;
  level: "high" | "medium" | "low";
  follow_up_state: string;
  actionable_reason: string;
  factors: DiscoveryFactor[];
  suggested_action: string;
  pinned: boolean;
  compliance_note: string;
}

export interface DiscoveryItem {
  customer: Customer;
  discovery: Discovery;
}

export interface WorkItem {
  id: number;
  customer_id: string;
  title: string;
  status: "action_required" | "waiting" | "completed_today" | "cancelled";
  waiting_on: string;
  current_progress: string;
  next_action: string;
  due_at: string | null;
  started_at: string;
  completed_at: string | null;
  name?: string;
  customer_level?: string;
  relationship_stage?: RelationshipStage;
  intent_level?: IntentLevel;
  last_contact_at?: string | null;
  customer_progress?: string;
  customer_next_step?: string;
}

export interface Workbench {
  summary: {
    action_required: number;
    waiting: number;
    completed_today: number;
    discovery: number;
  };
  work_area: {
    action_required: WorkItem[];
    waiting: WorkItem[];
    completed_today: WorkItem[];
  };
  discovery: DiscoveryItem[];
}

export interface ActivityEvent {
  id: number;
  activity_type: string;
  channel: string;
  occurred_at: string;
  raw_content: string;
  structured_summary: string;
  customer_feedback: string;
  action_taken: string;
  next_step: string;
}

export interface CustomerDetail {
  customer: Customer;
  active_work_item: WorkItem | null;
  activities: ActivityEvent[];
  field_changes: Array<{
    id: number;
    field_name: string;
    old_value: string | null;
    new_value: string | null;
    changed_at: string;
  }>;
}

export interface InteractionPayload {
  raw_content: string;
  structured_summary: string;
  customer_feedback: string;
  action_taken: string;
  relationship_stage: RelationshipStage;
  intent_level: IntentLevel;
  current_need: string;
  current_obstacle: string;
  next_step: string;
  next_contact_at: string | null;
  channel: "phone" | "wecom" | "meeting" | "app" | "other";
  outcome: "completed" | "waiting";
  waiting_on: "none" | "customer" | "manager" | "internal" | "scheduled_time";
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    let message = `请求失败（${response.status}）`;
    try {
      const body = await response.json();
      if (body?.detail) {
        message = body.detail;
      }
    } catch {
      // Keep the status-based message.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export const api = {
  workbench: () => request<Workbench>("/api/workbench"),

  customer: (customerId: string) =>
    request<CustomerDetail>(`/api/customers/${customerId}`),

  startWork: (customerId: string) =>
    request<WorkItem>(`/api/discovery/${customerId}/start`, {
      method: "POST",
    }),

  recordInteraction: (workItemId: number, payload: InteractionPayload) =>
    request(`/api/work-items/${workItemId}/interactions`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  resetDemo: () =>
    request<Workbench>("/api/demo/reset", {
      method: "POST",
    }),
};
