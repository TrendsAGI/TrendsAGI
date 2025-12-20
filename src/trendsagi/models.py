# File: trendsagi-client/trendsagi/models.py

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Any, Dict
from datetime import datetime, date

# --- Base & Helper Models ---
class OrmBaseModel(BaseModel):
    class Config:
        from_attributes = True
        populate_by_name = True  

class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    period: Optional[str] = None
    sort_by: Optional[str] = None
    order: Optional[str] = None
    search: Optional[str] = None
    category: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


# --- Autocomplete and Categories Models ---
class AutocompleteResponse(OrmBaseModel):
    suggestions: List[str]

class ActiveCategoriesResponse(OrmBaseModel):
    categories: List[str]

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
    average_velocity: Optional[float] = Field(None, description="Average velocity (posts/hour) over recent snapshots.")
    trend_stability: Optional[float] = Field(None, description="Standard deviation of volume over recent snapshots. Lower is more stable.")
    overall_trend: Optional[str] = Field(None, description="Qualitative assessment of the trend's direction (growing, declining, stable).")

class TrendListResponse(OrmBaseModel):
    trends: List[TrendItem]
    meta: PaginationMeta 

class TrendDataPoint(OrmBaseModel):
    date: datetime
    volume: Optional[int] = None
    velocity_per_hour: Optional[float] = None
    acceleration: Optional[float] = None
    is_forecast: Optional[bool] = False

class TrendAnalytics(OrmBaseModel):
    trend_id: int
    name: str
    period: str
    start_date: Optional[str] = None
    end_date: str
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
    usage_count: Optional[int] = None
    usage_limit: Optional[int] = None

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
    source_trend_id: Optional[int] = None
    source_trend_name: Optional[str] = None
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime
    user_feedback: Optional[str] = None

class RecommendationListResponse(OrmBaseModel):
    recommendations: List[Recommendation]
    meta: PaginationMeta

# --- Intelligence Models ---

class UsageInfo(OrmBaseModel):
    count: int
    limit: int

class CrisisEvent(OrmBaseModel):
    id: int
    user_id: int
    title: str
    summary: str
    severity: str
    status: str
    detected_at: datetime
    source_keywords: Optional[List[str]] = None
    impacted_entity: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class CrisisEventListResponse(OrmBaseModel):
    events: List[CrisisEvent]
    meta: PaginationMeta

# --- Financial Data Models ---
class FinancialNews(OrmBaseModel):
    id: int
    title: str
    summary: str
    source_timestamp: Optional[str] = None
    sentiment: Optional[str] = None
    company: Optional[str] = None
    created_at: datetime

class FinancialPressRelease(OrmBaseModel):
    id: int
    company: str
    title: str
    summary: str
    source_timestamp: Optional[str] = None
    sentiment: Optional[str] = None
    created_at: datetime

class EarningsReport(OrmBaseModel):
    id: int
    company: str
    period: str
    revenue: Optional[str] = None
    earnings_per_share: Optional[str] = None
    guidance_update: Optional[str] = None
    source_timestamp: Optional[str] = None
    sentiment: Optional[str] = None
    created_at: datetime

class IPONews(OrmBaseModel):
    id: int
    company: str
    symbol: Optional[str] = None
    status: Optional[str] = None
    filing_date: Optional[str] = None
    expected_trade_date: Optional[str] = None
    created_at: datetime

class MarketSentiment(OrmBaseModel):
    id: int
    sentiment: str
    drivers: Optional[List[str]] = None
    source_timestamp: Optional[str] = None
    created_at: datetime


class ForexFactoryEvent(OrmBaseModel):
    id: int
    event_at: datetime  
    currency: str
    impact: Optional[str] = None
    event_name: str
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    updated_at: datetime
    @property
    def event_date(self) -> str:
        return self.event_at.strftime('%Y-%m-%d')

    @property
    def event_time(self) -> str:
        return self.event_at.strftime('%H:%M:%S %Z') 

class FinancialDataResponse(OrmBaseModel):
    market_sentiment: Optional[MarketSentiment] = None
    earnings_reports: List[EarningsReport] = Field(default_factory=list)
    financial_news: List[FinancialNews] = Field(default_factory=list)
    financial_press_releases: List[FinancialPressRelease] = Field(default_factory=list)
    ipo_filings_news: List[IPONews] = Field(default_factory=list)
    forex_factory_events: List[ForexFactoryEvent] = Field(default_factory=list) 

class CombinedReleaseResponse(OrmBaseModel):
    id: str
    title: str
    published_at: str
    source: str
    source_id: Optional[str] = None

class HomepageEarningsReportResponse(OrmBaseModel):
    id: int
    company: str
    source_timestamp: Optional[datetime] = None
    report_time_of_day: str
    period: str

class HomepageIPONewsResponse(OrmBaseModel):
    id: int
    company: str
    symbol: str
    status: str
    expected_trade_date: str

class HomepageFinancialDataResponse(OrmBaseModel):
    earnings_reports: List[HomepageEarningsReportResponse]
    releases: List[CombinedReleaseResponse]
    ipo_filings_news: List[HomepageIPONewsResponse]

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
    selected_fields: List[str] = Field(default_factory=list)
    file_name_template: Optional[str] = None

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

class DashboardOverview(OrmBaseModel):
    stats: DashboardStats
    top_trends: List[TrendItem]
    recent_alerts: List[Notification]

class NotificationListResponse(OrmBaseModel):
    notifications: List[Notification]
    unread_count: int

# --- Public Information & Status Models ---
class SessionInfoResponse(OrmBaseModel):
    country: str

class SubscriptionPlan(OrmBaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price_monthly: Optional[Dict[str, float]] = None
    price_yearly: Optional[Dict[str, float]] = None
    is_custom: bool
    features: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ComponentStatus(OrmBaseModel):
    name: str
    status: str
    description: Optional[str] = None

class StatusPage(OrmBaseModel):
    overall_status: str
    last_updated: datetime
    components: List[ComponentStatus]

class StatusHistoryResponse(OrmBaseModel):
    uptime_percentages: Dict[str, float]
    daily_statuses: Dict[str, Dict[str, str]]


# --- Context Intelligence Suite Models ---

class ContextProject(OrmBaseModel):
    """A context project for organizing AI agent context."""
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool = True
    item_count: int = 0
    total_size_bytes: int = 0
    created_at: datetime
    updated_at: datetime


class ContextProjectListResponse(OrmBaseModel):
    projects: List[ContextProject]
    meta: PaginationMeta


class ContextItem(OrmBaseModel):
    """A context item (spec, plan, code, etc.) within a project."""
    id: int
    project_id: int
    item_type: str
    name: str
    content: Optional[str] = None
    file_size_bytes: int = 0
    mime_type: Optional[str] = None
    original_filename: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    has_content: bool = False
    created_at: datetime
    updated_at: datetime


class ContextItemListResponse(OrmBaseModel):
    items: List[ContextItem]
    meta: PaginationMeta


class ContextUsage(OrmBaseModel):
    """Storage usage for context items."""
    used_bytes: int
    limit_bytes: int
    used_percentage: float
    plan_name: str