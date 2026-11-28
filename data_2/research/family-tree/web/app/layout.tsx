import type { Metadata } from "next";
import Link from "next/link";
import AutoRefresh from "@/components/AutoRefresh";
import "./globals.css";

export const metadata: Metadata = { title: "Soát dữ liệu gia phả" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <header className="top">
          <b>
            <Link href="/">Soát dữ liệu gia phả</Link>
          </b>
          <span className="muted small">Thêm hoặc sinh lại file .jsonl là trang tự cập nhật</span>
          <span style={{ flex: 1 }} />
          <AutoRefresh />
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
