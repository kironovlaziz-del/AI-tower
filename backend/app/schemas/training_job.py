from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List, Literal


class TrainingJobCreate(BaseModel):
    dataset_id: int
    name: str
    task_type: Literal[
        "tabular_classification",
        "tabular_regression",
        "transformer_text_classification",
        "transformer_text_generation",
    ]
    target_column: Optional[str] = None  # required for tabular_* and transformer_text_classification; unused for generation
    # sklearn track (tabular_*)
    algorithm: Optional[
        Literal[
            "logistic_regression",
            "random_forest_classifier",
            "linear_regression",
            "random_forest_regressor",
        ]
    ] = None
    # transformer track (transformer_text_classification / transformer_text_generation)
    base_model: Optional[str] = None
    hyperparameters: Optional[Dict[str, Any]] = None

    # When true, the backend runs Optuna over the algorithm's search space
    # before training the final model. n_trials bounds the budget.
    auto_tune: bool = False
    auto_tune_trials: int = 20
    auto_tune_metric: Optional[str] = None  # default per task type


class TrainingJobOut(BaseModel):
    id: int
    org_id: int
    dataset_id: int
    name: str
    task_type: str
    target_column: Optional[str]
    algorithm: Optional[str]
    base_model: Optional[str]
    hyperparameters_json: Optional[Dict[str, Any]]
    feature_columns_json: Optional[List[str]]
    status: str
    celery_task_id: Optional[str]
    # The absolute path on disk is intentionally not exposed - the frontend
    # only needs to know whether a downloadable artifact exists.
    has_model_artifact: bool = False
    metrics_json: Optional[Dict[str, Any]]
    error_message: Optional[str]
    progress_pct: Optional[float] = None
    progress_stage: Optional[str] = None
    created_by: Optional[int]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True


class PredictRequest(BaseModel):
    features: Dict[str, Any]


class PredictResponse(BaseModel):
    prediction: Any
