import json
import uuid
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from httpx import Response


def generic_http_call(
    mocked_user_client: TestClient,
    endpoint: str,
    method: str,
    data: dict[str, Any] | None = None,
    expected_status_code: int = 201,
) -> Any | None:
    fn: Callable[..., Response] = getattr(mocked_user_client, method)

    if method in ("get", "delete"):
        response = fn(endpoint)
    else:
        response = fn(endpoint, json=data)

    response_data: Any | None = None
    if response.status_code == 204:
        response_data = None
    else:
        try:
            response_data = response.json()
        except json.decoder.JSONDecodeError:
            response_data = None

    assert (
        response.status_code == expected_status_code
    ), f"({method}, {endpoint}) Expected status code {expected_status_code}, got {response.status_code} with response: {response_data}"

    return response_data


def bp_for_test(
    id_: str | None = None,
    relations: dict[str, Any] | None = None,
    reference_properties: dict[str, Any] | None = None,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    return {
        "id": id_ or str(uuid.uuid4()),
        "title": title or "blueprint-for-my-services",
        "description": description
        or "A blueprint that will hold the definition for a service on company mycompany.com",
        "schemaProperties": {
            "title": "blueprint properties",
            "type": "object",
            "properties": {
                "someString": {"type": "string", "title": "Some string Property of my service"},
                "someObject": {
                    "type": "object",
                    "title": "Some object Property of my service",
                    "format": "test",
                    "properties": {"field1": {"type": "string"}, "field2": {"type": "string"}},
                },
                "someNumber": {"type": "number", "title": "Some Property"},
                "someBoolean": {"type": "boolean", "title": "Some Property"},
                "someArray": {
                    "type": "array",
                    "title": "Some Property",
                    "items": {"title": "Some List Property of my service", "type": "number"},
                },
                "someDatetime": {
                    "type": "string",
                    "title": "Some Datetime Property of my service",
                    "format": "date-time",
                },
                "someExtraField": {"type": "string", "title": "some extra field"},
            },
        },
        "relations": relations or {},
        "referenceProperties": reference_properties or {},
    }


def entity_for_test(
    id_: str | None = None,
    blueprint_id: str | None = None,
    relations: dict[str, Any] | None = None,
    extra_properties: dict[str, Any] | None = None,
    sources: dict[str, Any] | None = None,
    **kwargs,
) -> dict[str, Any]:
    return {
        "id": id_ or str(uuid.uuid4()),
        "title": "entity-for-my-services",
        "blueprintId": blueprint_id or str(uuid.uuid4()),
        "description": "An entity that will hold the definition for a service on company mycompany.com",
        "properties": {
            "someString": "abc",
            "someObject": {"field1": "abc", "field2": "abc"},
            "someNumber": 1,
            "someBoolean": True,
            "someArray": [1, 2, 3],
            "someDatetime": "2022-01-01T00:00:00Z",
            "someExtraField": None,
            **(extra_properties or {}),
        },
        "relations": relations or {},
        "sources": sources or {},
    } | kwargs


def scorecard_for_test(
    blueprint_id: str,
    extra_bronze_rules: list[dict] | None = None,
    extra_silver_rules: list[dict] | None = None,
    extra_gold_rules: list[dict] | None = None,
) -> dict[str, Any]:
    extra_bronze_rules = extra_bronze_rules or []
    extra_silver_rules = extra_silver_rules or []
    extra_gold_rules = extra_gold_rules or []
    return {
        "title": "Scorecard for testing",
        "description": "This scorecard is used to test scorecards",
        "isActive": True,
        "blueprintId": blueprint_id,
        "medianRank": "noData",
        "ranks": [
            {
                "id": "bronze",
                "rules": [
                    {
                        "id": "some-string-exists",
                        "title": "Some string exists",
                        "description": "The Service must have a string property",
                        "conditions": [{"field": "data.properties.someString", "operator": "neq", "value": None}],
                    },
                    *extra_bronze_rules,
                ],
            },
            {
                "id": "silver",
                "rules": [
                    {
                        "id": "some-number-is-1",
                        "title": "Some number is 1",
                        "description": "The Service must have a number property set to 1",
                        "conditions": [{"field": "data.properties.someNumber", "operator": "eq", "value": 1}],
                    },
                    *extra_silver_rules,
                ],
            },
            {
                "id": "gold",
                "rules": [
                    {
                        "id": "some-boolean-is-true",
                        "title": "Some boolean is true",
                        "description": "The Service must have a boolean property set to true",
                        "conditions": [{"field": "data.properties.someBoolean", "operator": "eq", "value": True}],
                    },
                    *extra_gold_rules,
                ],
            },
        ],
    }


def suggestion_for_test(
    id_: str | None = None,
    title: str = "Suggestion Title",
    description: str | None = None,
    origin_type: str = "automation",
    origin_id: str = "origin.example.id",
    source_type: str = "entity",
    source_id: str = "source.example.id",
    source_context: dict[str, Any] | None = None,
    target_type: str = "entity",
    target_id: str = "target.example.id",
    target_context: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    ignored: bool = False,
    auto_apply: bool = False,
) -> dict[str, Any]:
    return {
        "id": id_ or str(uuid.uuid4()),
        "title": title,
        "description": description,
        "originType": origin_type,
        "originId": origin_id,
        "sourceType": source_type,
        "sourceId": source_id,
        "sourceContext": source_context or {"blueprintId": "source.blueprint.id"},
        "targetType": target_type,
        "targetId": target_id,
        "targetContext": target_context or {"blueprintId": "target.blueprint.id"},
        "data": data
        or {
            "id": target_id,
            "title": "Target Entity Title",
            "properties": {},
            "blueprintId": "target.blueprint.id",
            "description": "Example description for the target entity",
        },
        "ignored": ignored,
        "autoApply": auto_apply,
    }


def automation_for_test(
    id_: str | None = None,
    title: str = "GitLab Repository to Service",
    description: str = "This automation creates a service from a GitLab repository",
    source_blueprint_id: str = "gitlab.v1.repository",
    target_blueprint_id: str = "service",
    is_active: bool = True,
    order: int = 0,
    triggers: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
    tags: list[dict[str, str]] | None = None,
) -> dict:
    if triggers is None:
        triggers = [
            {
                "type": "onEvent",
                "conditions": [
                    {"field": "data.blueprintId", "operator": "eq", "value": "{{ arguments.sourceBlueprintId }}"}
                ],
                "event": {"resource": "entity", "action": ["create", "update"]},
            }
        ]

    if actions is None:
        actions = [
            {
                "type": "upsertResource",
                "args": {
                    "data": {
                        "id": "{{ data.id }}.service",
                        "title": "Service {{ data.title }}",
                        "relations": {"GitlabRepository": {"value": "{{ data.id }}"}},
                        "properties": {
                            "readme": "{{ data.properties.readme }}",
                            "language": "{{ data.properties.languages[0] }}",
                            "repo-link": "{{ data.properties.url }}",
                        },
                        "blueprintId": "{{ arguments.targetBlueprintId }}",
                        "description": "{{ data.properties.description }}",
                    },
                    "resourceType": "entity",
                    "createSuggestion": True,
                },
            }
        ]

    if tags is None:
        tags = [{"key": "default", "value": "true"}, {"key": "owner", "value": "rely"}]

    return {
        "id": id_ or str(uuid.uuid4()),
        "title": title,
        "description": description,
        "isActive": is_active,
        "order": order,
        "type": "automation",
        "arguments": {"sourceBlueprintId": source_blueprint_id, "targetBlueprintId": target_blueprint_id},
        "triggers": triggers,
        "actions": actions,
        "outputs": {},
        "tags": tags,
    }
