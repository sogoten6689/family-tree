from label_studio_pipeline import train_re as tr


def row(tree, h, t, label):
    return {"tree": tree, "head": h, "tail": t, "label": label}


def test_relation_prf_and_spouse_symmetry():
    rows = [row("1", 0, 1, "FATHER_OF"), row("1", 1, 0, "NONE"), row("1", 0, 2, "SPOUSE"), row("1", 2, 0, "SPOUSE")]
    # dự đoán đúng cha-con, nhưng SPOUSE chỉ đoán một chiều → vẫn tính khớp (không phân biệt chiều)
    r = tr.relation_prf(rows, ["FATHER_OF", "NONE", "NONE", "SPOUSE"])
    assert r["tp"] == 2 and r["fp"] == 0 and r["f1"] == 1.0
    # đảo chiều cha-con = sai
    r2 = tr.relation_prf(rows, ["NONE", "FATHER_OF", "NONE", "NONE"])
    assert r2["tp"] == 0 and r2["fp"] == 1


def test_end_to_end_recall_counts_out_of_window():
    rows = [row("1", 0, 1, "FATHER_OF")]
    r = tr.relation_prf(rows, ["FATHER_OF"], out_of_window_gold=3)
    assert r["recall_in_window"] == 1.0 and r["recall_end_to_end"] == 0.25


def test_bootstrap_ci_is_ordered():
    rows = [row(str(i % 5), i, i + 1, "FATHER_OF") for i in range(10)]
    lo, hi = tr.bootstrap_f1_ci(rows, ["FATHER_OF"] * 10, 0, n=100)
    assert lo <= hi <= 1.0
