"""ml_algorithms.py: the classic-ML algorithm registry (pure data + lookups)."""

import pytest

from app.services import ml_algorithms


def test_list_algorithms_returns_everything_when_no_filter():
    result = ml_algorithms.list_algorithms()
    ids = {a["id"] for a in result}
    assert ids == {
        "logistic_regression",
        "random_forest_classifier",
        "linear_regression",
        "random_forest_regressor",
    }


def test_list_algorithms_filters_by_task_type():
    classification = ml_algorithms.list_algorithms("tabular_classification")
    ids = {a["id"] for a in classification}
    assert ids == {"logistic_regression", "random_forest_classifier"}

    regression = ml_algorithms.list_algorithms("tabular_regression")
    ids = {a["id"] for a in regression}
    assert ids == {"linear_regression", "random_forest_regressor"}


def test_list_algorithms_unknown_task_type_returns_empty():
    assert ml_algorithms.list_algorithms("no_such_task_type") == []


@pytest.mark.parametrize(
    "algorithm,task_type,expected",
    [
        ("logistic_regression", "tabular_classification", True),
        ("logistic_regression", "tabular_regression", False),
        ("linear_regression", "tabular_regression", True),
        ("linear_regression", "tabular_classification", False),
        ("random_forest_classifier", "tabular_classification", True),
        ("random_forest_regressor", "tabular_regression", True),
        ("nonexistent_algorithm", "tabular_classification", False),
    ],
)
def test_is_valid_for_task(algorithm, task_type, expected):
    assert ml_algorithms.is_valid_for_task(algorithm, task_type) is expected


def test_every_algorithm_hyperparameter_has_required_spec_fields():
    """Guards against a typo'd spec silently breaking the training-job
    creation form on the frontend."""
    for algo in ml_algorithms.ALGORITHMS:
        for param in algo["hyperparameters"]:
            assert "name" in param
            assert "type" in param
            assert param["type"] in ("int", "float", "select")
            if param["type"] in ("int", "float"):
                assert "min" in param and "max" in param
            if param["type"] == "select":
                assert "options" in param and len(param["options"]) > 0
