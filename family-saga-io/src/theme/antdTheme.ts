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
        siderBg: isDark ? "#0f1412" : "#f0f7f2",
        bodyBg: isDark ? "#0f1412" : "#f7fbf8",
        headerBg: isDark ? "#141a17" : "#ffffff",
        triggerBg: isDark ? "#141a17" : "#f0f7f2",
      },
      Menu: {
        itemBorderRadius: 8,
        darkItemBg: "#141a17",
        darkSubMenuItemBg: "#141a17",
        darkItemSelectedBg: "#1a2e24",
      },
      Table: {
        headerBg: isDark ? "#1a221d" : "#eef5f0",
        rowHoverBg: isDark ? "#1a221d" : "#f0f7f2",
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
