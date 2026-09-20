export type RelationshipStage =
  | "new"
  | "contacted"
  | "interested"
  | "considering"
  | "rejected"
  | "dormant";

export type IntentLevel = "unknown" | "low" | "medium" | "high";

export interface CustomerProfile {
  demographics?: {
    residence_region?: string;
    occupation?: string;
    industry?: string;
    employer_type?: string;
  };
  family_and_life?: {
    family_stage?: string;
    dependents_summary?: string;
    major_plan?: string;
  };
  financial_context?: {
    annual_income_band?: string;
    liabilities_band?: string;
    cash_flow_pattern?: string;
    liquidity_preference?: string;
  };
  investment_context?: {
    experience?: string;
    primary_goal?: string;
    investment_horizon?: string;
    information_preference?: string;
  };
  service_preferences?: {
    preferred_channel?: string;
    preferred_contact_time?: string;
    communication_style?: string;
  };
  relationship_context?: {
    interests?: string[];
    key_concerns?: string[];
    trust_factors?: string[];
  };
}

export interface ProfileHypothesis {
  key: string;
  value: string;
  confidence: number;
  status: "needs_validation" | string;
  basis: string;
}

export interface Customer {
  customer_id: string;
  name: string;
  age_band: string;
  customer_level: string;
  risk_level: string;
  total_assets_band: string;
  investable_funds_band: string;
  profile: CustomerProfile;
  profile_hypotheses: ProfileHypothesis[];
  holdings_summary: string;
  recent_login_at: string | null;
  recent_trade_at: string | null;
  asset_change_30d_pct: number;
  recent_product_interest: string;
  recent_consult_topic: string;
  relationship_stage: RelationshipStage;
  intent_level: IntentLevel;
  current_need: string;
  current_obstacle: string;
  current_progress: string;
  next_step: string;
  next_contact_at: string | null;
  cooldown_until: string | null;
  pinned: boolean;
  manager_note: string;
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

export interface WorkLifecycleResult {
  work_item: WorkItem;
  customer: Customer;
  activity_id: number;
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
  demo_time: string;
}

export interface ActivityEvent {
  id: number;
  customer_id: string;
  name?: string;
  source: string;
  activity_type: string;
  channel: string;
  occurred_at: string;
  raw_content: string;
  structured_summary: string;
  customer_feedback: string;
  action_taken: string;
  next_step: string;
  metadata?: Record<string, unknown>;
}

export interface ProposedChange {
  from: unknown;
  to: unknown;
  reason: string;
}

export interface ChangeProposal {
  id: number;
  customer_id: string;
  customer_name?: string;
  activity_id: number | null;
  status: string;
  source: string;
  raw_content: string;
  proposed_changes: Record<string, ProposedChange>;
  extraction_summary: string;
  confidence: number | null;
  model: string | null;
  created_at: string;
}

export interface JudgmentEvidence {
  source: string;
  text: string;
  kind: "confirmed" | "hypothesis" | string;
  activity_id: number | null;
}

export interface JudgmentItem {
  text: string;
  evidence: JudgmentEvidence[];
}

export interface ActionBrief {
  mode: "contact" | "wait" | "prepare" | string;
  objective: string;
  questions: string[];
  completion_criteria: string;
  opening_line: string;
  evidence: JudgmentEvidence[];
}

export interface OperatingJudgment {
  generated_at: string;
  mode: "deterministic" | string;
  current_state: JudgmentItem;
  core_concern: JudgmentItem;
  decision_barrier: JudgmentItem;
  next_confirmation: JudgmentItem;
  action_brief: ActionBrief;
  communication_approach: JudgmentItem;
  avoid_action: JudgmentItem;
}

export interface CustomerDetail {
  customer: Customer;
  active_work_item: WorkItem | null;
  completed_today: boolean;
  activities: ActivityEvent[];
  field_changes: Array<{
    id: number;
    field_name: string;
    old_value: string | null;
    new_value: string | null;
    changed_at: string;
  }>;
  pending_proposals: ChangeProposal[];
  operating_judgment: OperatingJudgment;
}

export interface CustomerListItem {
  customer: Customer;
  active_work_item: WorkItem | null;
  discovery: Discovery | null;
}

export interface ImageAttachmentInput {
  name: string;
  mime_type: "image/jpeg" | "image/png" | "image/webp";
  data_url: string;
}

export interface SavedAttachment {
  id: string;
  name: string;
  mime_type: string;
  size: number;
  url: string;
  sha256: string;
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
  manager_note: string;
  next_step: string;
  next_contact_at: string | null;
  channel: "phone" | "wecom" | "meeting" | "app" | "other";
  outcome: "completed" | "waiting";
  waiting_on: "none" | "customer" | "manager" | "internal" | "scheduled_time";
  proposal_id?: number | null;
  attachments?: ImageAttachmentInput[];
}

export interface AIExtraction {
  proposal: ChangeProposal;
  suggested_interaction: {
    structured_summary: string;
    customer_feedback: string;
    relationship_stage: RelationshipStage;
    intent_level: IntentLevel;
    current_need: string;
    current_obstacle: string;
    next_step: string;
    next_contact_at: string | null;
    outcome: "completed" | "waiting";
    waiting_on: InteractionPayload["waiting_on"];
    reasoning_summary: string;
    confidence: number;
  };
  usage: Record<string, number>;
}

export interface QuickRecordPreparation {
  customer: Customer;
  ai_ready: boolean;
  warning: string | null;
  suggested_interaction: AIExtraction["suggested_interaction"];
  usage: Record<string, number>;
}

export interface CustomerBrief {
  summary: string;
  main_focus: string;
  current_obstacle: string;
  unresolved_questions: string[];
  next_conversation_focus: string;
  model: string;
  generated_at: string;
}

export interface ContextPack {
  text: string;
  included_fields: string[];
  redacted_fields: string[];
}

export interface SyncState {
  source: string;
  cursor: number;
  last_attempt_at: string | null;
  last_success_at: string | null;
  last_error: string;
  last_result_count: number;
}

export interface ActivityFeed {
  activities: ActivityEvent[];
  pending_proposals: ChangeProposal[];
  sync: {
    sources: SyncState[];
    configured_sources: string[];
  };
}

export interface CustomerImportPreviewRow {
  row_number: number;
  status: "valid" | "invalid";
  normalized: Customer & Record<string, unknown>;
  errors: string[];
  warnings: string[];
}

export interface CustomerImportPreview {
  summary: {
    total: number;
    valid: number;
    invalid: number;
    warnings: number;
  };
  ignored_columns: string[];
  rows: CustomerImportPreviewRow[];
}

export interface CustomerImportResult {
  imported_count: number;
  skipped_count: number;
  imported_customer_ids: string[];
  preview: CustomerImportPreview;
}

export interface BulkDeleteResult {
  deleted_count: number;
  deleted_customer_ids: string[];
  missing_customer_ids: string[];
  removed_attachment_count: number;
}

export interface Meta {
  product_name: string;
  working_name: boolean;
  positioning: string;
  data_notice: string;
  ai: {
    configured: boolean;
  };
  demo_time: string;
  compliance: string[];
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

function queryString(
  values: Record<string, string | number | undefined>,
): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value === undefined || value === "") continue;
    params.set(key, String(value));
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const api = {
  meta: () => request<Meta>("/api/meta"),

  workbench: () => request<Workbench>("/api/workbench"),

  customers: (filters: {
    search?: string;
    stage?: string;
    risk_level?: string;
    intent?: string;
    customer_level?: string;
    total_assets_band?: string;
    sort_by?: string;
  }) =>
    request<CustomerListItem[]>(
      "/api/customers" + queryString(filters),
    ),

  customer: (customerId: string) =>
    request<CustomerDetail>(`/api/customers/${customerId}`),

  previewCustomerImport: (csvText: string) =>
    request<CustomerImportPreview>("/api/customers/import/preview", {
      method: "POST",
      body: JSON.stringify({ csv_text: csvText }),
    }),

  commitCustomerImport: (csvText: string) =>
    request<CustomerImportResult>("/api/customers/import/commit", {
      method: "POST",
      body: JSON.stringify({ csv_text: csvText }),
    }),

  bulkDeleteCustomers: (customerIds: string[]) =>
    request<BulkDeleteResult>("/api/customers/bulk-delete", {
      method: "POST",
      body: JSON.stringify({
        customer_ids: customerIds,
        confirm: true,
      }),
    }),

  quickRecordPrepare: (payload: {
    raw_content: string;
    channel: InteractionPayload["channel"];
    attachments?: ImageAttachmentInput[];
  }) =>
    request<QuickRecordPreparation>("/api/quick-record/prepare", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  manualWork: (customerId: string) =>
    request<WorkItem>(`/api/customers/${customerId}/manual-work`, {
      method: "POST",
    }),

  setPin: (customerId: string, pinned: boolean) =>
    request<Customer>(`/api/customers/${customerId}/pin`, {
      method: "POST",
      body: JSON.stringify({ pinned }),
    }),

  deferCustomer: (
    customerId: string,
    payload: { days?: number; next_contact_at?: string | null },
  ) =>
    request<Customer>(`/api/customers/${customerId}/defer`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  startWork: (customerId: string) =>
    request<WorkItem>(`/api/discovery/${customerId}/start`, {
      method: "POST",
    }),

  aiExtract: (
    customerId: string,
    payload: {
      raw_content: string;
      channel: InteractionPayload["channel"];
      attachments?: ImageAttachmentInput[];
    },
  ) =>
    request<AIExtraction>(`/api/customers/${customerId}/ai/extract`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  aiBrief: (customerId: string) =>
    request<CustomerBrief>(`/api/customers/${customerId}/ai/brief`, {
      method: "POST",
    }),

  contextPack: (customerId: string, question = "") =>
    request<ContextPack>(`/api/customers/${customerId}/ai-context`, {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  cancelWork: (workItemId: number) =>
    request<WorkLifecycleResult>(`/api/work-items/${workItemId}/cancel`, {
      method: "POST",
    }),

  completeWork: (workItemId: number) =>
    request<WorkLifecycleResult>(`/api/work-items/${workItemId}/complete`, {
      method: "POST",
    }),

  recordInteraction: (workItemId: number, payload: InteractionPayload) =>
    request(`/api/work-items/${workItemId}/interactions`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  activityFeed: () => request<ActivityFeed>("/api/activities"),

  refreshSources: () =>
    request<{
      refreshed_at: string;
      new_count: number;
      pending_proposals_created: number;
    }>("/api/sync/refresh", { method: "POST" }),

  applyProposal: (proposalId: number) =>
    request(`/api/change-proposals/${proposalId}/apply`, {
      method: "POST",
    }),

  rejectProposal: (proposalId: number) =>
    request(`/api/change-proposals/${proposalId}/reject`, {
      method: "POST",
    }),

  advanceDemoTime: (days: number, hours = 0) =>
    request<{ demo_time: string; workbench: Workbench }>("/api/demo/time", {
      method: "POST",
      body: JSON.stringify({ days, hours }),
    }),

  resetDemo: () =>
    request<Workbench>("/api/demo/reset", {
      method: "POST",
    }),
};
