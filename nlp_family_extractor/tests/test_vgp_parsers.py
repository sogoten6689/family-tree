from __future__ import annotations

from pathlib import Path

from app.vgp.parsers import (
    detect_pha_he_mode,
    parse_giapha,
    parse_pha_he,
    parse_pha_ky_text,
)


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "data" / "vietnamgiapha" / "raw_html"


def test_parse_legacy_pha_he_122():
    html = (FIXTURE_DIR / "122.html").read_text(encoding="utf-8")
    assert detect_pha_he_mode(html) == "legacy_js"
    nodes, relationships, mode = parse_pha_he(html, tree_id=122)
    assert mode == "legacy_js"
    assert len(nodes) >= 70
    assert len(relationships) >= 50
    assert nodes[0]["node_id"] == 1


def test_parse_giapha_modern_sample():
    html = """
    <html><body>
    <h1>HUỲNH Ở Tiên Phước</h1>
    <section><h2>Ở tại</h2><p>Thạnh Yên thôn 3</p></section>
    <section>
      <h2>Tổng quan gia phả</h2>
      <div class="stats">
        <div class="stat"><strong>9</strong> Số đời từ thủy tổ tới con cháu</div>
        <div class="stat"><strong>136</strong> Gia đình trong gia phả</div>
        <div class="stat"><strong>195</strong> Số người trong gia phả</div>
      </div>
    </section>
    <section><h2>Thông tin người quản lý gia phả</h2><p><strong>Người làm:</strong> Huỳnh Ngọc Trình</p></section>
    </body></html>
    """
    metadata = parse_giapha(html, tree_id=11108)
    assert metadata["lineage_name"] == "HUỲNH Ở Tiên Phước"
    assert metadata["location"] == "Thạnh Yên thôn 3"
    assert metadata["generation_count"] == 9
    assert metadata["family_count"] == 136
    assert metadata["people_count"] == 195
    assert metadata["manager_name"] == "Huỳnh Ngọc Trình"


def test_parse_modern_gt_pha_he():
    html = """
    <div class="tree-view"><div class="gt"><b>1.1</b> <a href="/XemChiTietTungNguoi/11108/1/giapha.html">Huỳnh Kim Quy</a> + <a href="/XemChiTietTungNguoi/11108/2/giapha.html">Vợ Chưa sưu tầm</a>
    &nbsp;&nbsp;&nbsp;&nbsp;<b>2.2</b> <a href="/XemChiTietTungNguoi/11108/3/giapha.html">Huỳnh Kim Quyền</a></div></div>
    """
    nodes, relationships, mode = parse_pha_he(html, tree_id=11108)
    assert mode == "modern_gt"
    assert len(nodes) == 3
    assert nodes[0]["node_id"] == 1
    assert nodes[1]["node_id"] == 2
    assert nodes[2]["node_id"] == 3
    assert nodes[0]["generation"] == 1
    assert len(relationships) == 1


def test_parse_pha_ky_text():
    html = """
    <main>
      <section class="section">
        <h2>Phả ký gia sử</h2>
        <div class="legacy-content">
          <div>TỘC HUỲNH TIÊN PHƯỚC QUẢNG NAM</div>
          <div>Theo dòng lịch sử từ thế kỷ XIV.</div>
        </div>
      </section>
    </main>
    """
    text = parse_pha_ky_text(html)
    assert "TỘC HUỲNH TIÊN PHƯỚC" in text
    assert "theo dòng lịch sử" in text.lower()
