import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider, theme as antdTheme } from "antd";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useTheme } from "next-themes";
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
import AdminUsersPage from "./pages/AdminUsersPage";
import EditDocumentPage from "./pages/EditDocumentPage";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const AppContent = () => {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
        token: {
          colorPrimary: "#1677ff",
          borderRadius: 12,
          fontFamily: "Roboto, sans-serif",
        },
        components: {
          Layout: {
            siderBg: "#f8f9fa",
            headerBg: "#ffffff",
            bodyBg: "#f0f2f5",
          },
          Menu: {
            itemBorderRadius: 8,
          },
        },
      }}
    >
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            {/* ── Public ── */}
            <Route element={<PublicLayout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/huong-dan" element={<GuidePage />} />
            </Route>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

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
              <Route path="documents/:documentId/edit" element={<EditDocumentPage />} />
              <Route path="users" element={<AdminUsersPage />} />
            </Route>

            {/* Redirects cũ */}
            <Route path="/dashboard" element={<Navigate to="/user/dashboard" replace />} />
            <Route path="/document-reader" element={<Navigate to="/user/document-reader" replace />} />
            <Route path="/family-tree" element={<Navigate to="/user/family-tree" replace />} />
            <Route path="/family-tree-manager" element={<Navigate to="/admin/gia-pha" replace />} />

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
