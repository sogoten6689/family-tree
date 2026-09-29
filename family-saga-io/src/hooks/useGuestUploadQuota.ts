import { useCallback, useState } from "react";

/** Đếm số lượt phân tích ẩn danh trong 1 session — tạm chỉ client-side
 * (sessionStorage), dễ vượt qua bằng cách xoá cache, nhưng đủ để tạo hành vi
 * "gợi ý đăng nhập" thay vì chặn cứng. Rate-limit thật ở backend là việc sau
 * (docs/product/REQUIREMENTS.md R7.1.3), không thuộc phạm vi lần này. */
const STORAGE_KEY = "guest_analyze_quota";
const DEFAULT_LIMIT = 5;

function readCount(): number {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    const parsed = raw ? parseInt(raw, 10) : 0;
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  } catch {
    return 0;
  }
}

export function useGuestUploadQuota(limit: number = DEFAULT_LIMIT) {
  const [used, setUsed] = useState<number>(() => readCount());

  const consume = useCallback(() => {
    const next = readCount() + 1;
    try {
      sessionStorage.setItem(STORAGE_KEY, String(next));
    } catch {
      // sessionStorage không khả dụng (vd. private mode) — vẫn cập nhật
      // state trong bộ nhớ để UI hoạt động đúng trong phiên hiện tại.
    }
    setUsed(next);
    return next;
  }, []);

  const remaining = Math.max(0, limit - used);

  return { remaining, exhausted: remaining <= 0, consume, limit };
}
