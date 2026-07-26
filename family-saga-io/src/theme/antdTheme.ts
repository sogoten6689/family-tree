import { theme as antdTheme, type ThemeConfig } from "antd";
import { brandSeed, darkSeedOverrides } from "./seedTokens";

export function getAntdTheme(isDark: boolean): ThemeConfig {
  return {
    cssVar: { prefix: "ant" },
    hashed: false,
    algorithm: isDark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
    token: {
      ...brandSeed,
      ...(isDark ? darkSeedOverrides : {}),
    },
    components: {
      Layout: {
        siderBg: isDark ? "#141414" : "#fafafa",
        bodyBg: isDark ? "#141414" : "#f5f5f5",
        headerBg: isDark ? "#1f1f1f" : "#ffffff",
        triggerBg: isDark ? "#1f1f1f" : "#fafafa",
      },
      Menu: {
        itemBorderRadius: 8,
        darkItemBg: "#141414",
        darkSubMenuItemBg: "#141414",
      },
      Table: {
        headerBg: isDark ? "#262626" : "#fafafa",
        rowHoverBg: isDark ? "#262626" : "#fafafa",
      },
      Button: {
        primaryShadow: "none",
        controlHeightLG: 48,
      },
      Typography: {
        fontFamilyCode: "Roboto, monospace",
      },
    },
  };
}
