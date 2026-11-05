/** Đặt chữ người soát đang sửa vào vị trí chữ trên ảnh. Vị trí lấy từ bản máy, nên phải dóng hai chuỗi. */
import type { SoatRow } from "@/lib/doiChieuApi";

/** Khóa giả của cột bản tâm: không phải dòng soát nên không có số dòng, bấm vào thì tới ô sửa bản tâm. */
export const BAN_TAM_KEY = -1;

const HAN_RE = /[㐀-䶿一-鿿豈-﫿\u{20000}-\u{3ffff}]/u;

export interface DraftChar {
  ch: string;
  rowKey: number;
  trang: string;
}

export interface Placed {
  ch: string;
  rowKey: number;
  /** Khác chữ bản máy ở vị trí này, tức là người soát đã sửa. */
  changed: boolean;
}

/** Chữ Hán của các dòng đang dùng; dấu câu do người soát thêm không có trên ảnh nên bỏ. */
export const draftChars = (rows: (SoatRow & { key: number })[]): DraftChar[] =>
  rows
    .filter((r) => !r.bo)
    .flatMap((r) => Array.from(r.han).filter((ch) => HAN_RE.test(ch)).map((ch) => ({ ch, rowKey: r.key, trang: r.trang })));

/**
 * Dóng chữ bản máy (có vị trí) với chữ đang sửa bằng dãy con chung dài nhất; phần chênh giữa hai chữ khớp
 * coi là chữ bị thay, ghép lần lượt. Hai đầu chỉ lấy chữ thuộc đúng trang này, vì `draft` có cả trang kề
 * (để theo được câu đã ghép qua trang) và chữ trang kề không nằm trên ảnh trang này.
 */
export const alignToAnchors = (anchors: string[], draft: DraftChar[], page: string): (Placed | null)[] => {
  const n = anchors.length;
  const m = draft.length;
  const width = m + 1;
  const dp = new Uint16Array((n + 1) * width);
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i * width + j] =
        anchors[i] === draft[j].ch
          ? dp[(i + 1) * width + j + 1] + 1
          : Math.max(dp[(i + 1) * width + j], dp[i * width + j + 1]);
    }
  }

  const out: (Placed | null)[] = new Array(n).fill(null);
  const put = (a: number, d: number) => {
    out[a] = { ch: draft[d].ch, rowKey: draft[d].rowKey, changed: draft[d].ch !== anchors[a] };
  };
  const pairs: [number, number][] = [];
  for (let i = 0, j = 0; i < n && j < m; ) {
    if (anchors[i] === draft[j].ch && dp[i * width + j] === dp[(i + 1) * width + j + 1] + 1) {
      pairs.push([i, j]);
      i++;
      j++;
    } else if (dp[(i + 1) * width + j] >= dp[i * width + j + 1]) {
      i++;
    } else {
      j++;
    }
  }
  pairs.forEach(([a, d]) => put(a, d));

  let [prevA, prevD] = [-1, -1];
  for (const [a, d] of [...pairs, [n, m] as [number, number]]) {
    const gapA = a - prevA - 1;
    const gapD = d - prevD - 1;
    const isHead = prevA < 0;
    const isTail = a === n;
    for (let k = 0; k < Math.min(gapA, gapD); k++) {
      // Đầu trang dóng sát về chữ khớp đầu tiên, các chỗ còn lại đi từ trái sang.
      const [ax, dx] = isHead && !isTail ? [a - 1 - k, d - 1 - k] : [prevA + 1 + k, prevD + 1 + k];
      if (!(isHead || isTail) || draft[dx].trang === page) put(ax, dx);
    }
    [prevA, prevD] = [a, d];
  }
  return out;
};

/** Đặt chữ cho mọi ô của trang: ô chữ chính trước, ô bản tâm sau. */
export const placeOnPage = (body: string[], gutter: string[], draft: DraftChar[], banTam: string, page: string): (Placed | null)[] => {
  const gutterDraft = draftChars([{ key: BAN_TAM_KEY, trang: page, han: banTam, viet: "", bo: false }]);
  return [...alignToAnchors(body, draft, page), ...alignToAnchors(gutter, gutterDraft, page)];
};

/** Dòng của từng ô; null là chưa gán được. Ô bản tâm luôn thuộc bản tâm, kể cả khi chữ chưa khớp. */
export const rowKeysOf = (placed: (Placed | null)[], bodyCount: number): (number | null)[] =>
  placed.map((p, i) => (i >= bodyCount ? BAN_TAM_KEY : (p?.rowKey ?? null)));
