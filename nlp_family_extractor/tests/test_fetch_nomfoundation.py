from tools.fetch_nomfoundation import (
    build_page_image_url,
    extract_catalog_slug,
    extract_media_image_template,
    parse_volume_metadata,
    resolve_page_image_urls,
)

VOLUME_1255_HTML = """
<html><head><title>朱族譜記 | Chu tộc gia phả</title></head><body>
<h1>[朱族譜記]</h1><h1>[Chu tộc gia phả]</h1>
<h2>TNVNPF-001</h2><h2>TN.146</h2>
<dt>Pages</dt><dd>6</dd>
<img src="/site_media/nom/tnvnpf/tnvnpf-001/jpeg/tnvnpf-001-001.jpg" />
</body></html>
"""

VOLUME_208_HTML = """
<html><head><title>東稠段族譜 | Đông Trù Đoàn tộc phả</title></head><body>
<h1>東稠段族譜</h1><h1>Đông Trù Đoàn tộc phả</h1>
<h2>NLVNPF-0155</h2><h2>R.951</h2>
<dt>Pages</dt><dd>79</dd>
<img src="/site_media/nom/nlvnpf-0155/jpeg/nlvnpf-0155-001.jpg" />
</body></html>
"""


def test_parse_volume_metadata_tnvnpf():
    meta = parse_volume_metadata(VOLUME_1255_HTML, collection_id=2, volume_id=1255)
    assert meta["title_han"] == "朱族譜記"
    assert meta["title_vn"] == "Chu tộc gia phả"
    assert meta["catalog_code"] == "TNVNPF-001"
    assert meta["local_code"] == "TN.146"
    assert meta["catalog_slug"] == "tnvnpf-001"
    assert meta["media_rel"] == "tnvnpf/tnvnpf-001"
    assert meta["file_prefix"] == "tnvnpf-001"
    assert meta["page_count"] == 6


def test_parse_volume_metadata_nlvnpf():
    meta = parse_volume_metadata(VOLUME_208_HTML, collection_id=2, volume_id=208)
    assert meta["title_vn"] == "Đông Trù Đoàn tộc phả"
    assert meta["catalog_code"] == "NLVNPF-0155"
    assert meta["catalog_slug"] == "nlvnpf-0155"
    assert meta["media_rel"] == "nlvnpf-0155"
    assert meta["file_prefix"] == "nlvnpf-0155"
    assert meta["page_count"] == 79


def test_build_page_image_urls():
    meta = parse_volume_metadata(VOLUME_1255_HTML, collection_id=2, volume_id=1255)
    urls = resolve_page_image_urls(meta, image_variant="large", max_pages=6)
    assert len(urls) == 6
    assert urls[0] == build_page_image_url(
        media_rel="tnvnpf/tnvnpf-001",
        file_prefix="tnvnpf-001",
        page=1,
        variant="large",
    )
    assert urls[-1].endswith("tnvnpf-001-006.jpg")


def test_resolve_page_image_urls_page_range():
    meta = parse_volume_metadata(VOLUME_208_HTML, collection_id=2, volume_id=208)
    urls = resolve_page_image_urls(meta, image_variant="large", max_pages=79, page_start=11, page_end=15)
    assert len(urls) == 5
    assert "0155-011.jpg" in urls[0]
    assert "0155-015.jpg" in urls[-1]


def test_extract_catalog_slug_from_heading_only():
    html = "<html><h2>NLVNPF-0155</h2></html>"
    assert extract_catalog_slug(html) == "nlvnpf-0155"


def test_extract_media_image_template():
    media_rel, file_prefix = extract_media_image_template(VOLUME_1255_HTML)
    assert media_rel == "tnvnpf/tnvnpf-001"
    assert file_prefix == "tnvnpf-001"
