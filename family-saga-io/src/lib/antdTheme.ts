import { theme as antdTheme, type ThemeConfig } from "antd";

export function getAntdTheme(isDark: boolean): ThemeConfig {
  return {
    algorithm: isDark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
    token: {
      colorPrimary: "#1677ff",
      borderRadius: 12,
      fontFamily: "Roboto, sans-serif",
      colorBgContainer: isDark ? "#1f1f1f" : "#ffffff",
      colorBgElevated: isDark ? "#2a2a2a" : "#ffffff",
      colorBgLayout: isDark ? "#141414" : "#f0f2f5",
      colorText: isDark ? "rgba(255, 255, 255, 0.88)" : "rgba(0, 0, 0, 0.88)",
      colorTextSecondary: isDark ? "rgba(255, 255, 255, 0.65)" : "rgba(0, 0, 0, 0.65)",
      colorTextTertiary: isDark ? "rgba(255, 255, 255, 0.45)" : "rgba(0, 0, 0, 0.45)",
      colorBorder: isDark ? "#424242" : "#d9d9d9",
      colorBorderSecondary: isDark ? "#303030" : "#f0f0f0",
      colorFillAlter: isDark ? "#262626" : "#fafafa",
    },
    components: {
      Layout: {
        siderBg: isDark ? "#141414" : "#f8f9fa",
        headerBg: isDark ? "#1f1f1f" : "#ffffff",
        bodyBg: isDark ? "#141414" : "#f0f2f5",
        triggerBg: isDark ? "#1f1f1f" : "#f8f9fa",
      },
      Menu: {
        itemBorderRadius: 8,
        darkItemBg: "#141414",
        darkSubMenuItemBg: "#141414",
        darkItemSelectedBg: "#111d2c",
      },
      Table: {
        headerBg: isDark ? "#262626" : "#fafafa",
        rowHoverBg: isDark ? "#262626" : "#fafafa",
        borderColor: isDark ? "#424242" : "#f0f0f0",
      },
      Card: {
        colorBgContainer: isDark ? "#1f1f1f" : "#ffffff",
      },
      Drawer: {
        colorBgElevated: isDark ? "#1f1f1f" : "#ffffff",
      },
      Modal: {
        contentBg: isDark ? "#1f1f1f" : "#ffffff",
        headerBg: isDark ? "#1f1f1f" : "#ffffff",
      },
    },
  };
}
