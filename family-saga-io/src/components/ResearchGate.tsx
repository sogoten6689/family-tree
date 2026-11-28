import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { RESEARCH_HOME, isResearchPath, researchMode } from "@/config/researchMode";

/** Chế độ nghiên cứu: trang đã đóng chuyển về trang đối chiếu. Tắt chế độ thì không làm gì. */
export const ResearchGate = ({ children }: { children: ReactNode }) => {
  const { pathname } = useLocation();
  if (researchMode() && !isResearchPath(pathname)) return <Navigate to={RESEARCH_HOME} replace />;
  return <>{children}</>;
};
