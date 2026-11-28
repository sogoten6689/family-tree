"use client";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

/** Hỏi /api/version mỗi 3 giây; dữ liệu trên đĩa đổi thì làm mới trang (không mất bản đang sửa). */
export default function AutoRefresh() {
  const router = useRouter();
  const last = useRef<string | null>(null);
  const [at, setAt] = useState<string>("");
  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const r = await fetch("/api/version", { cache: "no-store" });
        const { v } = await r.json();
        if (last.current && v !== last.current) {
          router.refresh();
          setAt(new Date().toLocaleTimeString("vi-VN"));
        }
        last.current = v;
      } catch {}
      if (alive) setTimeout(tick, 3000);
    };
    tick();
    return () => {
      alive = false;
    };
  }, [router]);
  return <span className="muted small">{at ? `Cập nhật lúc ${at}` : "Đang theo dõi thay đổi"}</span>;
}
