import pytest

from label_studio_pipeline.export_cv_folds import plan_folds


def test_every_tree_is_test_exactly_once_and_no_leakage():
    ids = [str(i) for i in range(25)]
    folds = plan_folds(ids, 5, 42)
    tests = [t for f in folds for t in f["test"]]
    assert sorted(tests) == sorted(ids)
    for f in folds:
        assert not (set(f["train"]) & set(f["test"])) and not (set(f["train"]) & set(f["dev"])) and not (set(f["dev"]) & set(f["test"]))
        assert set(f["train"]) | set(f["dev"]) | set(f["test"]) == set(ids)


def test_deterministic_and_too_few():
    ids = [str(i) for i in range(25)]
    assert plan_folds(ids, 5, 1) == plan_folds(ids, 5, 1)
    with pytest.raises(ValueError):
        plan_folds(["a", "b", "c"], 5, 1)
