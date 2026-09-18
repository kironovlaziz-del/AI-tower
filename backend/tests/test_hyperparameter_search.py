"""
hyperparameter_search.py: Optuna search-space suggesters.

Uses a real optuna study/trial via study.ask() rather than mocking the
Trial object - suggest_int/suggest_float/suggest_categorical are cheap,
in-memory operations with no external calls, so there's no reason to fake
them, and doing so would risk testing our mock instead of optuna's real
contract (e.g. that suggest_categorical actually returns one of the given
choices).
"""

import optuna

from app.services import hyperparameter_search


def _real_trial() -> optuna.Trial:
    study = optuna.create_study()
    return study.ask()


def test_suggest_logistic_regression_bounds():
    params = hyperparameter_search.suggest_logistic_regression(_real_trial())
    assert 200 <= params["max_iter"] <= 3000
    assert 1e-3 <= params["C"] <= 10.0
    assert params["class_weight"] in ("balanced", None)


def test_suggest_random_forest_classifier_bounds():
    params = hyperparameter_search.suggest_random_forest_classifier(_real_trial())
    assert 50 <= params["n_estimators"] <= 400
    assert 2 <= params["max_depth"] <= 20
    assert params["class_weight"] in ("balanced", None)


def test_suggest_linear_regression_has_no_tunable_params():
    assert hyperparameter_search.suggest_linear_regression(_real_trial()) == {}


def test_suggest_random_forest_regressor_bounds():
    params = hyperparameter_search.suggest_random_forest_regressor(_real_trial())
    assert 50 <= params["n_estimators"] <= 400
    assert 2 <= params["max_depth"] <= 20


def test_suggest_dispatches_to_the_right_algorithm():
    params = hyperparameter_search.suggest("random_forest_regressor", _real_trial())
    assert set(params.keys()) == {"n_estimators", "max_depth"}


def test_suggest_returns_empty_dict_for_unknown_algorithm():
    assert hyperparameter_search.suggest("some_unregistered_algorithm", _real_trial()) == {}
