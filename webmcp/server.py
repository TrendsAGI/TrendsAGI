"""Serve TrendsAGI's tools to your web page for WebMCP.

    pip install "trendsagi>=0.16" fastapi uvicorn
    TRENDSAGI_API_KEY=... uvicorn server:app

Then load trendsagi-webmcp.js in your page and call registerTrendsAGITools().

Replace require_user with your own sign-in check: anyone who can reach these
routes spends your TrendsAGI API quota and reads your account's data.
"""

import os
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, HTTPException, Request

from trendsagi import TrendsAGIClient, TrendsAGITools

# Read-only by default. TrendsAGITools(client, allow_writes=True) would also
# expose add_to_watchlist and update_recommendation, marked readOnlyHint=False.
tools = TrendsAGITools(TrendsAGIClient(api_key=os.environ["TRENDSAGI_API_KEY"]))
app = FastAPI()


def require_user(request: Request) -> None:
    """Placeholder: replace with your application's session check."""
    if not request.cookies.get("session"):
        raise HTTPException(status_code=401, detail="Sign in first.")


@app.get("/trendsagi/tools")
def list_tools(_: None = Depends(require_user)) -> List[Dict[str, Any]]:
    # name, description, inputSchema and annotations, ready for registerTool.
    return tools.webmcp()


@app.post("/trendsagi/tools/{name}")
def call_tool(name: str, arguments: Dict[str, Any], _: None = Depends(require_user)) -> Dict[str, Any]:
    # Errors come back as {"error": ...} so the browser's agent can recover.
    return tools.call(name, arguments)
