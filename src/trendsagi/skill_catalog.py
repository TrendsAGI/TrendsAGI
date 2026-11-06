"""Agent Skills served over MCP (SEP-2640).

The package ships one skill, ``trendsagi``, next to this module. Every file is
served as a resource under ``skill://`` and the ``skills/list`` / ``skills/get``
entries carry a complete manifest with a SHA-256 digest and byte size. The MCP
server advertises the ``io.modelcontextprotocol/skills`` extension and registers
the methods in :mod:`trendsagi.mcp_server`.

The catalog is deliberately independent of the MCP SDK so it can be tested
without the optional ``mcp`` dependency.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SKILLS_EXTENSION = "io.modelcontextprotocol/skills"
SKILLS_TTL_MS = 300_000
SKILLS_CACHE_SCOPE = "public"
SKILLS_PAGE_SIZE = 50

_NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


@dataclass(frozen=True)
class SkillResource:
    """One file in a skill's manifest."""

    uri: str
    digest: str
    size: int

    def as_dict(self) -> Dict[str, Any]:
        return {"uri": self.uri, "digest": self.digest, "size": self.size}


@dataclass(frozen=True)
class SkillEntry:
    """The ``skills/list`` / ``skills/get`` entry for one skill."""

    uri: str
    frontmatter: Dict[str, Any]
    resources: Tuple[SkillResource, ...]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "frontmatter": self.frontmatter,
            "resources": [resource.as_dict() for resource in self.resources],
        }


@dataclass(frozen=True)
class SkillFile:
    """A skill file's bytes and resource metadata."""

    uri: str
    name: str
    mime_type: str
    text: Optional[str]
    blob: bytes

    def as_resource(self, description: str = "", title: str = "") -> Dict[str, Any]:
        resource: Dict[str, Any] = {
            "uri": self.uri,
            "name": self.name,
            "mimeType": self.mime_type,
            "size": len(self.blob),
        }
        if description:
            resource["description"] = description
        if title:
            resource["title"] = title
        return resource

    def as_contents(self) -> Dict[str, Any]:
        contents: Dict[str, Any] = {"uri": self.uri, "mimeType": self.mime_type}
        if self.text is not None:
            contents["text"] = self.text
        else:
            contents["blob"] = base64.b64encode(self.blob).decode("ascii")
        return contents


