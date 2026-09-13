"""
Registry of classic ML algorithms exposed by the Training Service.

Each entry describes:
- id:              algorithm identifier used in TrainingJob.algorithm
- label:           human-readable name (English; the frontend maps it to
                   a localized label via i18n using the same key)
- task_types:      which task_type values this algorithm is valid for
- hyperparameters: list of tunable parameters with type / range / default
- supports_class_weight: convenience flag for the UI

Adding a new algorithm (SVM, XGBoost, etc.) means appending to this list
and adding the corresponding branch in training_tasks._build_sklearn_model.
The frontend picks it up automatically on the next API call.
"""

from typing import Any, Dict, List


# Hyperparameter spec format:
#   name       - passed to the sklearn constructor
#   label_key  - i18n key suffix under "training.hyperparams.<name>"
#   type       - "int" | "float" | "select"
#   default    - value used when the user leaves the field empty
#   min/max    - bounds for numeric types
#   options    - for select type: list of {value, label_key}

ALGORITHMS: List[Dict[str, Any]] = [
    {
        "id": "logistic_regression",
        "label_key": "training.algorithms.logistic_regression",
        "task_types": ["tabular_classification"],
        "hyperparameters": [
            {
                "name": "max_iter",
                "label_key": "training.max_iter",
                "type": "int",
                "default": 1000,
                "min": 1,
                "max": 100000,
            },
            {
                "name": "class_weight",
                "label_key": "training.class_weight",
                "type": "select",
                "default": "balanced",
                "options": [
                    {"value": "balanced", "label_key": "training.class_weight_balanced"},
                    {"value": "none", "label_key": "training.class_weight_none"},
                ],
            },
        ],
    },
    {
        "id": "random_forest_classifier",
        "label_key": "training.algorithms.random_forest_classifier",
        "task_types": ["tabular_classification"],
        "hyperparameters": [
            {
                "name": "n_estimators",
                "label_key": "training.n_estimators",
                "type": "int",
                "default": 100,
                "min": 1,
                "max": 1000,
            },
            {
                "name": "max_depth",
                "label_key": "training.max_depth",
                "type": "int",
                "default": None,
                "min": 1,
                "max": 100,
            },
            {
                "name": "class_weight",
                "label_key": "training.class_weight",
                "type": "select",
                "default": "balanced",
                "options": [
                    {"value": "balanced", "label_key": "training.class_weight_balanced"},
                    {"value": "none", "label_key": "training.class_weight_none"},
                ],
            },
        ],
    },
    {
        "id": "linear_regression",
        "label_key": "training.algorithms.linear_regression",
        "task_types": ["tabular_regression"],
        "hyperparameters": [],
    },
    {
        "id": "random_forest_regressor",
        "label_key": "training.algorithms.random_forest_regressor",
        "task_types": ["tabular_regression"],
        "hyperparameters": [
            {
                "name": "n_estimators",
                "label_key": "training.n_estimators",
                "type": "int",
                "default": 100,
                "min": 1,
                "max": 1000,
            },
            {
                "name": "max_depth",
                "label_key": "training.max_depth",
                "type": "int",
                "default": None,
                "min": 1,
                "max": 100,
            },
        ],
    },
]


def list_algorithms(task_type: str | None = None) -> List[Dict[str, Any]]:
    """Return all algorithms, optionally filtered by task_type."""
    if task_type is None:
        return ALGORITHMS
    return [a for a in ALGORITHMS if task_type in a["task_types"]]


def is_valid_for_task(algorithm_id: str, task_type: str) -> bool:
    """Sanity check used by training_service.create_job."""
    for a in ALGORITHMS:
        if a["id"] == algorithm_id:
            return task_type in a["task_types"]
    return False
