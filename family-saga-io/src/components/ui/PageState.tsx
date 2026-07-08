import { Alert, Button, Empty, Spin } from "antd";
import type { ReactNode } from "react";

interface PageStateProps {
  loading?: boolean;
  loadingTip?: string;
  error?: string | null;
  onRetry?: () => void;
  empty?: boolean;
  emptyDescription?: string;
  emptyAction?: ReactNode;
  children: ReactNode;
}

/** Loading / Empty / Error wrapper theo DESIGN_SYSTEM_GUIDELINES */
export function PageState({
  loading,
  loadingTip = "Đang tải…",
  error,
  onRetry,
  empty,
  emptyDescription = "Không có dữ liệu",
  emptyAction,
  children,
}: PageStateProps) {
  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Spin size="large" tip={loadingTip} />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        type="error"
        showIcon
        message={error}
        action={
          onRetry ? (
            <Button size="small" onClick={onRetry}>
              Thử lại
            </Button>
          ) : undefined
        }
        className="max-w-2xl mx-auto"
      />
    );
  }

  if (empty) {
    return <Empty description={emptyDescription}>{emptyAction}</Empty>;
  }

  return <>{children}</>;
}
