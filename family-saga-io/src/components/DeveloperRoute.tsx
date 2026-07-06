import { Spin } from "antd";
import { Navigate, useLocation } from "react-router-dom";

import { isDeveloperPath } from "@/config/developerRoutes";
import { useAuth } from "@/contexts/AuthContext";

export function DeveloperRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isAdmin, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (isDeveloperPath(location.pathname) && !isAdmin) {
    return <Navigate to="/403" replace />;
  }

  if (!isAdmin) {
    return <Navigate to="/403" replace />;
  }

  return <>{children}</>;
}
