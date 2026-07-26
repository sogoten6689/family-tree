import { Steps } from "antd";
import { useTranslation } from "react-i18next";

import {
  GENEALOGY_FLOW_STEPS,
  type GenealogyFlowStepId,
} from "@/lib/genealogyFlow";

type Props = {
  currentStep: GenealogyFlowStepId;
  completedSteps?: GenealogyFlowStepId[];
  compact?: boolean;
  className?: string;
};

export function GenealogyFlowStepper({
  currentStep,
  completedSteps = [],
  compact = false,
  className,
}: Props) {
  const { t } = useTranslation();
  const currentIndex = GENEALOGY_FLOW_STEPS.indexOf(currentStep);

  return (
    <div className={className}>
      <Steps
        size={compact ? "small" : "default"}
        direction={compact ? "vertical" : "horizontal"}
        responsive={!compact}
        current={currentIndex >= 0 ? currentIndex : 0}
        items={GENEALOGY_FLOW_STEPS.map((stepId) => {
          const done = completedSteps.includes(stepId);
          const isCurrent = stepId === currentStep;
          return {
            title: t(`flow.step.${stepId}`, { defaultValue: stepId }),
            description: compact
              ? undefined
              : t(`flow.stepDesc.${stepId}`, { defaultValue: "" }),
            status: done ? "finish" : isCurrent ? "process" : "wait",
          };
        })}
      />
    </div>
  );
}
