import { apiRequest } from "@/lib/apiClient";

export interface HannomFetchTokenResponse {
  token: string;
  token_preview: string;
  token_length: number;
  source: string;
  login_path: string;
  username: string;
  message: string;
}

export interface HannomTokenStatusResponse {
  configured: boolean;
  source: string;
  preview: string | null;
  token_length: number;
  expires_at?: string | null;
  username?: string | null;
  last_login_at?: string | null;
  last_error?: string | null;
}

export interface HannomCredentialsStatusResponse {
  configured: boolean;
  username: string | null;
  has_password: boolean;
  token_preview: string | null;
  token_expires_at: string | null;
  last_login_at: string | null;
  last_error: string | null;
}

export async function fetchHannomToken(payload: {
  email?: string;
  username?: string;
  password?: string;
}): Promise<HannomFetchTokenResponse> {
  return apiRequest<HannomFetchTokenResponse>("/api/developer/hannom/fetch-token", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getHannomTokenStatus(): Promise<HannomTokenStatusResponse> {
  return apiRequest<HannomTokenStatusResponse>("/api/developer/hannom/token-status", {
    method: "GET",
  });
}

export async function getHannomCredentials(): Promise<HannomCredentialsStatusResponse> {
  return apiRequest<HannomCredentialsStatusResponse>("/api/developer/hannom/credentials", {
    method: "GET",
  });
}

export async function saveHannomCredentials(payload: {
  username: string;
  password: string;
}): Promise<HannomCredentialsStatusResponse> {
  return apiRequest<HannomCredentialsStatusResponse>("/api/developer/hannom/credentials", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
