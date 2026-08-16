"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class BenchmarkRunRequest(BaseModel):
    """Request model for benchmark execution."""
    scenario_ids: List[int] = Field(..., min_items=1, description="List of scenario IDs to benchmark")
    model_names: List[str] = Field(..., min_items=1, description="List of model names to test")
    
    @field_validator('scenario_ids')
    @classmethod
    def validate_scenario_ids(cls, v):
        """Validate scenario IDs are positive integers."""
        if not all(isinstance(x, int) and x > 0 for x in v):
            raise ValueError("All scenario IDs must be positive integers")
        return v
    
    @field_validator('model_names')
    @classmethod
    def validate_model_names(cls, v):
        """Validate model names are non-empty strings."""
        if not all(isinstance(x, str) and len(x.strip()) > 0 for x in v):
            raise ValueError("All model names must be non-empty strings")
        return [x.strip() for x in v]


class ResultsQueryRequest(BaseModel):
    """Request model for querying results."""
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    scenario_id: Optional[int] = Field(default=None, ge=1, description="Filter by scenario ID")
    model_id: Optional[int] = Field(default=None, ge=1, description="Filter by model ID")


class ExecutionResponse(BaseModel):
    """Response model for execution data."""
    id: int
    scenario_id: int
    model_id: int
    reponse_generee: str
    latence_secondes: float
    date_execution: str


class ScoreResponse(BaseModel):
    """Response model for score data."""
    execution_id: int
    critere: str
    note: float = Field(ge=0, le=1, description="Score between 0 and 1")
    commentaire: Optional[str] = None


class ResultsSummary(BaseModel):
    """Response model for results summary."""
    total_executions: int
    total_scores: int
    date_range: dict
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_executions": 64,
                "total_scores": 256,
                "date_range": {
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-01-02T00:00:00Z"
                }
            }
        }
