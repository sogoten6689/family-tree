import { apiRequest } from "@/lib/apiClient";
import type { TokenResponse, User, UserListResponse, UserRole } from "@/types/auth";

export async function registerUser(payload: {
  email: string;
  password: string;
  full_name: string;
}): Promise<User> {
  return apiRequest<User>("/api/register", {
    method: "POST",
    body: JSON.stringify(payload),
  }, null);
}

export async function loginUser(payload: {
  email: string;
  password: string;
}): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/api/login", {
    method: "POST",
    body: JSON.stringify(payload),
  }, null);
}

export async function fetchCurrentUser(accessToken: string): Promise<User> {
  return apiRequest<User>("/api/me", { method: "GET" }, accessToken);
}

export async function fetchUsers(): Promise<UserListResponse> {
  return apiRequest<UserListResponse>("/api/users", { method: "GET" });
}

export async function updateUserRole(userId: number, role: UserRole): Promise<User> {
  return apiRequest<User>(`/api/users/${userId}/role`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export async function deleteUser(userId: number): Promise<void> {
  await apiRequest<{ message: string }>(`/api/users/${userId}`, {
    method: "DELETE",
  });
}
