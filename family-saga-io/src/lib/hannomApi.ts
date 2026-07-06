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
