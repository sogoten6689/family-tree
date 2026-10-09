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
        siderBg: isDark ? "#0e203a" : "#0f2a52",
        bodyBg: isDark ? "#0e131b" : "#f4f7fb",
        headerBg: isDark ? "#161d27" : "#ffffff",
        triggerBg: isDark ? "#161d27" : "#ffffff",
      },
      Menu: {
        itemBorderRadius: 8,
        darkItemBg: "transparent",
        darkSubMenuItemBg: "transparent",
      },
      Table: {
        headerBg: isDark ? "#212a36" : "#edf2f7",
        rowHoverBg: isDark ? "#212a36" : "#f1f5f9",
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
