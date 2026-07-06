import { useMemo } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import { BrowserRouter, Navigate, Outlet, Route, Routes, useParams } from "react-router-dom";
import { useTheme } from "next-themes";
import { getAntdTheme } from "@/lib/antdTheme";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/theme-provider";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AdminRoute } from "@/components/AdminRoute";
import PublicLayout from "@/layouts/PublicLayout";
import UserLayout from "@/layouts/UserLayout";
import AdminLayout from "@/layouts/AdminLayout";
import HomePage from "./pages/HomePage";
import GuidePage from "./pages/GuidePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import DocumentReaderPage from "./pages/DocumentReaderPage";
import FamilyTreePage from "./pages/FamilyTreePage";
import FamilyTreeManagerPage from "./pages/FamilyTreeManagerPage";
import FamilyTreeDetailPage from "./pages/admin/FamilyTreeDetailPage";
import PublicFamilyTreePage from "./pages/PublicFamilyTreePage";
import AdminUsersPage from "./pages/AdminUsersPage";
import EditDocumentPage from "./pages/EditDocumentPage";
import NotFound from "./pages/NotFound";
import ForbiddenPage from "./pages/ForbiddenPage";
import HannomConfigPage from "./pages/developer/HannomConfigPage";
import StoragePage from "./pages/developer/StoragePage";
import LogsPage from "./pages/developer/LogsPage";
import DocsPage from "./pages/developer/DocsPage";
import { DeveloperRoute } from "@/components/DeveloperRoute";

const queryClient = new QueryClient();

const AdminFamilyTreeRedirect = () => {
  const { treeId } = useParams<{ treeId: string }>();
  return <Navigate to={`/admin/gia-pha/${treeId ?? ""}`} replace />;
};

const AppContent = () => {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  const antTheme = useMemo(() => getAntdTheme(isDark), [isDark]);

  return (
    <ConfigProvider theme={antTheme}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            {/* ── Public ── */}
            <Route element={<PublicLayout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/huong-dan" element={<GuidePage />} />
              <Route path="/gia-pha/:treeId" element={<PublicFamilyTreePage />} />
            </Route>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/403" element={<ForbiddenPage />} />

            {/* ── User (đã đăng nhập) ── */}
            <Route
              path="/user"
              element={
                <ProtectedRoute>
                  <UserLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/user/dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="document-reader" element={<DocumentReaderPage />} />
              <Route path="family-tree" element={<FamilyTreePage />} />
            </Route>

            {/* ── Admin ── */}
            <Route
              path="/admin"
              element={
                <AdminRoute>
                  <AdminLayout />
                </AdminRoute>
              }
            >
              <Route index element={<Navigate to="/admin/gia-pha" replace />} />
              <Route path="gia-pha" element={<FamilyTreeManagerPage />} />
              <Route path="gia-pha/:treeId" element={<FamilyTreeDetailPage />} />
              <Route path="documents/:documentId/edit" element={<EditDocumentPage />} />
              <Route path="users" element={<AdminUsersPage />} />
              <Route
                path="developer"
                element={
                  <DeveloperRoute>
                    <Outlet />
                  </DeveloperRoute>
                }
              >
                <Route index element={<Navigate to="/admin/developer/hannom-config" replace />} />
                <Route path="hannom-config" element={<HannomConfigPage />} />
                <Route path="storage" element={<StoragePage />} />
                <Route path="logs" element={<LogsPage />} />
                <Route path="docs" element={<DocsPage />} />
              </Route>
            </Route>

            {/* Redirects cũ */}
            <Route path="/dashboard" element={<Navigate to="/user/dashboard" replace />} />
            <Route path="/document-reader" element={<Navigate to="/user/document-reader" replace />} />
            <Route path="/family-tree" element={<Navigate to="/user/family-tree" replace />} />
            <Route path="/family-tree-manager" element={<Navigate to="/admin/gia-pha" replace />} />
            <Route path="/admin/family-tree/:treeId" element={<AdminFamilyTreeRedirect />} />

            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </ConfigProvider>
  );
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