class SkillCatalog:
    """An immutable snapshot of the skills shipped with the package."""

    def __init__(
        self,
        entries: List[SkillEntry],
        files: Dict[str, SkillFile],
        directories: List[str],
    ) -> None:
        self.entries = tuple(sorted(entries, key=lambda entry: entry.uri))
        self.files = dict(files)
        self.entries_by_uri = {entry.uri: entry for entry in self.entries}
        self.directories = frozenset(directories)

    def list_result(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        start = _cursor_offset(cursor, len(self.entries))
        page = self.entries[start : start + SKILLS_PAGE_SIZE]
        result: Dict[str, Any] = {
            "resultType": "complete",
            "skills": [entry.as_dict() for entry in page],
            "ttlMs": SKILLS_TTL_MS,
            "cacheScope": SKILLS_CACHE_SCOPE,
        }
        next_cursor = start + len(page)
        if next_cursor < len(self.entries):
            result["nextCursor"] = str(next_cursor)
        return result

    def get_result(self, uri: str) -> Dict[str, Any]:
        entry = self.entries_by_uri.get(uri)
        if entry is None:
            raise KeyError(uri)
        return {
            "resultType": "complete",
            "skill": entry.as_dict(),
            "ttlMs": SKILLS_TTL_MS,
            "cacheScope": SKILLS_CACHE_SCOPE,
        }

    def resources_result(self) -> Dict[str, Any]:
        resources = []
        for uri in sorted(self.files):
            file = self.files[uri]
            if uri in self.entries_by_uri:
                frontmatter = self.entries_by_uri[uri].frontmatter
                resources.append(
                    file.as_resource(
                        description=str(frontmatter.get("description", "")),
                        title=str(frontmatter.get("name", "")),
                    )
                )
            else:
                resources.append(file.as_resource())
        return {
            "resultType": "complete",
            "resources": resources,
            "ttlMs": SKILLS_TTL_MS,
            "cacheScope": SKILLS_CACHE_SCOPE,
        }

    def read_result(self, uri: str) -> Dict[str, Any]:
        file = self.files.get(uri)
        if file is None:
            raise KeyError(uri)
        return {
            "resultType": "complete",
            "contents": [file.as_contents()],
            "ttlMs": SKILLS_TTL_MS,
            "cacheScope": SKILLS_CACHE_SCOPE,
        }

    def directory_result(self, uri: str) -> Dict[str, Any]:
        directory = uri.rstrip("/")
        if directory not in self.directories:
            raise KeyError(uri)
        children: Dict[str, Dict[str, Any]] = {}
        prefix = directory + "/"
        for child_uri, file in self.files.items():
            if not child_uri.startswith(prefix):
                continue
            remainder = child_uri[len(prefix) :]
            first, separator, _ = remainder.partition("/")
            name = prefix + first
            if separator:
                children[name] = {
                    "uri": name,
                    "name": first,
                    "mimeType": "inode/directory",
                }
            else:
                children[name] = file.as_resource()
        return {
            "resultType": "complete",
            "resources": [children[name] for name in sorted(children)],
            "ttlMs": SKILLS_TTL_MS,
            "cacheScope": SKILLS_CACHE_SCOPE,
        }


def _cursor_offset(cursor: Optional[str], total: int) -> int:
    if not cursor:
        return 0
    try:
        offset = int(cursor)
    except (TypeError, ValueError):
        return total
    if offset < 0 or offset > total:
        return total
    return offset


def skill_mime_type(name: str) -> str:
    suffix = Path(name).suffix.lower()
    if suffix in (".md", ".markdown"):
        return "text/markdown"
    if suffix == ".json":
        return "application/json"
    if suffix in (".yaml", ".yml"):
        return "application/yaml"
    if suffix == ".txt":
        return "text/plain"
    return "application/octet-stream"


def _is_text(name: str) -> bool:
    mime_type = skill_mime_type(name)
    return mime_type.startswith("text/") or mime_type in ("application/json", "application/yaml")


def parse_frontmatter(text: str) -> Dict[str, Any]:
    """Parse the simple YAML frontmatter used by SKILL.md.

    Supports scalar values and folded/literal block scalars. It intentionally
    does not try to be a general YAML parser: the skill files are part of this
    package, and the values a host verifies are the ones written here.
    """

    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    end = normalized.find("\n---", 4)
    if end < 0:
        raise ValueError("SKILL.md frontmatter is not closed")
    block = normalized[4:end]
    result: Dict[str, Any] = {}
    lines = block.split("\n")
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if line.startswith((" ", "\t")):
            raise ValueError("unexpected indented frontmatter line")
        key, separator, raw = line.partition(":")
        if not separator:
            raise ValueError("frontmatter line without a key/value separator")
        key = key.strip()
        raw = raw.strip()
        if raw in (">", ">-", "|", "|-"):
            index += 1
            parts: List[str] = []
            while index < len(lines):
                candidate = lines[index]
                if candidate.startswith((" ", "\t")):
                    parts.append(candidate.strip())
                    index += 1
                    continue
                if not candidate.strip():
                    parts.append("")
                    index += 1
                    continue
                break
            if raw.startswith(">"):
                result[key] = " ".join(part for part in parts if part)
            else:
                result[key] = "\n".join(parts).rstrip("\n")
            continue
        result[key] = _parse_scalar(raw)
        index += 1
    return result


def _parse_scalar(raw: str) -> Any:
    raw = raw.strip()
    if not raw:
        return ""
    if raw.startswith('"') and raw.endswith('"'):
        try:
            return json.loads(raw)
        except ValueError:
            return raw[1:-1]
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1].replace("''", "'")
    if raw in ("true", "false"):
        return raw == "true"
    if raw in ("null", "~"):
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


def load_catalog(root: Optional[Path] = None) -> SkillCatalog:
    """Load every skill directory under ``root`` (default: packaged skills)."""

    root = Path(root) if root is not None else Path(__file__).resolve().parent / "skills"
    entries: List[SkillEntry] = []
    files: Dict[str, SkillFile] = {}
    directories = set()
    if not root.is_dir():
        return SkillCatalog(entries, files, sorted(directories))

    for skill_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(text)
        name = frontmatter.get("name")
        if not isinstance(name, str) or not _NAME_RE.match(name):
            raise ValueError(f"{skill_md}: frontmatter name is missing or invalid")
        if name != skill_dir.name:
            raise ValueError(f"{skill_md}: frontmatter name {name!r} must equal the directory name")
        if not str(frontmatter.get("description", "")).strip():
            raise ValueError(f"{skill_md}: frontmatter description is required")

        skill_path = "skill://" + skill_dir.name
        directories.add(skill_path)
        resources: List[SkillResource] = []
        for file_path in sorted(path for path in skill_dir.rglob("*") if path.is_file()):
            relative = file_path.relative_to(skill_dir).as_posix()
            uri = skill_path + "/" + relative
            blob = file_path.read_bytes()
            resources.append(
                SkillResource(
                    uri=uri,
                    digest="sha256:" + hashlib.sha256(blob).hexdigest(),
                    size=len(blob),
                )
            )
            files[uri] = SkillFile(
                uri=uri,
                name=Path(relative).name,
                mime_type=skill_mime_type(relative),
                text=blob.decode("utf-8") if _is_text(relative) else None,
                blob=blob,
            )
            parent = uri.rsplit("/", 1)[0]
            while parent.startswith(skill_path):
                directories.add(parent)
                next_parent = parent.rsplit("/", 1)[0]
                if next_parent == parent:
                    break
                parent = next_parent
        entries.append(
            SkillEntry(
                uri=skill_path + "/SKILL.md",
                frontmatter=frontmatter,
                resources=tuple(sorted(resources, key=lambda resource: resource.uri)),
            )
        )
    return SkillCatalog(entries, files, sorted(directories))


@lru_cache(maxsize=1)
def catalog() -> SkillCatalog:
    """The packaged catalog, loaded once per process."""

    return load_catalog()
