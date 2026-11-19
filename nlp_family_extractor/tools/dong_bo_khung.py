"""Đẩy khung chữ lên máy chủ theo từng trang, để trang /nghien-cuu/tien-do và trang xem ảnh thấy ngay.

Chạy song song với tools/tao_khung_doi_chieu.py: cứ vài giây xem các thư mục <cuon>/khung/ ở máy, trang nào mới
hoặc vừa ghi lại thì gói (tar, không kèm tệp rác ._* của macOS) và giải nén thẳng vào thư mục dữ liệu đối chiếu
trong container backend qua ssh. Trang đang ghi dở (JSON chưa đọc được) được để lần sau.

    python tools/dong_bo_khung.py --sv chua-giao data/05_ops/khung_run/tq-950 data/05_ops/khung_run/tq-693 --theo-doi
    python tools/dong_bo_khung.py --trang-thai tien_do.json    # chỉ đẩy ghi chú Xong / Đang làm / Chờ quyết
"""
from __future__ import annotations

import argparse
import io
import json
import shlex
import subprocess
import sys
import tarfile
import time
from pathlib import Path

DEFAULT_HOST = "vps-caohoc"
DEFAULT_CONTAINER = "family-tree-backend"
DEFAULT_REMOTE = "/app/data/doi_chieu"


def changed_pages(book: Path, seen: dict[Path, tuple[int, int]]) -> list[Path]:
    """Trang khung mới hoặc đã đổi kể từ lần đẩy trước, chỉ lấy tệp JSON đọc được trọn vẹn."""
    khung = book / "khung"
    if not khung.is_dir():
        return []
    out = []
    for path in sorted(khung.glob("*.json")):
        if path.name.startswith("."):
            continue
        st = path.stat()
        if seen.get(path) == (st.st_mtime_ns, st.st_size):
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.append(path)
    return out


def pack(files: list[tuple[Path, str]]) -> bytes:
    """Gói tar: mỗi tệp đặt ở đường dẫn tương đối arcname, giữ mtime để web biết trang làm lúc nào."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for path, arcname in files:
            info = tarfile.TarInfo(arcname)
            data = path.read_bytes()
            info.size = len(data)
            info.mtime = int(path.stat().st_mtime)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def upload(blob: bytes, target_dir: str, host: str, container: str) -> None:
    remote = f"docker exec -i {shlex.quote(container)} tar xf - -C {shlex.quote(target_dir)}"
    subprocess.run(["ssh", host, remote], input=blob, check=True)


def sync_once(books: list[Path], student: str, seen: dict, args: argparse.Namespace) -> int:
    sent = 0
    for book in books:
        pages = changed_pages(book, seen)
        if not pages:
            continue
        blob = pack([(p, f"khung/{p.name}") for p in pages])
        upload(blob, f"{args.remote}/{student}/{book.name}", args.host, args.container)
        for p in pages:
            st = p.stat()
            seen[p] = (st.st_mtime_ns, st.st_size)
        sent += len(pages)
        print(f"{time.strftime('%H:%M:%S')} {book.name}: đẩy {len(pages)} trang", flush=True)
    return sent


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("books", nargs="*", type=Path, help="thư mục cuốn ở máy (có thư mục con khung/)")
    ap.add_argument("--sv", default="chua-giao", help="thư mục sinh viên/nhóm trên máy chủ")
    ap.add_argument("--theo-doi", action="store_true", help="chạy mãi, đẩy trang mới mỗi --moi giây (Ctrl+C để dừng)")
    ap.add_argument("--moi", type=float, default=5.0, help="số giây giữa hai lần xem (mặc định 5)")
    ap.add_argument("--trang-thai", type=Path, help="tệp tien_do.json (Xong / Đang làm / Chờ quyết) để đẩy lên")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--container", default=DEFAULT_CONTAINER)
    ap.add_argument("--remote", default=DEFAULT_REMOTE)
    args = ap.parse_args(argv)

    if args.trang_thai:
        json.loads(args.trang_thai.read_text(encoding="utf-8"))  # hỏng thì dừng ở máy, không đẩy tệp hỏng lên
        upload(pack([(args.trang_thai, "tien_do.json")]), args.remote, args.host, args.container)
        print("đã đẩy ghi chú tiến độ", flush=True)

    seen: dict[Path, tuple[int, int]] = {}
    sync_once(args.books, args.sv, seen, args)
    while args.theo_doi:
        time.sleep(args.moi)
        try:
            sync_once(args.books, args.sv, seen, args)
        except subprocess.CalledProcessError as exc:  # mạng chập chờn: thử lại ở vòng sau
            print(f"lỗi đẩy, thử lại sau: {exc}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
