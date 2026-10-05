import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation, useParams } from "react-router-dom";
import { ThemeContextProvider } from "@/theme/ThemeContextProvider";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/theme-provider";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AdminRoute } from "@/components/AdminRoute";
import RoleLayout from "@/layouts/RoleLayout";
import { roleHomePath } from "@/config/coreNav";
import DocumentReaderPage from "./pages/DocumentReaderPage";
import GuidePage from "./pages/GuidePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import FamilyTreeDetailPage from "./pages/admin/FamilyTreeDetailPage";
import PublicFamilyTreePage from "./pages/PublicFamilyTreePage";
import GiaPhaListPage from "./pages/GiaPhaListPage";
import AdminUsersPage from "./pages/AdminUsersPage";
import AdminDashboardPage from "./pages/admin/AdminDashboardPage";
import AdminHistoryPage from "./pages/admin/AdminHistoryPage";
import UserDocumentDetailPage from "./pages/user/UserDocumentDetailPage";
import UserFamilyTreeDetailPage from "./pages/user/UserFamilyTreeDetailPage";
import UserProfilePage from "./pages/user/UserProfilePage";
import EditDocumentPage from "./pages/EditDocumentPage";
import NotFound from "./pages/NotFound";
import ForbiddenPage from "./pages/ForbiddenPage";
import HannomConfigPage from "./pages/developer/HannomConfigPage";
import SettingsPage from "./pages/developer/SettingsPage";
import StoragePage from "./pages/developer/StoragePage";
import LogsPage from "./pages/developer/LogsPage";
import { DeveloperRoute } from "@/components/DeveloperRoute";

const queryClient = new QueryClient();

const AdminFamilyTreeRedirect = () => {
  const { treeId } = useParams<{ treeId: string }>();
  return <Navigate to={`/admin/gia-pha/${treeId ?? ""}`} replace />;
};

/** Route cũ "/user/family-trees(/:treeId)" và "/user/documents" (danh sách)
 * đã gộp vào "/user/gia-pha" — giữ redirect, kèm nguyên query (?tab=...) vì
 * genealogyFlow.ts/DocumentReaderPage vẫn sinh link theo path cũ. */
const UserGiaPhaRedirect = () => {
  const { treeId } = useParams<{ treeId: string }>();
  const { search } = useLocation();
  return <Navigate to={`/user/gia-pha${treeId ? `/${treeId}` : ""}${search}`} replace />;
};

/** Route "/" — khách ẩn danh thấy ngay màn hình tải lên/phân tích (không qua
 * trang giới thiệu); người đã đăng nhập tự chuyển sang trang tổng quan của
 * họ, tránh User/Admin lạc vào giao diện Guest. */
const GuestHomeRoute = () => {
  const { isAuthenticated, isAdmin } = useAuth();
  if (isAuthenticated) {
    return <Navigate to={roleHomePath(isAdmin ? "admin" : "user")} replace />;
  }
  return <DocumentReaderPage embedded />;
};

const AppContent = () => (
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            {/* Mọi trang dùng chung 1 RoleLayout — menu theo vai trò người đang
                đăng nhập, không theo tiền tố URL. Quyền truy cập kiểm tra theo
                từng nhóm route bên dưới. */}
            <Route element={<RoleLayout />}>
              {/* ── Công khai ── */}
              <Route path="/" element={<GuestHomeRoute />} />
              <Route path="/huong-dan" element={<GuidePage />} />
              <Route path="/gia-pha" element={<GiaPhaListPage scope="public" />} />
              <Route path="/gia-pha/:treeId" element={<PublicFamilyTreePage />} />

              {/* ── User (đã đăng nhập) ── */}
              <Route
                path="/user"
                element={
                  <ProtectedRoute>
                    <Outlet />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Navigate to="/user/dashboard" replace />} />
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="document-reader" element={<Navigate to="/user/documents/new" replace />} />
                <Route path="gia-pha" element={<GiaPhaListPage scope="user" />} />
                <Route path="gia-pha/:treeId" element={<UserFamilyTreeDetailPage />} />
                {/* Chi tiết bộ gia phả chưa dựng cây (+ "/new" = màn hình tải lên) */}
                <Route path="documents/:scanId" element={<UserDocumentDetailPage />} />
                <Route path="documents" element={<UserGiaPhaRedirect />} />
                <Route path="family-trees" element={<UserGiaPhaRedirect />} />
                <Route path="family-trees/:treeId" element={<UserGiaPhaRedirect />} />
                <Route path="family-tree" element={<Navigate to="/user/gia-pha" replace />} />
                <Route path="huong-dan" element={<Navigate to="/huong-dan" replace />} />
                <Route path="profile" element={<UserProfilePage />} />
              </Route>

              {/* ── Admin ── */}
              <Route
                path="/admin"
                element={
                  <AdminRoute>
                    <Outlet />
                  </AdminRoute>
                }
              >
                <Route index element={<Navigate to="/admin/dashboard" replace />} />
                <Route path="dashboard" element={<AdminDashboardPage />} />
                <Route path="gia-pha" element={<GiaPhaListPage scope="admin" />} />
                <Route path="gia-pha/:treeId" element={<FamilyTreeDetailPage />} />
                <Route path="history" element={<AdminHistoryPage />} />
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
                  <Route path="settings" element={<SettingsPage />} />
                  <Route path="storage" element={<StoragePage />} />
                  <Route path="logs" element={<LogsPage />} />
                </Route>
              </Route>
            </Route>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/403" element={<ForbiddenPage />} />

            {/* Redirects cũ */}
            <Route path="/dashboard" element={<Navigate to="/user/dashboard" replace />} />
            <Route path="/document-reader" element={<Navigate to="/user/documents/new" replace />} />
            <Route path="/family-tree" element={<Navigate to="/user/gia-pha" replace />} />
            <Route path="/family-tree-manager" element={<Navigate to="/admin/gia-pha" replace />} />
            <Route path="/admin/family-tree/:treeId" element={<AdminFamilyTreeRedirect />} />

            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
);

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <ThemeContextProvider>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </ThemeContextProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
