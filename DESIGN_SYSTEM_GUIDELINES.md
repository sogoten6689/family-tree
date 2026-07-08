# Design System Guidelines

> **Single Source of Truth:** Ant Design v6  
> **Stack:** React 18 · Vite · TypeScript · React Router v6 · Antd v6 · Tailwind · shadcn/ui  
> **Phạm vi:** Theme đồng bộ · Landing Page · UX/UI toàn hệ thống  
> **Tính chất:** Quy tắc **bắt buộc** — Dev phải tuân thủ, PR vi phạm sẽ bị reject.

---

## Mục lục

1. [Phân tích hiện trạng](#1-phân-tích-hiện-trạng)
2. [Đồng bộ theme — Antd v6 làm trung tâm](#2-đồng-bộ-theme--antd-v6-làm-trung-tâm)
3. [Code mẫu triển khai](#3-code-mẫu-triển-khai)
4. [Quy tắc component (Do's & Don'ts)](#4-quy-tắc-component-dos--donts)
5. [Quy tắc Landing Page](#5-quy-tắc-landing-page)
6. [Quy tắc UX/UI toàn hệ thống](#6-quy-tắc-uxui-toàn-hệ-thống)
7. [Migration checklist](#7-migration-checklist)
8. [Anti-patterns](#8-anti-patterns)
9. [Phụ lục](#9-phụ-lục)

---

## 1. Phân tích hiện trạng

### 1.1. Luồng theme hiện tại

```
App.tsx
└── ThemeProvider (next-themes)     → class .dark trên <html>
    └── AppContent
        └── ConfigProvider          → getAntdTheme(isDark) — KHÔNG bật cssVar
            └── Routes / Layouts / Pages
```

| File | Vai trò | Vấn đề |
|------|---------|--------|
| `src/lib/antdTheme.ts` | Seed + Component token | Màu `#1677ff`, **chưa `cssVar: true`** |
| `src/index.css` | Palette shadcn HSL độc lập | `--gold`, `--primary: 36 70% 42%` ≠ Antd |
| `tailwind.config.ts` | `hsl(var(--*))` | Không map `--ant-*` |
| `src/pages/HomePage.tsx` | Landing hero | **Inline `style={{ color: 'hsl(36,70%,42%)' }}`** — vi phạm SSOT |
| `components.json` | shadcn `baseColor: slate` | Palette riêng, không theo Antd |

### 1.2. Xung đột cụ thể (đã quét codebase)

| Vùng UI | Antd | Tailwind/shadcn | Landing (`HomePage`) |
|---------|------|-----------------|----------------------|
| Primary | `#1677ff` | `hsl(36 70% 42%)` vàng | `hsl(36, 70%, 42%)` inline trên Button |
| Nền layout | `#f0f2f5` | `hsl(39 50% 96%)` parchment | `bg-background` (shadcn) |
| Radius | `12px` | `--radius: 0.5rem` (8px) | — |
| Typography | `Roboto` token | `font-display` Playfair/Lora* | `font-display`, `font-body` class |

\* `tailwind.config.ts` khai báo Playfair/Lora nhưng `index.css` override body → Roboto.

### 1.3. Giải pháp bắt buộc

1. Bật **`cssVar: { prefix: 'ant' }`** → sinh `--ant-color-primary`, `--ant-border-radius`, …
2. Map **trực tiếp** trong `tailwind.config.ts`: `primary: 'var(--ant-color-primary)'`
3. Bridge HSL cho shadcn (`--primary`) từ `theme.useToken()` — **một chiều, từ Antd ra**
4. **Xóa** palette cứng trong `index.css` `:root` / `.dark`
5. **Cấm** inline hex/hsl trong Landing — dùng token class

### 1.4. Landing pages trong dự án

| Route | File | Layout |
|-------|------|--------|
| `/` | `HomePage.tsx` | Hero + Features + Stats + About |
| `/huong-dan` | `GuidePage.tsx` | Public content |
| `/gia-pha` | `PublicFamilyTreeListPage.tsx` | Public gallery |
| `/login`, `/register` | `LoginPage`, `RegisterPage` | Auth form |

**Nhận xét:** Landing dùng **Tailwind layout + Antd Button** nhưng override màu bằng `style={{}}` → phải chuẩn hóa theo token.

**Motion:** Dự án **chưa có** `framer-motion`. Dùng Tailwind `transition-*`, `animate-*` (plugin `tailwindcss-animate`). Nếu thêm framer-motion sau này → chỉ dùng trên Landing, lazy-load.

---

## 2. Đồng bộ theme — Antd v6 làm trung tâm

### 2.1. Pipeline token (3 tầng)

```
SEED TOKEN (seedTokens.ts — SSOT)
    ↓ algorithm (default / dark)
MAP TOKEN (Antd tự tính: colorPrimaryBg, colorBgContainer, …)
    ↓
COMPONENT TOKEN (Layout, Table, Button, … trong antdTheme.ts)
    ↓ cssVar: true
CSS Variables --ant-*  →  Tailwind + shadcn đọc
```

### 2.2. Quy tắc SSOT

| # | Quy tắc |
|---|---------|
| SSOT-1 | Mọi màu brand chỉ sửa tại `src/theme/seedTokens.ts` → `colorPrimary` |
| SSOT-2 | `antdTheme.ts` bật `cssVar: { prefix: 'ant' }` + `hashed: false` |
| SSOT-3 | Tailwind **ưu tiên** `var(--ant-*)`; shadcn dùng `hsl(var(--primary))` từ bridge |
| SSOT-4 | **Cấm** hex/rgb/hsl literal trong className, inline style, CSS file (trừ asset ảnh) |
| SSOT-5 | Dark mode: **một** nguồn — `next-themes` + Antd `darkAlgorithm`, không `dark:bg-[#xxx]` |

### 2.3. `cssVar` — cầu nối bắt buộc

Khi bật `cssVar`, Antd inject lên DOM:

```css
--ant-color-primary
--ant-color-success
--ant-color-warning
--ant-color-error
--ant-color-bg-container
--ant-color-bg-layout
--ant-color-text
--ant-color-text-secondary
--ant-color-border
--ant-border-radius
--ant-font-size
/* … */
```

Tailwind đọc **trực tiếp** — không cần hardcode hex trong config.

---

## 3. Code mẫu triển khai

### 3.1. `src/theme/seedTokens.ts`

```typescript
/** SSOT — CHỈ SỬA MÀU BRAND TẠI ĐÂY */
export const brandSeed = {
  colorPrimary: "#b8860b",   // brand vàng gia phả (thống nhất Landing + App)
  colorSuccess: "#52c41a",
  colorWarning: "#faad14",
  colorError: "#ff4d4f",
  colorInfo: "#1677ff",
  borderRadius: 12,
  fontSize: 14,
  fontFamily: "Roboto, -apple-system, BlinkMacSystemFont, sans-serif",
  controlHeight: 36,
} as const;

export const darkSeedOverrides = {
  colorPrimary: "#d4a017",
} as const;
```

### 3.2. `src/theme/antdTheme.ts`

```typescript
import { theme as antdTheme, type ThemeConfig } from "antd";
import { brandSeed, darkSeedOverrides } from "./seedTokens";

export function getAntdTheme(isDark: boolean): ThemeConfig {
  return {
    cssVar: { prefix: "ant" },   // ← BẮT BUỘC
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
      },
      Table: {
        headerBg: isDark ? "#262626" : "#fafafa",
      },
      Button: { primaryShadow: "none" },
      Typography: {
        fontFamilyCode: "Roboto, monospace",
      },
    },
  };
}
```

### 3.3. `src/theme/syncTokensToCss.ts` (bridge shadcn)

```typescript
import type { GlobalToken } from "antd/es/theme/interface";

function toHslChannels(color: string): string {
  /* hex/rgb → "H S% L%" — xem bản đầy đủ trong repo */
  // ...
  return "0 0% 0%";
}

/** Map Antd GlobalToken → biến shadcn (HSL channels) */
export function syncAntdTokensToCssVars(token: GlobalToken) {
  const root = document.documentElement;
  const set = (k: string, v: string) => root.style.setProperty(k, v);

  set("--primary", toHslChannels(token.colorPrimary));
  set("--primary-foreground", toHslChannels(token.colorTextLightSolid));
  set("--background", toHslChannels(token.colorBgLayout));
  set("--foreground", toHslChannels(token.colorText));
  set("--card", toHslChannels(token.colorBgContainer));
  set("--border", toHslChannels(token.colorBorder));
  set("--muted-foreground", toHslChannels(token.colorTextSecondary));
  set("--destructive", toHslChannels(token.colorError));
  set("--radius", `${token.borderRadius}px`);
  set("--brand", toHslChannels(token.colorPrimary));
  set("--brand-light", toHslChannels(token.colorPrimaryBg));
}
```

### 3.4. `src/theme/ThemeContextProvider.tsx`

```tsx
import { useEffect, useMemo } from "react";
import { ConfigProvider, theme as antdThemeLib } from "antd";
import { useTheme } from "next-themes";
import { getAntdTheme } from "./antdTheme";
import { syncAntdTokensToCssVars } from "./syncTokensToCss";

function AntdCssBridge() {
  const { token } = antdThemeLib.useToken();
  useEffect(() => { syncAntdTokensToCssVars(token); }, [token]);
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
```

### 3.5. `tailwind.config.ts` — map trực tiếp `--ant-*`

```typescript
import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "1.5rem", screens: { "2xl": "1280px" } },
    extend: {
      colors: {
        // ── Lớp 1: Antd cssVar (ưu tiên cho màu thuần) ──
        primary: "var(--ant-color-primary)",
        success: "var(--ant-color-success)",
        warning: "var(--ant-color-warning)",
        error: "var(--ant-color-error)",
        ant: {
          primary: "var(--ant-color-primary)",
          "primary-bg": "var(--ant-color-primary-bg)",
          "primary-hover": "var(--ant-color-primary-hover)",
          success: "var(--ant-color-success)",
          warning: "var(--ant-color-warning)",
          error: "var(--ant-color-error)",
          "bg-container": "var(--ant-color-bg-container)",
          "bg-layout": "var(--ant-color-bg-layout)",
          "bg-elevated": "var(--ant-color-bg-elevated)",
          border: "var(--ant-color-border)",
          text: "var(--ant-color-text)",
          "text-secondary": "var(--ant-color-text-secondary)",
          "text-tertiary": "var(--ant-color-text-tertiary)",
        },
        // ── Lớp 2: Semantic cho shadcn (HSL bridge) ──
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        brand: {
          DEFAULT: "hsl(var(--brand))",
          light: "hsl(var(--brand-light))",
        },
        border: "hsl(var(--border))",
        ring: "hsl(var(--primary))",
      },
      borderRadius: {
        base: "var(--ant-border-radius)",
        lg: "var(--ant-border-radius)",
        md: "calc(var(--ant-border-radius) - 2px)",
        sm: "calc(var(--ant-border-radius) - 4px)",
      },
      fontSize: {
        // Đồng bộ Antd Typography scale
        ant: ["var(--ant-font-size)", { lineHeight: "var(--ant-line-height)" }],
      },
      fontFamily: {
        sans: ["Roboto", "var(--ant-font-family)", "sans-serif"],
      },
      spacing: {
        // Landing section rhythm (bội số 4px — Tailwind default)
        section: "5rem",    // py-section = 80px
        "section-sm": "3rem",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
```

### 3.6. `src/index.css` — tối giản

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Biến --ant-* do Antd inject. Biến --primary, --background do AntdCssBridge inject. */
/* KHÔNG định nghĩa palette màu cố định trong :root / .dark */

@layer base {
  body {
    @apply bg-ant-bg-layout text-ant-text antialiased;
    font-family: Roboto, sans-serif;
  }
}

@layer components {
  .hero-overlay {
    background: linear-gradient(to bottom, hsl(var(--foreground) / 0.7), hsl(var(--foreground) / 0.8));
  }
  .brand-gradient {
    background: linear-gradient(135deg, hsl(var(--brand)), hsl(var(--brand-light)));
  }
  .section-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--ant-color-primary), transparent);
  }
}
```

### 3.7. Gắn vào `App.tsx`

```tsx
<ThemeProvider attribute="class" defaultTheme="system" enableSystem>
  <ThemeContextProvider>
    <AppContent />  {/* Bỏ ConfigProvider lồng ở đây */}
  </ThemeContextProvider>
</ThemeProvider>
```

---

## 4. Quy tắc component (Do's & Don'ts)

### Ưu tiên 1 — Antd native + Component Token

| ✅ DO | ❌ DON'T |
|-------|----------|
| Sửa `components.Table` trong `antdTheme.ts` | `className="!bg-gray-100"` trên `<Table>` |
| `<Form>`, `<Input>`, `<Select>` cho nhập liệu | shadcn Form cho CRUD admin |
| `<Modal>`, `<Drawer>`, `<Upload>` Antd | shadcn Dialog cho workflow chính |
| `<Empty>`, `<Spin>`, `<Result>` cho trạng thái | Custom div "Không có dữ liệu" |
| `Button type="primary"` cho CTA chính trong app | shadcn Button cho form submit admin |

### Ưu tiên 2 — Tailwind layout/spacing

| ✅ DO | ❌ DON'T |
|-------|----------|
| `flex`, `grid`, `gap-4`, `p-6`, `max-w-7xl` | `gap-[13px]`, `p-[18px]` |
| `bg-ant-bg-layout`, `text-ant-text` | `bg-white`, `text-gray-900` |
| `text-primary`, `border-ant-border` | `text-[#1677ff]`, `#d9d9d9` |
| `rounded-base` (= `--ant-border-radius`) | `rounded-2xl` tùy hứng |

### Ưu tiên 3 — shadcn (hạn chế)

| ✅ DO | ❌ DON'T |
|-------|----------|
| `Sonner` / `Toaster` cho toast | Antd `message` + Sonner song song |
| shadcn khi Antd không có primitive | shadcn Button thay Antd Button trên form |
| Giữ `hsl(var(--primary))` trong component | Sửa `button.tsx` hardcode màu |

---

## 5. Quy tắc Landing Page

> Áp dụng: `HomePage`, `GuidePage`, `LoginPage`, `RegisterPage`, `PublicFamilyTreeListPage` và mọi trang **public marketing**.

### 5.1. Layout & Spacing

**Mobile-first bắt buộc.** Breakpoint theo Tailwind mặc định: `sm` 640 · `md` 768 · `lg` 1024 · `xl` 1280.

| Token class | Giá trị | Dùng cho |
|-------------|---------|----------|
| `px-4` / `md:px-6` / `lg:px-8` | 16/24/32px | Padding ngang section |
| `py-section-sm` / `md:py-section` | 48/80px | Padding dọc section |
| `max-w-7xl mx-auto` | 1280px | Container nội dung |
| `gap-4` / `md:gap-6` / `lg:gap-8` | 16/24/32px | Grid feature cards |
| `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` | — | Feature grid |

**✅ DO**

```tsx
<section className="py-section-sm md:py-section px-4 md:px-6">
  <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
```

**❌ DON'T**

```tsx
<section style={{ padding: '60px 20px' }}>
<div className="grid grid-cols-3">  {/* Không mobile-first */}
```

### 5.2. Typography

Đồng bộ **Antd Typography token** ↔ **Tailwind utility** trên Landing:

| Vai trò | Antd | Tailwind Landing | Cỡ chữ |
|---------|------|------------------|--------|
| Hero headline | `<Title level={1}>` hoặc `h1` | `text-4xl md:text-5xl lg:text-6xl font-bold leading-tight` | 36→48→60px |
| Section title | `<Title level={2}>` | `text-3xl md:text-4xl font-bold text-ant-text` | 30→36px |
| Subtitle | `<Paragraph>` | `text-lg md:text-xl text-ant-text-secondary` | 18→20px |
| Body | `<Text>` | `text-base text-ant-text-secondary leading-relaxed` | 16px |
| Caption | `<Text type="secondary">` | `text-sm text-ant-text-tertiary` | 14px |

**✅ DO**

```tsx
<h1 className="text-4xl md:text-5xl font-bold text-ant-text">{title}</h1>
<BranchesOutlined className="text-3xl text-primary" />
```

**❌ DON'T** (hiện trạng `HomePage.tsx` — phải refactor)

```tsx
<h1 className="font-display text-parchment">           {/* palette cũ */}
<BranchesOutlined style={{ color: 'hsl(36, 70%, 42%)' }} />
<Button style={{ background: 'hsl(36, 70%, 42%)' }}>   {/* bypass token */}
```

**Quy tắc font:** Dùng **một** font family — `Roboto` (đã khai báo trong seed). **Cấm** `font-display` Playfair trên Landing trừ khi được thêm vào `seedTokens.fontFamily` và approve design.

### 5.3. Màu sắc Landing

| Element | Class / Component | Ghi chú |
|---------|-------------------|---------|
| Hero CTA chính | `<Button type="primary" size="large">` | **Không** override `style.background` |
| CTA phụ | `<Button size="large">` default | Hoặc `ghost` trên nền ảnh |
| Nền section | `bg-ant-bg-layout` hoặc `bg-background` | Sau bridge |
| Card feature | `bg-ant-bg-container border border-ant-border rounded-base` | Hoặc Antd `<Card>` |
| Icon accent | `text-primary` | = `--ant-color-primary` |
| Gradient brand | `.brand-gradient` | Chỉ dùng hero/badge, tối đa 2 chỗ/page |

### 5.4. Hiệu ứng & Animation

**Không có framer-motion** → dùng CSS/Tailwind. Nếu bổ sung sau: lazy `import('framer-motion')`, chỉ Landing, không dùng admin.

| ✅ DO | Giới hạn |
|-------|----------|
| `transition-colors duration-200` | Hover button, card |
| `transition-transform duration-300 hover:-translate-y-0.5` | Feature card |
| `animate-fade-in` (tailwindcss-animate) | Section enter — **1 lần** |
| `scroll-smooth` + `scrollIntoView` | Anchor nav (`#features`) |
| `prefers-reduced-motion: reduce` → tắt animation | Bắt buộc accessibility |

| ❌ DON'T |
|----------|
| `animate-bounce` lặp vô hạn trên nhiều element |
| Parallax JS nặng trên hero |
| Animation > 500ms trên interactive element |
| Layout shift khi load (CLS) — luôn set `width/height` cho hero image |

```css
/* Thêm vào index.css */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### 5.5. Landing checklist (PR bắt buộc)

- [ ] Mobile-first responsive đã test 375px / 768px / 1280px
- [ ] Không inline `style` màu — chỉ `style` layout (height hero) nếu cần
- [ ] CTA dùng Antd Button `type="primary"` / default / `ghost`
- [ ] Typography theo bảng 5.2
- [ ] Hero image có `alt`, `object-cover`, kích thước cố định
- [ ] Section có `id` cho anchor (`#features`, `#about`)
- [ ] Lighthouse Performance ≥ 80 trên Landing (không block render bởi animation)

---

## 6. Quy tắc UX/UI toàn hệ thống

### 6.1. Phân cấp nhận thức (Visual Hierarchy)

**Một màn hình = một hành động chính.**

| Loại nút | Antd | Màu | Vị trí |
|----------|------|-----|--------|
| **Primary CTA** | `<Button type="primary">` | `--ant-color-primary` | Phải / trên cùng action bar |
| **Secondary** | `<Button>` default | border + nền container | Trái primary |
| **Tertiary / Hủy** | `<Button type="text">` hoặc `link` | text secondary | Cùng hàng, sau secondary |
| **Destructive** | `<Button danger>` | `--ant-color-error` | Tách biệt, cần Popconfirm |

**✅ DO**

```tsx
<Space>
  <Button type="primary" onClick={onSave}>Lưu</Button>
  <Button onClick={onCancel}>Hủy</Button>
</Space>
```

**❌ DON'T**

```tsx
<Button type="primary">Lưu</Button>
<Button type="primary">Xuất file</Button>  {/* 2 primary cùng màn */}
<Button danger onClick={onDelete}>Xóa</Button>  {/* Không confirm */}
```

**Mật độ màu:** Primary chiếm ≤ 10% diện tích màn hình. Nền dùng `colorBgLayout`, card dùng `colorBgContainer`.

### 6.2. Đặt tính năng (Feature Placement)

```
┌─────────────────────────────────────────────────────────────┐
│  PUBLIC / LANDING          │  Tailwind layout + Antd Button │
│  (marketing, CTA)        │  shadcn toast nếu cần          │
├──────────────────────────┼─────────────────────────────────┤
│  USER workspace          │  Antd Form/Table/Card chính     │
│  (dashboard, lists)      │  Tailwind grid wrapper          │
├──────────────────────────┼─────────────────────────────────┤
│  ADMIN / CRUD            │  100% Antd native              │
│  (table, filter, crawl)  │  Không shadcn table/form        │
└─────────────────────────────────────────────────────────────┘
```

| Loại tính năng | Bắt buộc dùng | Lý do |
|----------------|---------------|-------|
| Table + sort + filter + pagination | Antd `<Table>` | UX nhập liệu, accessibility |
| Form nhiều field + validation | Antd `<Form>` + rules | Consistent error display |
| Dashboard thống kê | Antd `<Statistic>` + `<Card>` | Token đồng bộ |
| Modal xác nhận xóa | Antd `<Popconfirm>` / `<Modal>` | Focus trap chuẩn |
| Toast feedback | shadcn **Sonner** (đã có) | Nhẹ, không block UI |
| Landing CTA / hero | Antd `<Button>` + Tailwind layout | Brand + performance |
| Theme toggle | Custom + token class | Đã có `ThemeToggle` |
| Drawer filter phức tạp | Antd `<Drawer>` | Mobile admin |

**❌ DON'T:** Table HTML + Tailwind cho admin. Form shadcn + Antd Input lẫn lộn field trong cùng form.

### 6.3. Trạng thái không gian (Contextual States)

**Người dùng không bao giờ thấy màn hình trống im lặng.**

| Trạng thái | Component | Pattern bắt buộc |
|------------|-----------|------------------|
| **Loading** lần đầu | `<Spin>` hoặc Skeleton Antd | Bọc toàn section, có `tip` mô tả |
| **Loading** inline | `<Button loading>` | Trên chính nút trigger |
| **Empty** | `<Empty description="…">` | Kèm action: "Tạo mới", "Upload" |
| **Error** fetch | `<Alert type="error" showIcon>` | Message rõ + nút "Thử lại" |
| **Error** form field | Antd Form rule | Không `alert()` browser |
| **Success** action | Sonner toast | 3–5 giây, không Modal |
| **Permission** | `<Result status="403">` | Route `/403` |

**✅ DO**

```tsx
if (loading) return <Spin tip="Đang tải danh sách gia phả…" />;
if (error) return <Alert type="error" message={error} action={<Button onClick={retry}>Thử lại</Button>} />;
if (!items.length) return <Empty description="Chưa có gia phả"><Button type="primary" onClick={onCreate}>Tạo mới</Button></Empty>;
```

**❌ DON'T**

```tsx
if (loading) return null;
if (!items.length) return <p>Trống</p>;
catch { console.error(e); }
```

### 6.4. Navigation & IA (Information Architecture)

| Vai trò | Menu chính (ngắn) | Ghi chú |
|---------|-------------------|---------|
| Guest | Trang chủ · Gia phả mẫu · Hướng dẫn · Đăng nhập | Max **7** mục |
| User | Tổng quan · Đọc tài liệu · Tài liệu · Gia phả · Tài khoản | Sidebar |
| Admin | Tổng quan · Gia phả · Lịch sử · Thành viên · Developer | CRUD tách Developer |

**Quy tắc IA:** CTA đăng nhập luôn visible trên public header. Tính năng hệ thống (crawl, OCR config, storage) → **Developer**, không nhét vào menu nghiệp vụ.

### 6.5. Quy tắc đặt tên Menu, Header & Button

> **Nguyên tắc:** Đơn giản · ngắn gọn · dễ hiểu — người dùng đọc lướt 1 giây là biết chức năng.

#### 6.5.1. Giới hạn độ dài

| Loại | Giới hạn | Ví dụ ✅ | Ví dụ ❌ |
|------|----------|----------|----------|
| **Menu** (sidebar/header nav) | ≤ **3 từ**, ≤ **24** ký tự | `Gia phả`, `Lịch sử`, `Hán-Nôm` | `Quản lý gia phả`, `Cấu hình API Kim Hán Nôm` |
| **Header trang** (title H4) | ≤ **4 từ**, ưu tiên **trùng menu** | `Tổng quan`, `Đồng bộ VGP` | `Dashboard quản trị`, `Crawl dữ liệu và đồng bộ database` |
| **Breadcrumb** (mục cuối) | = header hoặc ngắn hơn | `Gia phả` → `Chi tiết` | `Quản lý gia phả` → `Chi tiết cây gia phả số 101` |
| **Button label** | **1–2 từ**, ≤ **20** ký tự | `Lưu`, `Tạo mới`, `Thử lại` | `Lưu thay đổi`, `Tải tài liệu về máy` |
| **Subtitle / mô tả** | Câu đầy đủ, **không** đặt trong menu/button | Dưới `Typography.Title` | Nhét mô tả dài vào `label` menu |

#### 6.5.2. Cách chọn từ

| # | Quy tắc |
|---|---------|
| NAME-1 | **Menu = danh từ** hoặc cụm danh từ: `Tài liệu`, `Thành viên` — không dùng động từ |
| NAME-2 | **Button = động từ** (+ tân ngữ nếu cần): `Tải lên`, `Xóa`, `Chạy` |
| NAME-3 | **Bỏ tiền tố thừa:** `Quản lý`, `Xem`, `Mở`, `Danh sách` — ngữ cảnh menu đã đủ |
| NAME-4 | **Thuật ngữ kỹ thuật** chỉ khi không thay được: `API`, `JSON`, `OCR`, `VGP` — không `MinIO/S3`, `Crawl VietnamGiaPha` |
| NAME-5 | **Một khái niệm = một tên** xuyên suốt: menu `Gia phả` → header `Gia phả` → button `Tạo mới` (không đổi thành `Cây gia phả` / `Tạo cây`) |
| NAME-6 | **i18n SSOT:** mọi label qua `vi.json` / `en.json`; `defaultValue` trong code chỉ là fallback ngắn |

#### 6.5.3. Bảng chuẩn dự án (tham chiếu)

| Vùng | Menu / Header | Button chính | Button phụ |
|------|---------------|--------------|------------|
| Public | Trang chủ · Gia phả mẫu · Hướng dẫn | Đăng nhập · Đăng ký | — |
| User | Tổng quan · Đọc tài liệu · Tài liệu · Gia phả | Tải lên · Tạo mới | Tải lại · Quay lại |
| Admin | Gia phả · Lịch sử · Thành viên | Tạo mới · Lưu · Xóa | Chi tiết · Sửa |
| Developer | Hán-Nôm · Lưu trữ · Đồng bộ VGP · Nhật ký · API Docs | Chạy · Lưu | Đặt lại · Thử lại |

#### 6.5.4. Do's & Don'ts

**✅ DO**

```tsx
// Menu
label: t("admin.menuFamilyTrees")  // "Gia phả"

// Header
<Typography.Title level={4}>Gia phả</Typography.Title>

// Button
<Button type="primary">Lưu</Button>
<Button>Tải lại</Button>
```

**❌ DON'T**

```tsx
label: "Quản lý danh sách cây gia phả hệ thống"
<Button type="primary">Lưu thay đổi vào cơ sở dữ liệu</Button>
<Button>Crawl dữ liệu và đồng bộ database</Button>
```

### 6.6. UX checklist (PR bắt buộc)

- [ ] Mỗi async action có loading state
- [ ] Mỗi list có empty state + hướng dẫn bước tiếp
- [ ] Mỗi error có message tiếng Việt + recovery action
- [ ] Chỉ một `type="primary"` Button nổi bật nhất mỗi viewport
- [ ] Form submit disabled khi đang loading
- [ ] Destructive action có Popconfirm
- [ ] Menu/header/button tuân thủ **§6.5** (độ dài, không tiền tố thừa)

---

## 7. Migration checklist

**Phase A — Theme (tuần 1)**

- [ ] Tạo `src/theme/` (seedTokens, antdTheme, syncTokensToCss, ThemeContextProvider)
- [ ] Bật `cssVar: { prefix: 'ant' }`
- [ ] Cập nhật `tailwind.config.ts` map `var(--ant-*)`
- [ ] Tối giản `index.css` — xóa palette `:root`/`.dark`
- [ ] Thay `ConfigProvider` trong App → `ThemeContextProvider`

**Phase B — Refactor màu (tuần 2)**

- [ ] `text-[#1677ff]` → `text-primary`
- [ ] `HomePage.tsx` — xóa toàn bộ inline `hsl(36,…)` trên Button/icon
- [ ] `border-gold` / `text-gold` → `text-primary` / `border-primary`
- [ ] `AdminLayout` `!bg-[#1677ff]` → `bg-primary`

**Phase C — Landing & UX (tuần 3)**

- [ ] Chuẩn hóa spacing Landing theo §5.1
- [ ] Thêm empty/loading/error cho pages còn thiếu
- [ ] Review CTA hierarchy toàn app

---

## 8. Anti-patterns

```tsx
// ❌ Hai primary trên Landing
<Button type="primary">Xem mẫu</Button>
<Button type="primary">Đăng ký</Button>

// ❌ Landing bypass Antd token
<Button type="primary" style={{ background: 'hsl(36,70%,42%)' }}>

// ❌ Admin table HTML
<table className="w-full border">…</table>

// ❌ Loading im lặng
{loading ? <Spin /> : null}  // Không có tip, không skeleton

// ❌ Palette song song
// index.css: --primary: 36 70% 42%
// antdTheme: colorPrimary: "#1677ff"
```

---

## 9. Phụ lục

### A. Map token nhanh

| Antd Token | CSS Var | Tailwind |
|------------|---------|----------|
| `colorPrimary` | `--ant-color-primary` | `text-primary`, `bg-primary` |
| `colorError` | `--ant-color-error` | `text-error` |
| `colorBgLayout` | `--ant-color-bg-layout` | `bg-ant-bg-layout` |
| `colorBgContainer` | `--ant-color-bg-container` | `bg-ant-bg-container` |
| `colorText` | `--ant-color-text` | `text-ant-text` |
| `colorTextSecondary` | `--ant-color-text-secondary` | `text-ant-text-secondary` |
| `colorBorder` | `--ant-color-border` | `border-ant-border` |
| `borderRadius` | `--ant-border-radius` | `rounded-base` |

### B. Map shadcn ← Antd (bridge)

| shadcn var | Nguồn Antd |
|------------|------------|
| `--primary` | `colorPrimary` |
| `--background` | `colorBgLayout` |
| `--foreground` | `colorText` |
| `--card` | `colorBgContainer` |
| `--border` | `colorBorder` |
| `--destructive` | `colorError` |

### C. Cấu trúc file

```
family-saga-io/src/theme/
├── seedTokens.ts
├── antdTheme.ts
├── colorUtils.ts
├── syncTokensToCss.ts
└── ThemeContextProvider.tsx
```

### D. Tham chiếu codebase hiện tại

| File cần refactor | Ưu tiên |
|-------------------|---------|
| `HomePage.tsx` | **Cao** — inline HSL Landing |
| `index.css` | **Cao** — palette độc lập |
| `DashboardPage.tsx` | Trung bình — hex icon |
| `FamilyTreeManagerPage.tsx` | Trung bình |
| `src/lib/antdTheme.ts` | **Cao** — migrate → `src/theme/` |

---

*Phiên bản: 2.1 · 07/2026 · Bổ sung §6.5 Naming Rules (menu, header, button)*
