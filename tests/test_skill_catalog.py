"""Tests for the skills catalog and the MCP registrations that serve it."""

from __future__ import annotations

import asyncio
import hashlib
from types import SimpleNamespace

import pytest

from trendsagi.skill_catalog import (
    SKILLS_EXTENSION,
    catalog,
    load_catalog,
    parse_frontmatter,
)


def test_packaged_catalog_has_a_complete_manifest():
    skills = load_catalog()
    assert [entry.uri for entry in skills.entries] == ["skill://trendsagi/SKILL.md"]
    entry = skills.entries_by_uri["skill://trendsagi/SKILL.md"]
    assert entry.frontmatter["name"] == "trendsagi"
    assert entry.frontmatter["description"]

    manifest = {resource.uri: resource for resource in entry.resources}
    assert set(manifest) == {
        "skill://trendsagi/SKILL.md",
        "skill://trendsagi/references/errors.md",
        "skill://trendsagi/references/paid-media.md",
        "skill://trendsagi/references/sql.md",
        "skill://trendsagi/references/tools.md",
    }
    for resource in entry.resources:
        assert resource.digest.startswith("sha256:")
        assert len(resource.digest) == len("sha256:") + 64
        assert resource.size > 0

    contents = skills.read_result("skill://trendsagi/SKILL.md")["contents"][0]
    raw = contents["text"].encode("utf-8")
    assert manifest["skill://trendsagi/SKILL.md"].size == len(raw)
    assert manifest["skill://trendsagi/SKILL.md"].digest == "sha256:" + hashlib.sha256(raw).hexdigest()


def test_catalog_lists_directories_and_rejects_unknown_uris():
    skills = catalog()
    listing = skills.directory_result("skill://trendsagi")
    uris = {resource["uri"] for resource in listing["resources"]}
    assert uris == {"skill://trendsagi/SKILL.md", "skill://trendsagi/references"}
    references = skills.directory_result("skill://trendsagi/references")
    assert {resource["uri"] for resource in references["resources"]} == {
        "skill://trendsagi/references/errors.md",
        "skill://trendsagi/references/paid-media.md",
        "skill://trendsagi/references/sql.md",
        "skill://trendsagi/references/tools.md",
    }
    with pytest.raises(KeyError):
        skills.read_result("skill://missing/SKILL.md")
    with pytest.raises(KeyError):
        skills.get_result("skill://missing/SKILL.md")
    with pytest.raises(KeyError):
        skills.directory_result("skill://trendsagi/SKILL.md")


def test_frontmatter_supports_folded_descriptions():
    frontmatter = parse_frontmatter(
        "---\n"
        "name: example\n"
        "description: >-\n"
        "  Use this skill when a task\n"
        "  spans several tools.\n"
        "license: MIT\n"
        "---\n\n# Example\n"
    )
    assert frontmatter == {
        "name": "example",
        "description": "Use this skill when a task spans several tools.",
        "license": "MIT",
    }


class _FakeTools:
    tools = []

    def call(self, name, arguments):
        return {}


def test_mcp_server_advertises_and_registers_skills():
    pytest.importorskip("mcp")
    from trendsagi.mcp_server import SKILLS_EXTENSION as SERVER_EXTENSION
    from trendsagi.mcp_server import build_server

    server = build_server(_FakeTools())
    assert SERVER_EXTENSION == SKILLS_EXTENSION
    assert server.extensions[SKILLS_EXTENSION] == {"directoryRead": True}

    options = server.create_initialization_options()
    assert options.capabilities.resources is not None
    assert options.capabilities.extensions[SKILLS_EXTENSION] == {"directoryRead": True}

    list_handler = server.get_request_handler("skills/list").handler
    listing = asyncio.run(list_handler(None, SimpleNamespace(cursor=None)))
    assert listing["skills"][0]["uri"] == "skill://trendsagi/SKILL.md"

    get_handler = server.get_request_handler("skills/get").handler
    entry = asyncio.run(get_handler(None, SimpleNamespace(uri="skill://trendsagi/SKILL.md")))
    assert entry["skill"]["frontmatter"]["name"] == "trendsagi"

    read_handler = server.get_request_handler("resources/read").handler
    contents = asyncio.run(read_handler(None, SimpleNamespace(uri="skill://trendsagi/SKILL.md")))
    assert contents["contents"][0]["mimeType"] == "text/markdown"
    assert "name: trendsagi" in contents["contents"][0]["text"]

    directory_handler = server.get_request_handler("resources/directory/read").handler
    directory = asyncio.run(directory_handler(None, SimpleNamespace(uri="skill://trendsagi")))
    assert {resource["uri"] for resource in directory["resources"]} == {
        "skill://trendsagi/SKILL.md",
        "skill://trendsagi/references",
    }


def test_mcp_serves_skills_over_the_modern_protocol():
    pytest.importorskip("mcp")
    from typing import Literal

    from pydantic import TypeAdapter

    import mcp.types as types
    from mcp import Client
    from mcp.shared.exceptions import MCPError

    from trendsagi.mcp_server import build_server

    class SkillsListRequest(types.Request[types.PaginatedRequestParams, Literal["skills/list"]]):
        method: Literal["skills/list"] = "skills/list"
        params: types.PaginatedRequestParams

    async def scenario():
        async with Client(build_server(_FakeTools())) as client:
            assert client.protocol_version == "2026-07-28"
            assert client.server_capabilities.extensions[SKILLS_EXTENSION] == {"directoryRead": True}

            listing = await client.session.send_request(
                SkillsListRequest(params=types.PaginatedRequestParams()),
                TypeAdapter(dict),
            )
            assert listing["resultType"] == "complete"
            assert listing["skills"][0]["uri"] == "skill://trendsagi/SKILL.md"

            contents = await client.session.read_resource("skill://trendsagi/SKILL.md")
            assert contents.contents[0].mime_type == "text/markdown"
            assert "name: trendsagi" in contents.contents[0].text

            try:
                await client.session.read_resource("skill://missing/SKILL.md")
            except MCPError as exc:
                assert exc.code == types.INVALID_PARAMS
            else:  # pragma: no cover - a missing resource must fail
                raise AssertionError("an unknown skill resource must be invalid params")

    asyncio.run(scenario())
