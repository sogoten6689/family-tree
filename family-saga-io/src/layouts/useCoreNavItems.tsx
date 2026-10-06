import { BranchesOutlined, FileSearchOutlined, InboxOutlined, ReadOutlined } from "@ant-design/icons";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { CORE_NAV_ITEMS, type CoreNavKey } from "@/config/coreNav";

const CORE_NAV_ICON_MAP: Record<CoreNavKey, React.ReactNode> = {
  upload: <InboxOutlined />,
  "gia-pha": <BranchesOutlined />,
  genealogy: <FileSearchOutlined />,
  guide: <ReadOutlined />,
};

/** Mục menu lõi (antd Menu items) — 3 layout dùng chung để menu luôn giống nhau. */
export function useCoreNavItems() {
  const { t } = useTranslation();
  return useMemo(
    () =>
      CORE_NAV_ITEMS.map((item) => ({
        key: item.key,
        icon: CORE_NAV_ICON_MAP[item.key],
        label: t(item.labelKey, { defaultValue: item.labelDefault }),
      })),
    [t],
  );
}
