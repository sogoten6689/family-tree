import io
import json
import tarfile
from pathlib import Path

from tools import dong_bo_khung as d


def test_only_new_complete_pages_are_sent_and_tar_has_no_mac_junk(tmp_path: Path) -> None:
    khung = tmp_path / "tq-1" / "khung"
    khung.mkdir(parents=True)
    (khung / "001.json").write_text(json.dumps({"chu": []}), encoding="utf-8")
    (khung / "002.json").write_text('{"chu": [', encoding="utf-8")  # đang ghi dở
    (khung / "._001.json").write_bytes(b"\x00rac")
    seen: dict = {}

    pages = d.changed_pages(tmp_path / "tq-1", seen)
    assert [p.name for p in pages] == ["001.json"]

    with tarfile.open(fileobj=io.BytesIO(d.pack([(p, f"khung/{p.name}") for p in pages]))) as tar:
        assert tar.getnames() == ["khung/001.json"]
        assert json.loads(tar.extractfile("khung/001.json").read()) == {"chu": []}

    st = pages[0].stat()
    seen[pages[0]] = (st.st_mtime_ns, st.st_size)
    (khung / "002.json").write_text(json.dumps({"chu": [1]}), encoding="utf-8")
    assert [p.name for p in d.changed_pages(tmp_path / "tq-1", seen)] == ["002.json"]


def test_sync_uploads_each_book_to_its_server_folder(tmp_path: Path, monkeypatch) -> None:
    khung = tmp_path / "tq-2" / "khung"
    khung.mkdir(parents=True)
    (khung / "005.json").write_text("{}", encoding="utf-8")
    calls = []
    monkeypatch.setattr(d, "upload", lambda blob, target, host, container: calls.append((target, host, container)))
    args = d.argparse.Namespace(remote="/app/data/doi_chieu", host="h", container="c")
    seen: dict = {}
    assert d.sync_once([tmp_path / "tq-2"], "chua-giao", seen, args) == 1
    assert calls == [("/app/data/doi_chieu/chua-giao/tq-2", "h", "c")]
    assert d.sync_once([tmp_path / "tq-2"], "chua-giao", seen, args) == 0
