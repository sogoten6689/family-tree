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
      // Nền tối: antd mặc định đen (#141414) — nâng lên xám xanh cho dịu mắt, khớp --background/--card.
      ...(isDark
        ? {
            colorBgContainer: "#242c38",
            colorBgElevated: "#28313e",
            colorBgLayout: "#192029",
            colorBorder: "#3b4554",
            colorBorderSecondary: "#323b48",
          }
        : { colorBgLayout: "#f4f7fb" }),
    },
    components: {
      Layout: {
        siderBg: isDark ? "#172c4a" : "#0f2a52",
        bodyBg: isDark ? "#192029" : "#f4f7fb",
        headerBg: isDark ? "#353c46" : "#e2e5e9",
        triggerBg: isDark ? "#353c46" : "#e2e5e9",
      },
      Menu: {
        itemBorderRadius: 8,
        darkItemBg: "transparent",
        darkSubMenuItemBg: "transparent",
      },
      Table: {
        headerBg: isDark ? "#313b49" : "#edf2f7",
        rowHoverBg: isDark ? "#313b49" : "#f1f5f9",
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
