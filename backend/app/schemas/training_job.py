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
    ]
    target_column: str
    # sklearn track (tabular_*)
    algorithm: Optional[
        Literal[
            "logistic_regression",
            "random_forest_classifier",
            "linear_regression",
            "random_forest_regressor",
        ]
    ] = None
    # transformer track (transformer_text_classification)
    base_model: Optional[str] = None
    hyperparameters: Optional[Dict[str, Any]] = None


class TrainingJobOut(BaseModel):
    id: int
    org_id: int
    dataset_id: int
    name: str
    task_type: str
    target_column: str
    algorithm: Optional[str]
    base_model: Optional[str]
    hyperparameters_json: Optional[Dict[str, Any]]
    feature_columns_json: Optional[List[str]]
    status: str
    metrics_json: Optional[Dict[str, Any]]
    error_message: Optional[str]
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
