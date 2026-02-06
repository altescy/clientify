from __future__ import annotations

from clientify.generation.client import generate_client
from clientify.generation.profile import GenerationProfile
from clientify.ir import MediaTypeIR, OperationIR, ParameterIR, RequestBodyIR, ResponseIR


class TestGenerateClient:
    def test_generates_sync_and_async(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/users/{id}",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "class SyncClient" in output
        assert "class AsyncClient" in output
        assert "def create" in output
        assert "class ClientError" in output
        assert "class DecodeError" in output
        assert "raise_on_unexpected_status" in output
        assert "TransportError" in output
        assert "def get" in output
        assert "async def get" in output

    def test_generates_literal_path_and_params(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/users/{id}",
                operation_id=None,
                parameters=[
                    ParameterIR(
                        name="id",
                        location="path",
                        required=True,
                        schema={"type": "integer"},
                        content=[],
                        style=None,
                        explode=None,
                        default=None,
                    )
                ],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/json", schema={"type": "integer"})],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "Literal['/users/{id}']" in output
        assert "GetUsersIdPathParams = TypedDict(" in output
        assert "'id': Required[int]" in output
        assert "GetUsersIdResponse" in output
        assert "GetUsersIdAsyncResponse" in output

    def test_generates_request_body_union(self) -> None:
        operations = [
            OperationIR(
                method="post",
                path="/events",
                operation_id=None,
                parameters=[],
                request_body=RequestBodyIR(
                    required=False,
                    content=[
                        MediaTypeIR(
                            content_type="application/json",
                            schema={"type": "object", "properties": {"name": {"type": "string"}}},
                        ),
                        MediaTypeIR(content_type="text/plain", schema={"type": "string"}),
                    ],
                ),
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/json", schema={"type": "string"})],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "body:" in output
        assert "dict[str, object] | str | None" in output
        assert "content_type: Literal['application/json', 'text/plain']" in output

    def test_generates_expected_statuses(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/status",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/json", schema={"type": "string"})],
                    ),
                    ResponseIR(
                        status="404",
                        description="missing",
                        content=[MediaTypeIR(content_type="application/json", schema={"type": "string"})],
                    ),
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "expected_statuses: set[str] | None" in output
        assert "EXPECTED_STATUSES" in output

    def test_default_status_skips_expected_statuses(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/default",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="default",
                        description="any",
                        content=[MediaTypeIR(content_type="application/json", schema={"type": "string"})],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "('/default'" not in output

    def test_generates_accept_and_request_content_maps(self) -> None:
        operations = [
            OperationIR(
                method="post",
                path="/submit",
                operation_id=None,
                parameters=[],
                request_body=RequestBodyIR(
                    required=True,
                    content=[MediaTypeIR(content_type="application/json", schema={"type": "object"})],
                ),
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="text/plain", schema={"type": "string"})],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "ACCEPT_TYPES" in output
        assert "REQUEST_CONTENT_TYPES" in output

    def test_generates_accept_literal_when_multiple_response_types(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/reports",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[
                            MediaTypeIR(content_type="application/json", schema={"type": "object"}),
                            MediaTypeIR(content_type="text/plain", schema={"type": "string"}),
                        ],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "'accept': Literal['application/json', 'text/plain']" in output
        assert "timeout: float | None" in output

    def test_empty_json_schema_uses_json_value(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/empty",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/json", schema={})],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[JsonValue]" in output
