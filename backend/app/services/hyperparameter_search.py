"""
Optuna search spaces for the classic ML track.

Each entry maps an algorithm id (see ml_algorithms.py) to a function that
proposes hyperparameters on a per-trial basis. The suggested values are
merged with user-supplied hyperparameters - user values always win, so a
caller can pin any parameter and let Optuna tune the rest.

The search spaces are intentionally conservative: they keep trial run
times reasonable on a CPU-only host.
"""

from typing import Any, Dict

import optuna


def suggest_logistic_regression(trial: "optuna.Trial") -> Dict[str, Any]:
    return {
        "max_iter": trial.suggest_int("max_iter", 200, 3000, step=100),
        "C": trial.suggest_float("C", 1e-3, 10.0, log=True),
        "class_weight": trial.suggest_categorical(
            "class_weight", ["balanced", None]
        ),
    }


def suggest_random_forest_classifier(trial: "optuna.Trial") -> Dict[str, Any]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 50, 400, step=50),
        "max_depth": trial.suggest_int("max_depth", 2, 20),
        "class_weight": trial.suggest_categorical(
            "class_weight", ["balanced", None]
        ),
    }


def suggest_linear_regression(trial: "optuna.Trial") -> Dict[str, Any]:
    return {}


def suggest_random_forest_regressor(trial: "optuna.Trial") -> Dict[str, Any]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 50, 400, step=50),
        "max_depth": trial.suggest_int("max_depth", 2, 20),
    }


SUGGESTERS = {
    "logistic_regression": suggest_logistic_regression,
    "random_forest_classifier": suggest_random_forest_classifier,
    "linear_regression": suggest_linear_regression,
    "random_forest_regressor": suggest_random_forest_regressor,
}


def suggest(algorithm: str, trial: "optuna.Trial") -> Dict[str, Any]:
    """Return suggested hyperparameters for one trial, or {} if unknown."""
    fn = SUGGESTERS.get(algorithm)
    if fn is None:
        return {}
    return fn(trial)
