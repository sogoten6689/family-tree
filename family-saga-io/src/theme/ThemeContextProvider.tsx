import { useEffect, useMemo } from "react";
import { ConfigProvider, theme as antdThemeLib } from "antd";
import { useTheme } from "next-themes";
import { getAntdTheme } from "./antdTheme";
import { syncAntdTokensToCssVars } from "./syncTokensToCss";

function AntdCssBridge() {
  const { token } = antdThemeLib.useToken();

  useEffect(() => {
    syncAntdTokensToCssVars(token);
  }, [token]);

  return null;
}

export function ThemeContextProvider({ children }: { children: React.ReactNode }) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  const antTheme = useMemo(() => getAntdTheme(isDark), [isDark]);

  return (
    <ConfigProvider theme={antTheme}>
      <AntdCssBridge />
      {children}
    </ConfigProvider>
  );
}
