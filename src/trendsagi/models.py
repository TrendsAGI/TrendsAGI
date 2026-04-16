from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class _ModelBase(BaseModel):
    @classmethod
    def model_validate(cls, obj: Any):  # pydantic v1/v2 compatibility
        validator = getattr(super(), "model_validate", None)
        if callable(validator):
            return validator(obj)
        return cls.parse_obj(obj)


class AudienceInjection(_ModelBase):
    interest_keywords: List[str] = Field(default_factory=list)
    negative_keywords: List[str] = Field(default_factory=list)
    demographics: Dict[str, Any] = Field(default_factory=dict)
    platform_payloads: Dict[str, Any] = Field(default_factory=dict)


class AIInsight(_ModelBase):
    trend_id: int
    key_themes: List[str] = Field(default_factory=list)
    ad_platform_targeting: Dict[str, Any] = Field(default_factory=dict)
    audience_injection: Optional[AudienceInjection] = None
