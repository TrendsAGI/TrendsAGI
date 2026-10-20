"""Tool definitions that let AI agents use TrendsAGI.

One registry, several wire formats. The same tool names, descriptions, and
JSON schemas are exported for OpenAI function calling, Anthropic tool use,
LangChain, and the bundled MCP server (``trendsagi mcp``), so an agent built
on any of them sees an identical surface and :meth:`TrendsAGITools.call`
executes the request.

Read-only by default. Tools that change account state (adding a watchlist
topic, moving a recommendation through its workflow) are only exposed when
``allow_writes=True`` is passed explicitly.

Example::

    from openai import OpenAI
    from trendsagi import TrendsAGIClient
    from trendsagi.agent_tools import TrendsAGITools

    tools = TrendsAGITools(TrendsAGIClient(api_key="..."))
    response = OpenAI().chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "What is trending in Technology?"}],
        tools=tools.openai(),
    )
    for call in response.choices[0].message.tool_calls or []:
        result = tools.call(call.function.name, call.function.arguments)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

from . import exceptions
from .client import TrendsAGIClient

__all__ = ["AgentTool", "TrendsAGITools"]

# Keep tool results small enough to fit comfortably in a model context window.
_MAX_LIST_ITEMS = 25
_MAX_SQL_ROWS = 200
_MAX_RESULT_CHARS = 20000


@dataclass(frozen=True)
class AgentTool:
    """A single tool: its public contract plus the function that serves it."""

    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., Any]
    writes: bool = False


def _schema(properties: Dict[str, Any], required: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


def _limit(default: int = 10, maximum: int = _MAX_LIST_ITEMS) -> Dict[str, Any]:
    return {
        "type": "integer",
        "minimum": 1,
        "maximum": maximum,
        "default": default,
        "description": f"Number of results to return (1-{maximum}).",
    }


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True, by_alias=False)
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


class TrendsAGITools:
    """Agent tool registry bound to a :class:`TrendsAGIClient`.

    :param client: An authenticated client.
    :param allow_writes: Expose tools that modify account state. Off by default
        so an autonomous agent cannot change anything unless you opt in.
    """

    def __init__(self, client: TrendsAGIClient, allow_writes: bool = False):
        self.client = client
        self.allow_writes = allow_writes
        self._tools: Dict[str, AgentTool] = {}
        for tool in self._build():
            if tool.writes and not allow_writes:
                continue
            self._tools[tool.name] = tool

    # -- registry --------------------------------------------------------

    @property
    def tools(self) -> List[AgentTool]:
        return list(self._tools.values())

    @property
    def names(self) -> List[str]:
        return list(self._tools)

    def _build(self) -> List[AgentTool]:
        c = self.client
        return [
            AgentTool(
                name="list_trends",
                description=(
                    "List topics trending right now on social platforms with measured volume, "
                    "velocity and growth. Sort by velocity to find what is accelerating fastest - "
                    "the best moment to target an audience or launch a creative before competitors "
                    "bid on it. Filter by category or a search phrase."
                ),
                parameters=_schema({
                    "category": {"type": "string", "description": "Category name, e.g. 'Technology'. Use list_trend_categories for valid names."},
                    "search": {"type": "string", "description": "Only return trends whose name matches this phrase."},
                    "sort_by": {
                        "type": "string",
                        "enum": ["velocity", "growth", "volume", "timestamp", "name"],
                        "default": "velocity",
                    },
                    "period": {"type": "string", "description": "Optional lookback window, e.g. '24h' or '7d'."},
                    "limit": _limit(),
                }),
                handler=lambda category=None, search=None, sort_by="velocity", period=None, limit=10: c.get_trends(
                    category=category, search=search, sort_by=sort_by, period=period, limit=limit
                ),
            ),
            AgentTool(
                name="list_trend_categories",
                description="List the trend category names that list_trends accepts.",
                parameters=_schema({}),
                handler=lambda: c.get_trend_categories(),
            ),
            AgentTool(
                name="search_trend_insights",
                description=(
                    "Search AI-generated trend insights by theme, e.g. 'AI chips' or 'sustainable "
                    "packaging', to find related trends, why they are moving and which audiences "
                    "care - useful for building interest and keyword targeting around a product."
                ),
                parameters=_schema({
                    "query": {"type": "string", "description": "Theme or phrase to search for."},
                    "limit": _limit(),
                }, ["query"]),
                handler=lambda query, limit=10: c.search_insights(key_theme_contains=query, limit=limit),
            ),
            AgentTool(
                name="get_trend",
                description="Get one trend by its numeric id, including volume, growth and category.",
                parameters=_schema({"trend_id": {"type": "integer", "minimum": 1}}, ["trend_id"]),
                handler=lambda trend_id: c.get_trend(trend_id),
            ),
            AgentTool(
                name="get_trend_ai_insights",
                description=(
                    "Get the cached AI insight for a trend: summary, key themes, sentiment, audience "
                    "and suggested marketing angles to use in ad copy and creative briefs. Returns "
                    "null when no insight exists yet."
                ),
                parameters=_schema({"trend_id": {"type": "integer", "minimum": 1}}, ["trend_id"]),
                handler=lambda trend_id: c.get_ai_insights(trend_id),
            ),
            AgentTool(
                name="get_trend_analytics",
                description=(
                    "Get the time series of a trend's volume over a period, to judge whether it is "
                    "still rising (scale spend) or already fading (pull back) before committing budget."
                ),
                parameters=_schema({
                    "trend_id": {"type": "integer", "minimum": 1},
                    "period": {"type": "string", "enum": ["24h", "7d", "30d"], "default": "7d"},
                }, ["trend_id"]),
                handler=lambda trend_id, period="7d": c.get_trend_analytics(trend_id, period=period),
            ),
            AgentTool(
                name="list_recommendations",
                description=(
                    "List evidence-backed recommendations for this account (content ideas, marketing "
                    "angles, PR responses, SEO actions) with a decision brief. The confidence score "
                    "measures evidence completeness, not the probability of success."
                ),
                parameters=_schema({
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "critical", "all"]},
                    "status": {"type": "string", "enum": ["new", "viewed", "actioned", "dismissed", "all"], "default": "new"},
                    "recommendation_type": {
                        "type": "string",
                        "enum": [
                            "pr_response", "content_idea", "marketing_angle", "seo_optimization",
                            "influencer_collab", "product_improvement", "crm_strategy", "monitoring", "other", "all",
                        ],
                    },
                    "match_user_interests": {"type": "boolean", "default": False},
                    "limit": _limit(),
                }),
                handler=lambda priority=None, status="new", recommendation_type=None, match_user_interests=False, limit=10: c.get_recommendations(
                    limit=limit, priority=priority, status=status,
                    recommendation_type=recommendation_type, match_user_interests=match_user_interests,
                ),
            ),
            AgentTool(
                name="list_crisis_events",
                description=(
                    "List reputation or crisis events detected for this account's monitored topics - "
                    "check before scaling spend on a brand or topic."
                ),
                parameters=_schema({
                    "status": {"type": "string", "enum": ["active", "resolved", "all"], "default": "active"},
                    "time_range": {"type": "string", "enum": ["24h", "7d", "30d"], "default": "24h"},
                    "limit": _limit(),
                }),
                handler=lambda status="active", time_range="24h", limit=10: c.get_crisis_events(
                    limit=limit, status=status, time_range=time_range
                ),
            ),
            AgentTool(
                name="list_watchlist",
                description="List the topics this account is watching, with their alert conditions.",
                parameters=_schema({}),
                handler=lambda: c.get_topic_interests(),
            ),
            AgentTool(
                name="get_api_usage",
                description="Get this API key's usage against its daily limit, so the agent can pace itself.",
                parameters=_schema({}),
                handler=lambda: c.get_api_usage(),
            ),
            AgentTool(
                name="read_data_schema",
                description=(
                    "List the tables execute_sql can query, with every column's type and meaning, "
                    "the query rules and example queries. Call once before writing SQL."
                ),
                parameters=_schema({}),
                handler=lambda: c.get_data_schema(),
            ),
            AgentTool(
                name="execute_sql",
                description=(
                    "Run one read-only PostgreSQL SELECT over the account's TrendsAGI data (tables from "
                    "read_data_schema: trends, trend_snapshots, trend_categories, trend_insights, "
                    "watchlist, recommendations, crisis_events). Use for questions that need filtering, "
                    "joins or aggregation. Returns columns and rows; results stop at max_rows."
                ),
                parameters=_schema({
                    "query": {
                        "type": "string",
                        "maxLength": 10000,
                        "description": (
                            "One SELECT (WITH ... SELECT is fine), e.g. SELECT name, volume, growth_pct "
                            "FROM trends WHERE last_seen_at > now() - interval '24 hours' "
                            "ORDER BY velocity_per_hour DESC NULLS LAST LIMIT 20."
                        ),
                    },
                    "max_rows": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": _MAX_SQL_ROWS,
                        "default": 50,
                        "description": f"Most rows to return (1-{_MAX_SQL_ROWS}).",
                    },
                }, ["query"]),
                # The server stops adding rows below the result cap, so a large
                # result arrives as valid JSON marked truncated, not as a preview.
                handler=lambda query, max_rows=50: c.execute_sql(
                    query, max_rows=max(1, min(int(max_rows), _MAX_SQL_ROWS)),
                    max_result_bytes=_MAX_RESULT_CHARS - 2000,
                ),
            ),
            AgentTool(
                name="find_capability",
                description=(
                    "Check whether TrendsAGI can do a task and how: returns the tools that cover it, "
                    "or the page in the TrendsAGI app where the user does it. Use when no other tool "
                    "fits the user's request, for example setting up an alert, exporting data or "
                    "connecting an ad account. Describe the task in a few words; do not include "
                    "personal details."
                ),
                parameters=_schema({
                    "goal": {
                        "type": "string",
                        "maxLength": 200,
                        "description": "The task in a few words, e.g. 'alert me when a topic spikes'.",
                    },
                }, ["goal"]),
                handler=lambda goal: c.find_capability(goal),
            ),
            AgentTool(
                name="add_to_watchlist",
                description=(
                    "Start watching a topic and alert when it crosses a volume threshold or a "
                    "percentage growth. Changes account state."
                ),
                parameters=_schema({
                    "keyword": {"type": "string", "description": "Topic to watch."},
                    "alert_condition_type": {"type": "string", "enum": ["volume_threshold", "percentage_growth"]},
                    "volume_threshold_value": {"type": "integer", "minimum": 1},
                    "percentage_growth_value": {"type": "number", "exclusiveMinimum": 0},
                }, ["keyword", "alert_condition_type"]),
                handler=lambda keyword, alert_condition_type, volume_threshold_value=None, percentage_growth_value=None: c.create_topic_interest(
                    keyword=keyword, alert_condition_type=alert_condition_type,
                    volume_threshold_value=volume_threshold_value, percentage_growth_value=percentage_growth_value,
                ),
                writes=True,
            ),
            AgentTool(
                name="update_recommendation",
                description=(
                    "Move a recommendation through its workflow (viewed, actioned, dismissed) or "
                    "leave feedback. Provide exactly one of action or feedback. Changes account state."
                ),
                parameters=_schema({
                    "recommendation_id": {"type": "integer", "minimum": 1},
                    "action": {"type": "string", "enum": ["new", "viewed", "actioned", "dismissed"]},
                    "feedback": {"type": "string", "maxLength": 500},
                }, ["recommendation_id"]),
                handler=lambda recommendation_id, action=None, feedback=None: c.perform_recommendation_action(
                    recommendation_id, action=action, feedback=feedback
                ),
                writes=True,
            ),
        ]

    # -- wire formats ----------------------------------------------------

    def openai(self) -> List[Dict[str, Any]]:
        """Tools for OpenAI Chat Completions ``tools=``."""
        return [
            {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
            for t in self.tools
        ]

    def openai_responses(self) -> List[Dict[str, Any]]:
        """Tools for the OpenAI Responses API ``tools=``."""
        return [
            {"type": "function", "name": t.name, "description": t.description, "parameters": t.parameters}
            for t in self.tools
        ]

    def anthropic(self) -> List[Dict[str, Any]]:
        """Tools for the Anthropic Messages API ``tools=``."""
        return [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in self.tools]

    def langchain(self) -> List[Any]:
        """LangChain ``StructuredTool`` objects (requires ``langchain-core``)."""
        try:
            from langchain_core.tools import StructuredTool
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError("Install langchain-core to use TrendsAGITools.langchain()") from exc

        def make(tool: AgentTool) -> Any:
            def run(**kwargs: Any) -> str:
                return json.dumps(self.call(tool.name, kwargs))

            return StructuredTool.from_function(
                func=run, name=tool.name, description=tool.description, args_schema=tool.parameters
            )

        return [make(tool) for tool in self.tools]

    # -- execution -------------------------------------------------------

    def call(self, name: str, arguments: Union[str, Dict[str, Any], None] = None) -> Dict[str, Any]:
        """Execute a tool and return a JSON-serialisable result.

        Errors are returned as ``{"error": ...}`` rather than raised, so an agent
        loop can show the failure to the model and let it recover.
        """
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"unknown tool {name!r}", "available_tools": self.names}
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments.strip() else {}
            except json.JSONDecodeError as exc:
                return {"error": f"arguments are not valid JSON: {exc}"}
        arguments = dict(arguments or {})
        allowed = set(tool.parameters.get("properties", {}))
        unknown = sorted(set(arguments) - allowed)
        if unknown:
            return {"error": f"unexpected arguments: {', '.join(unknown)}"}
        missing = [key for key in tool.parameters.get("required", []) if arguments.get(key) in (None, "")]
        if missing:
            return {"error": f"missing required arguments: {', '.join(missing)}"}
        if "limit" in arguments:
            try:
                arguments["limit"] = max(1, min(int(arguments["limit"]), _MAX_LIST_ITEMS))
            except (TypeError, ValueError):
                return {"error": "limit must be an integer"}

        try:
            result = _to_jsonable(tool.handler(**arguments))
        except exceptions.QueryError as exc:
            # The model fixes its SQL from these, so pass them through whole.
            error = {"error": exc.code, "detail": exc.error_detail}
            if exc.hint:
                error["hint"] = exc.hint
            if exc.position:
                error["position"] = exc.position
            return error
        except exceptions.RateLimitError as exc:
            return {"error": "rate_limited", "detail": str(exc), "hint": "Call get_api_usage and wait before retrying."}
        except exceptions.AuthenticationError as exc:
            return {"error": "authentication_failed", "detail": str(exc)}
        except exceptions.NotFoundError as exc:
            return {"error": "not_found", "detail": str(exc)}
        except (exceptions.TrendsAGIError, ValueError) as exc:
            return {"error": type(exc).__name__, "detail": str(exc)}

        payload = {"result": result}
        encoded = json.dumps(payload, default=str)
        if len(encoded) > _MAX_RESULT_CHARS:
            payload = {
                "result_truncated": True,
                "result_preview": encoded[:_MAX_RESULT_CHARS],
                "hint": "Narrow the request with a smaller limit or a filter.",
            }
        return payload
