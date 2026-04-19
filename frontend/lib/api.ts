export interface AdminSession {
  id: string;
  username: string;
}

export interface PatientSummary {
  id: string;
  telegram_user_id: number;
  first_name: string | null;
  last_name: string | null;
  username: string | null;
  last_interaction: string | null;
}

export interface DentistSummary {
  id: string;
  name: string;
  calendar_id: string;
  active_status: boolean;
  created_at?: string;
}

export interface AppointmentListItem {
  id: string;
  patient: {
    id: string;
    first_name: string | null;
    last_name: string | null;
    telegram_user_id: number;
  };
  dentist: {
    id: string;
    name: string | null;
  };
  slot_date: string;
  start_time: string;
  end_time: string;
  reason: string;
  status: string;
  created_at?: string;
}

export interface AppointmentDetail {
  id: string;
  patient: {
    id: string;
    first_name: string | null;
    last_name: string | null;
  };
  dentist: {
    id: string;
    name: string | null;
  };
  slot_date: string;
  start_time: string;
  end_time: string;
  reason: string;
  status: string;
}

export interface PatientAppointment {
  id: string;
  dentist: {
    id: string;
    name: string | null;
  };
  slot_date: string;
  status: string;
}

export interface AppointmentListResponse {
  items: AppointmentListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface DentistListResponse {
  items: DentistSummary[];
}

export interface PatientListResponse {
  items: PatientSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface PatientDetail {
  id: string;
  telegram_user_id: number;
  first_name: string | null;
  last_name: string | null;
  username: string | null;
  appointments: PatientAppointment[];
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public data: { error?: string; detail?: string; ok?: boolean }
  ) {
    super(data.error || data.detail || 'API request failed');
  }
}

function buildApiPath(path: string) {
  return `/api/proxy${path}`;
}

async function fetchApi<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = buildApiPath(path);
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  });

  const data = await response.json();

  if (!response.ok) {
    throw new ApiError(response.status, data);
  }

  return data;
}

// Auth
export const auth = {
  login: (username: string, password: string) =>
    fetchApi<{ ok: boolean; username: string }>('/admin/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  logout: () =>
    fetchApi<{ ok: boolean }>('/admin/auth/logout', { method: 'POST' }),

  getMe: () =>
    fetchApi<AdminSession>('/admin/auth/me'),
};

// Appointments
export const appointments = {
  list: (params?: { status?: string; page?: number; page_size?: number }) =>
    fetchApi<AppointmentListResponse>(
      `/admin/appointments?${new URLSearchParams(params as Record<string, string>).toString()}`
    ),

  get: (id: string) =>
    fetchApi<AppointmentDetail>(`/admin/appointments/${id}`),

  cancel: (id: string) =>
    fetchApi<{ ok: boolean; id: string; status: string }>(`/admin/appointments/${id}/cancel`, {
      method: 'PATCH',
    }),

  delete: (id: string) =>
    fetchApi<{ ok: boolean }>(`/admin/appointments/${id}`, { method: 'DELETE' }),
};

// Dentists
export const dentists = {
  list: () =>
    fetchApi<DentistListResponse>('/admin/dentists'),

  get: (id: string) =>
    fetchApi<DentistSummary>(`/admin/dentists/${id}`),

  create: (data: { name: string; calendar_id: string }) =>
    fetchApi<DentistSummary>('/admin/dentists', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: Partial<{ name: string; calendar_id: string; active_status: boolean }>) =>
    fetchApi<DentistSummary>(`/admin/dentists/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
};

// Patients
export const patients = {
  list: (params?: { page?: number; page_size?: number }) =>
    fetchApi<PatientListResponse>(
      `/admin/patients?${new URLSearchParams(params as Record<string, string>).toString()}`
    ),

  get: (id: string) =>
    fetchApi<PatientDetail>(`/admin/patients/${id}`),
};
