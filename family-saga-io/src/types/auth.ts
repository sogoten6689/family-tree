export type UserRole = "admin" | "user";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface UserListResponse {
  total: number;
  items: User[];
}

export interface AuthSession {
  accessToken: string;
  user: User;
}
