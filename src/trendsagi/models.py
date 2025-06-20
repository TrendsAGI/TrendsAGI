# File: trendsagi-client/trendsagi/models.py

from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import List, Optional, Any, Dict
from datetime import datetime, date

# --- Base & Helper Models ---
class OrmBaseModel(BaseModel):
    class Config:
        from_attributes = True

class PaginationMeta(OrmBaseModel):
    total: int
    limit: int
    offset: int
    period: Optional[str] = None
    sort_by: Optional[str] = None
    order: Optional[str] = None
    search: Optional[str] = None
    category: Optional[str] = None

# --- Trends & Insights Models ---
class TrendItem(OrmBaseModel):
    id: int
    name: str
    volume: Optional[int] = None
    timestamp: datetime
    meta_description: Optional[str] = None
    category: Optional[str] = None
    growth: Optional[float] = None
    previous_volume: Optional[int] = None
    absolute_change: Optional[int] = None

class TrendListResponse(OrmBaseModel):
    trends: List[TrendItem]
    meta: PaginationMeta
    
class TweetUser(OrmBaseModel):
    id: int
    user_id: int
    screen_name: str
    name: Optional[str] = None

class Tweet(OrmBaseModel):
    id: int
    tweet_id: int
    text: str
    created_at: datetime
    user: Optional[TweetUser] = None

class TrendDetail(TrendItem):
    tweets: List[Tweet] = Field(default_factory=list)

class TrendDataPoint(OrmBaseModel):
    date: datetime
    volume: Optional[int] = None
    growth_rate: Optional[float] = None

class TrendAnalytics(OrmBaseModel):
    trend_id: int
    name: str
    period: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    data: List[TrendDataPoint]

class TrendSearchResultItem(OrmBaseModel):
    id: int
    name: str
    category: Optional[str] = None
    volume: Optional[int] = None
    timestamp: Optional[datetime] = None
    meta_description: Optional[str] = None

class InsightSearchResponse(OrmBaseModel):
    trends: List[TrendSearchResultItem]
    meta: PaginationMeta

class AIInsightContentBrief(OrmBaseModel):
    target_audience_segments: List[str]
    key_angles_for_content: List[str]
    suggested_content_formats: List[str]
    call_to_action_ideas: List[str]

class AIInsightAdTargeting(OrmBaseModel):
    primary_audience_keywords: List[str]
    secondary_audience_keywords: List[str]
    potential_demographics_summary: Optional[str]

class AIInsight(OrmBaseModel):
    trend_id: int
    trend_name: str
    sentiment_summary: Optional[str]
    sentiment_category: Optional[str]
    key_themes: List[str]
    content_brief: Optional[AIInsightContentBrief]
    ad_platform_targeting: Optional[AIInsightAdTargeting]
    potential_risks_or_controversies: List[str]
    overall_topic_category_llm: Optional[str]
    generated_at: datetime
    llm_model_used: str

# --- Custom Report Models ---
class ReportMeta(OrmBaseModel):
    row_count: int
    limit_applied: Optional[int] = None
    time_period: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class CustomReport(OrmBaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    meta: ReportMeta

# --- Intelligence Suite Models ---
class Recommendation(OrmBaseModel):
    id: int
    user_id: int
    type: str
    title: str
    details: str
    source_trend_id: Optional[str] = None
    source_trend_name: Optional[str] = None
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime
    user_feedback: Optional[str] = None

class RecommendationListResponse(OrmBaseModel):
    recommendations: List[Recommendation]
    meta: PaginationMeta

class MarketEntity(OrmBaseModel):
    id: int
    user_id: int
    name: Optional[str] = None
    handle: str
    website: Optional[HttpUrl] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    followers_count: Optional[int] = None
    overall_sentiment: Optional[str] = None
    top_keywords: Optional[List[str]] = Field(default_factory=list, alias="top_keywords_json")
    recent_topics: Optional[List[str]] = Field(default_factory=list, alias="recent_topics_json")
    last_analyzed_at: Optional[datetime] = Field(None, alias="last_analyzed")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True

class MarketEntityListResponse(OrmBaseModel):
    items: List[MarketEntity]

class CrisisEvent(OrmBaseModel):
    id: int
    user_id: int
    title: str
    summary: str
    severity: str
    status: str
    detected_at: datetime
    source_keywords: Optional[List[str]] = Field(None, alias="source_keywords_json")
    impacted_entity: Optional[str] = None
    trend_snapshot_link: Optional[HttpUrl] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True

class CrisisEventListResponse(OrmBaseModel):
    events: List[CrisisEvent]
    meta: PaginationMeta

class DeepAnalysisSentiment(OrmBaseModel):
    overall_sentiment_category: str
    positive_nuances: List[str]
    negative_nuances: List[str]
    neutral_aspects: List[str]

class DeepAnalysisActionableInsights(OrmBaseModel):
    marketing_pr: List[str]
    product_development: List[str]
    crm_strategy: List[str]
    
class DeepAnalysisRelatedTrend(OrmBaseModel):
    id: str
    name: str

class DeepAnalysis(OrmBaseModel):
    query_analyzed: str
    generated_at: datetime
    llm_model_used: str
    overall_summary: str
    key_findings: List[str]
    sentiment_analysis: DeepAnalysisSentiment
    causal_factors: List[str]
    emerging_sub_topics: List[str]
    future_outlook_and_predictions: List[str]
    actionable_insights_for_roles: DeepAnalysisActionableInsights
    related_trends: List[DeepAnalysisRelatedTrend]

# --- User & Account Management Models ---
class TopicInterest(OrmBaseModel):
    id: int
    user_id: int
    keyword: str
    alert_condition_type: str
    volume_threshold_value: Optional[int] = None
    percentage_growth_value: Optional[float] = None
    created_at: datetime

class ExportConfiguration(OrmBaseModel):
    id: int
    destination: str
    config: Dict[str, Any]
    schedule: str
    schedule_time: Optional[str] = None
    is_active: bool

class ExportExecutionLog(OrmBaseModel):
    id: int
    execution_time: datetime
    duration_seconds: Optional[float] = None
    destination: str
    status: str
    message: Optional[str] = None
    records_exported: Optional[int] = None
    export_configuration_id: Optional[int] = None

class ExportHistoryResponse(OrmBaseModel):
    history: List[ExportExecutionLog]
    meta: PaginationMeta

class DashboardStats(OrmBaseModel):
    active_trends: int
    alerts_today: int
    topic_interests: int
    avg_growth: Optional[float] = None

class Notification(OrmBaseModel):
    id: int
    title: str
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None

class NotificationListResponse(OrmBaseModel):
    notifications: List[Notification]
    unread_count: int

# --- Public Information & Status Models ---
class SubscriptionPlan(OrmBaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price_monthly: Optional[float] = None
    price_yearly: Optional[float] = None
    is_custom: bool
    features: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ComponentStatus(OrmBaseModel):
    name: str
    status: str
    description: str

class StatusPage(OrmBaseModel):
    overall_status: str
    last_updated: datetime
    components: List[ComponentStatus]

# NEW: Model for API Status History
class StatusHistoryResponse(OrmBaseModel):
    uptime_percentages: Dict[str, float]
    daily_statuses: Dict[str, Dict[str, str]]