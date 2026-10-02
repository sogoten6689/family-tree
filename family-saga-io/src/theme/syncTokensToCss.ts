import type { GlobalToken } from "antd/es/theme/interface";
import { toHslChannels } from "./colorUtils";

export function syncAntdTokensToCssVars(
  token: GlobalToken,
  root: HTMLElement = document.documentElement,
) {
  const set = (name: string, value: string) => root.style.setProperty(name, value);

  set("--primary", toHslChannels(token.colorPrimary));
  set("--primary-foreground", toHslChannels(token.colorTextLightSolid));
  set("--background", toHslChannels(token.colorBgLayout));
  set("--foreground", toHslChannels(token.colorText));
  set("--card", toHslChannels(token.colorBgContainer));
  set("--card-foreground", toHslChannels(token.colorText));
  set("--popover", toHslChannels(token.colorBgElevated));
  set("--popover-foreground", toHslChannels(token.colorText));
  set("--muted", toHslChannels(token.colorFillAlter, token.colorBgLayout));
  set("--muted-foreground", toHslChannels(token.colorTextSecondary));
  set("--accent", toHslChannels(token.colorPrimaryBg, token.colorBgContainer));
  set("--accent-foreground", toHslChannels(token.colorPrimaryText));
  set("--secondary", toHslChannels(token.colorError));
  set("--secondary-foreground", toHslChannels(token.colorTextLightSolid));
  set("--destructive", toHslChannels(token.colorError));
  set("--destructive-foreground", toHslChannels(token.colorTextLightSolid));
  set("--border", toHslChannels(token.colorBorder));
  set("--input", toHslChannels(token.colorBorder));
  set("--ring", toHslChannels(token.colorPrimary));
  set("--brand", toHslChannels(token.colorPrimary));
  set("--brand-light", toHslChannels(token.colorPrimaryBg, token.colorBgContainer));
  set("--brand-foreground", toHslChannels(token.colorPrimaryText));
  set("--radius", `${token.borderRadius}px`);
  // --sidebar-* KHÔNG sync từ token: sidebar có bảng màu riêng (nền xanh
  // dương, chữ trắng) khai báo trong index.css cho cả light/dark. Inline
  // style ở đây sẽ đè mất :root của index.css.
  set("--antd-font-size", `${token.fontSize}px`);
  set("--antd-control-height", `${token.controlHeight}px`);
}
