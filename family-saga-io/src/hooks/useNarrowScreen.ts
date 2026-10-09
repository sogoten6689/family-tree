import { useEffect, useState } from "react";

/** Dưới breakpoint `lg` của antd (992px): điện thoại và máy tính bảng dọc. */
export const NARROW_QUERY = "(max-width: 991.98px)";

/** true khi màn hình hẹp: menu chuyển thành ngăn kéo (Drawer) thay vì thanh bên cố định. */
export function useNarrowScreen(): boolean {
  const read = () => typeof window !== "undefined" && !!window.matchMedia?.(NARROW_QUERY).matches;
  const [mobile, setMobile] = useState(read);
  useEffect(() => {
    const query = window.matchMedia?.(NARROW_QUERY);
    if (!query) return;
    const onChange = () => setMobile(query.matches);
    onChange();
    query.addEventListener?.("change", onChange);
    return () => query.removeEventListener?.("change", onChange);
  }, []);
  return mobile;
}
