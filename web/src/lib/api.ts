const API_BASE = "http://127.0.0.1:8000";

export interface ApiResponse {
  session_id?: string;
  answer?: any;
  chart?: any;
  insights?: any;
  anomalies?: string[];
  recommendations?: string[];
  follow_up_questions?: string[];
  suggested_questions?: string[];
  conversation_state?: {
    mode: string;
    used_prior_context: boolean;
    carried_from_previous?: string[];
    turn_count?: number;
  };
  humanized_chat_answer?: string;
  verification?: any;
  query_plan?: any;
  detail?: string;
}

export interface StatsResponse {
  row_count: number;
  column_count: number;
  columns: string[];
  numeric_columns: string[];
  datetime_columns: string[];
  categorical_columns: string[];
  summary: any;
  unique_values: any;
}

export async function askQuestion(
  question: string,
  language: string = "en",
  sessionId?: string
): Promise<{ status: number; data: ApiResponse }> {
  try {
    const res = await fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, language, session_id: sessionId || null }),
    });
    const data = await res.json();
    return { status: res.status, data };
  } catch (error: any) {
    return { status: 500, data: { detail: error.message || "Failed to connect to backend." } };
  }
}

export async function resetSession(sessionId: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/reset-session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function uploadDataset(file: File): Promise<{ status: number; data: any }> {
  const formData = new FormData();
  formData.append("file", file);
  try {
    const res = await fetch(`${API_BASE}/upload-csv`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    return { status: res.status, data };
  } catch (error: any) {
    return { status: 500, data: { detail: error.message || "Failed to upload file." } };
  }
}

export async function fetchStats(): Promise<any | null> {
  try {
    const res = await fetch(`${API_BASE}/profile`);
    if (res.ok) {
      const data = await res.json();
      // Backend returns null when no dataset is loaded
      if (!data || data.error) return null;
      return data;
    }
    return null;
  } catch {
    return null;
  }
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

export async function clearDataset(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/clear-dataset`, { method: "POST" });
    return res.ok;
  } catch {
    return false;
  }
}

export interface DbConnectionParams {
  db_type: string;
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  table_name?: string;
  query?: string;
  row_limit?: number;
}

export async function listTables(params: Omit<DbConnectionParams, 'table_name' | 'query' | 'row_limit'>): Promise<{ status: number; data: any }> {
  try {
    const res = await fetch(`${API_BASE}/list-tables`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    const data = await res.json();
    return { status: res.status, data };
  } catch (error: any) {
    return { status: 500, data: { detail: error.message || "Failed to connect to database." } };
  }
}

export async function connectDatabase(params: DbConnectionParams): Promise<{ status: number; data: any }> {
  try {
    const res = await fetch(`${API_BASE}/connect-db`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    const data = await res.json();
    return { status: res.status, data };
  } catch (error: any) {
    return { status: 500, data: { detail: error.message || "Failed to connect to database." } };
  }
}
