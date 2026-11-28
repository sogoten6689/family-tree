"use client";
import { useState } from "react";

export default function ExportButton({ id }: { id: string }) {
  const [msg, setMsg] = useState("");
  return (
    <span>
      <button
        type="button"
        onClick={async () => {
          setMsg("Đang xuất…");
          const r = await fetch("/api/export", { method: "POST", body: JSON.stringify({ id }) });
          const j = await r.json();
          setMsg(j.error ? j.error : `Đã ghi ${j.count} mẫu (${j.edited} đã sửa) → ${j.path}`);
        }}
      >
        Xuất bản đã soát (.reviewed.jsonl)
      </button>
      {msg && <span className="muted small"> {msg}</span>}
    </span>
  );
}
