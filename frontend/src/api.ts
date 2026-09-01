const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

interface Manufacturer {
  id: string;
  name: string;
  drap_license_no: string;
  contact_email?: string;
  contact_phone?: string;
  created_at: string;
  is_active: boolean;
  is_verified: boolean;
  email_verified: boolean;
  role: string;
  totp_enabled: boolean;
  last_login: string | null;
}

interface Batch {
  id: string;
  manufacturer_id: string;
  drug_name: string;
  manufacturer_name: string;
  draper_reg_no: string;
  batch_number: string;
  manufacture_date: string;
  expiry_date: string;
  signed_code: string;
  status: string;
  created_at: string;
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface VerificationResult {
  status: "genuine" | "expired" | "not_found" | "suspicious" | "recalled";
  detail: string;
  drug_name?: string;
  batch_number?: string;
  manufacture_date?: string;
  expiry_date?: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private getHeaders(): HeadersInit {
    const token = localStorage.getItem("medverify_token");
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };
    if (token) {
      (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
    }
    return headers;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth endpoints
  async login(drapLicenseNo: string, password?: string, totpToken?: string) {
    return this.request<{
      access_token: string;
      refresh_token: string;
      token_type: string;
      manufacturer: Manufacturer;
    }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ drap_license_no: drapLicenseNo, password, totp_token: totpToken }),
    });
  }

  async register(payload: any) {
    return this.request("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async getProfile() {
    return this.request<Manufacturer>("/auth/me");
  }

  async refreshToken(refreshToken: string) {
    return this.request("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  async logout() {
    return this.request("/auth/logout", { method: "POST" });
  }

  // Batch endpoints
  async registerBatch(payload: any) {
    return this.request<Batch>("/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async listBatches(page = 1, pageSize = 50) {
    return this.request<PaginatedResponse<Batch>>(`/batches?page=${page}&page_size=${pageSize}`);
  }

  async verifyCode(signedCode: string) {
    return this.request<VerificationResult>(`/verify/${encodeURIComponent(signedCode)}`);
  }

  async getQrCode(url: string) {
    return fetch(`${this.baseUrl}/qr?url=${encodeURIComponent(url)}`);
  }

  async reportSuspicious(code: string, reason: string) {
    return this.request("/report", {
      method: "POST",
      body: JSON.stringify({ code, reason }),
    });
  }

  async getAdminFlags() {
    return this.request<any[]>("/admin/flags");
  }

  async getAdminBatches() {
    return this.request<any[]>("/admin/batches");
  }

  async getAdminSuspicious() {
    return this.request<any[]>("/admin/suspicious");
  }

  async getAdminBatchScans(batchId: string) {
    return this.request<any[]>(`/admin/batches/${batchId}/scans`);
  }

  async resolveAdminFlag(flagId: string) {
    return this.request(`/admin/flags/${flagId}/resolve`, { method: "POST" });
  }
}

export const api = new ApiClient();
export default api;