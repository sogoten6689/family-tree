import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Outlet, Route, Routes, useParams } from "react-router-dom";
import { ThemeContextProvider } from "@/theme/ThemeContextProvider";
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
import FamilyTreeManagerPage from "./pages/FamilyTreeManagerPage";
import FamilyTreeDetailPage from "./pages/admin/FamilyTreeDetailPage";
import PublicFamilyTreePage from "./pages/PublicFamilyTreePage";
import PublicFamilyTreeListPage from "./pages/PublicFamilyTreeListPage";
import AdminUsersPage from "./pages/AdminUsersPage";
import AdminDashboardPage from "./pages/admin/AdminDashboardPage";
import AdminHistoryPage from "./pages/admin/AdminHistoryPage";
import UserDocumentsPage from "./pages/user/UserDocumentsPage";
import UserDocumentDetailPage from "./pages/user/UserDocumentDetailPage";
import UserFamilyTreesPage from "./pages/user/UserFamilyTreesPage";
import UserFamilyTreeDetailPage from "./pages/user/UserFamilyTreeDetailPage";
import UserProfilePage from "./pages/user/UserProfilePage";
import EditDocumentPage from "./pages/EditDocumentPage";
import NotFound from "./pages/NotFound";
import ForbiddenPage from "./pages/ForbiddenPage";
import HannomConfigPage from "./pages/developer/HannomConfigPage";
import StoragePage from "./pages/developer/StoragePage";
import LogsPage from "./pages/developer/LogsPage";
import DocsPage from "./pages/developer/DocsPage";
import VietnamGiaPhaCrawlPage from "./pages/developer/VietnamGiaPhaCrawlPage";
import NomFoundationCrawlPage from "./pages/developer/NomFoundationCrawlPage";
import { DeveloperRoute } from "@/components/DeveloperRoute";

const queryClient = new QueryClient();

const AdminFamilyTreeRedirect = () => {
  const { treeId } = useParams<{ treeId: string }>();
  return <Navigate to={`/admin/gia-pha/${treeId ?? ""}`} replace />;
};

const AppContent = () => (
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            {/* ── Public ── */}
            <Route element={<PublicLayout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/huong-dan" element={<GuidePage />} />
              <Route path="/gia-pha" element={<PublicFamilyTreeListPage />} />
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
              <Route path="document-reader" element={<Navigate to="/user/documents/new" replace />} />
              <Route path="documents" element={<UserDocumentsPage />} />
              <Route path="documents/:scanId" element={<UserDocumentDetailPage />} />
              <Route path="family-trees" element={<UserFamilyTreesPage />} />
              <Route path="family-trees/:treeId" element={<UserFamilyTreeDetailPage />} />
              <Route path="family-tree" element={<Navigate to="/user/family-trees" replace />} />
              <Route path="profile" element={<UserProfilePage />} />
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
              <Route index element={<Navigate to="/admin/dashboard" replace />} />
              <Route path="dashboard" element={<AdminDashboardPage />} />
              <Route path="gia-pha" element={<FamilyTreeManagerPage />} />
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
                <Route path="storage" element={<StoragePage />} />
                <Route path="vietnamgiapha-crawl" element={<VietnamGiaPhaCrawlPage />} />
                <Route path="nomfoundation-crawl" element={<NomFoundationCrawlPage />} />
                <Route path="logs" element={<LogsPage />} />
                <Route path="docs" element={<DocsPage />} />
              </Route>
            </Route>

            {/* Redirects cũ */}
            <Route path="/dashboard" element={<Navigate to="/user/dashboard" replace />} />
            <Route path="/document-reader" element={<Navigate to="/user/documents/new" replace />} />
            <Route path="/family-tree" element={<Navigate to="/user/family-trees" replace />} />
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
