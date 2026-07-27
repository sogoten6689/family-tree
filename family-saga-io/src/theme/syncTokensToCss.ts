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
  set("--sidebar-background", toHslChannels(token.colorBgContainer));
  set("--sidebar-foreground", toHslChannels(token.colorText));
  set("--sidebar-primary", toHslChannels(token.colorPrimary));
  set("--sidebar-border", toHslChannels(token.colorBorder));
  set("--sidebar-ring", toHslChannels(token.colorPrimary));
  set("--sidebar-accent", toHslChannels(token.colorFillAlter, token.colorBgContainer));
  set("--sidebar-accent-foreground", toHslChannels(token.colorText));
  set("--sidebar-primary-foreground", toHslChannels(token.colorTextLightSolid));
  set("--antd-font-size", `${token.fontSize}px`);
  set("--antd-control-height", `${token.controlHeight}px`);
}
