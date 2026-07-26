import type { GenealogyFlowStepId } from "@/lib/genealogyFlow";
import { flowRouteForStep } from "@/lib/genealogyFlow";
import type { UserScan, UserStats } from "@/lib/userWorkspaceApi";

export type FlowProgress = {
  completedSteps: GenealogyFlowStepId[];
  currentStep: GenealogyFlowStepId;
  nextRoute: string;
  nextStep: GenealogyFlowStepId | null;
};

export function computeFlowProgress(
  stats: UserStats,
  scans: UserScan[] = [],
): FlowProgress {
  const completed: GenealogyFlowStepId[] = [];
  let current: GenealogyFlowStepId = "material";

  if (stats.scanned_documents > 0 || scans.length > 0) {
    completed.push("material");
    current = "ocr";
  }

  const latestScan = scans[0];
  const hasOcrDone = scans.some(
    (s) => s.ocr_status === "completed" || s.ocr_status === "skipped",
  );
  if (hasOcrDone) {
    if (!completed.includes("ocr")) completed.push("ocr");
    current = "extract";
  }

  const hasExtract = scans.some(
    (s) => s.request_id || s.tree_status === "draft" || s.tree_status === "created",
  );
  if (hasExtract) {
    if (!completed.includes("extract")) completed.push("extract");
    current = "canonical";
  }

  if (stats.family_trees > 0) {
    completed.push("canonical", "visual");
    current = "export";
  }

  const createdTree = scans.find((s) => s.family_tree_id && s.tree_status === "created");
  if (createdTree?.family_tree_id) {
    completed.push("export");
    current = "export";
  }

  let nextStep: GenealogyFlowStepId | null = null;
  let nextRoute = "/user/documents/new";

  if (stats.scanned_documents === 0) {
    nextStep = "material";
    nextRoute = "/user/documents/new";
  } else if (!hasOcrDone && latestScan) {
    nextStep = "ocr";
    nextRoute = flowRouteForStep("ocr", { scanId: latestScan.id });
  } else if (!hasExtract && latestScan) {
    nextStep = "extract";
    nextRoute = flowRouteForStep("extract", { scanId: latestScan.id });
  } else if (stats.family_trees === 0 && latestScan) {
    nextStep = "canonical";
    nextRoute = flowRouteForStep("extract", { scanId: latestScan.id });
  } else if (createdTree?.family_tree_id) {
    nextStep = "visual";
    nextRoute = flowRouteForStep("visual", { treeId: createdTree.family_tree_id });
  } else if (stats.family_trees > 0) {
    nextStep = "export";
    nextRoute = flowRouteForStep("export");
  }

  return {
    completedSteps: completed,
    currentStep: current,
    nextRoute,
    nextStep,
  };
}

export function computeFlowProgressForScan(scan: UserScan): {
  completedSteps: GenealogyFlowStepId[];
  currentStep: GenealogyFlowStepId;
} {
  const completed: GenealogyFlowStepId[] = ["material"];
  let current: GenealogyFlowStepId = "ocr";

  if (scan.ocr_status === "completed" || scan.ocr_status === "skipped") {
    completed.push("ocr");
    current = "extract";
  }

  if (scan.request_id || scan.tree_status === "draft" || scan.tree_status === "created") {
    completed.push("extract");
    current = "canonical";
  }

  if (scan.family_tree_id && scan.tree_status === "created") {
    completed.push("canonical", "visual");
    current = "export";
  }

  return { completedSteps: completed, currentStep: current };
}
