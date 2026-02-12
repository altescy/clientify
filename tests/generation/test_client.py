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
        assert "dict[str, JsonValue] | str | None" in output
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

    def test_json_without_schema_uses_json_value(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/data",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/json", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[JsonValue]" in output

    def test_plus_json_content_type_uses_json_value(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/custom",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/vnd.api+json", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[JsonValue]" in output

    def test_ndjson_response_uses_iterator_json_value(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/stream",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/x-ndjson", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[Iterator[JsonValue]]" in output
        assert "SuccessResponse[AsyncIterator[JsonValue]]" in output

    def test_stream_json_response_uses_iterator_json_value(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/stream2",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/stream+json", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[Iterator[JsonValue]]" in output
        assert "SuccessResponse[AsyncIterator[JsonValue]]" in output

    def test_text_plain_response_uses_str(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/text",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="text/plain", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[str]" in output

    def test_text_csv_response_uses_str(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/csv",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="text/csv", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[str]" in output

    def test_form_urlencoded_response_uses_str(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/form",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/x-www-form-urlencoded", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[str]" in output

    def test_unknown_content_type_without_schema_uses_object(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/unknown",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/x-custom", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[object]" in output

    def test_request_body_with_json_without_schema_uses_json_value(self) -> None:
        operations = [
            OperationIR(
                method="post",
                path="/data",
                operation_id=None,
                parameters=[],
                request_body=RequestBodyIR(
                    required=True,
                    content=[MediaTypeIR(content_type="application/json", schema=None)],
                ),
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/json", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "body: JsonValue" in output

    def test_request_body_with_ndjson_uses_iterator_json_value(self) -> None:
        operations = [
            OperationIR(
                method="post",
                path="/stream",
                operation_id=None,
                parameters=[],
                request_body=RequestBodyIR(
                    required=True,
                    content=[MediaTypeIR(content_type="application/x-ndjson", schema=None)],
                ),
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/json", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "body: Iterator[JsonValue]" in output

    def test_request_body_with_text_plain_uses_str(self) -> None:
        operations = [
            OperationIR(
                method="post",
                path="/text",
                operation_id=None,
                parameters=[],
                request_body=RequestBodyIR(
                    required=True,
                    content=[MediaTypeIR(content_type="text/plain", schema=None)],
                ),
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/json", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "body: str" in output

    def test_ndjson_with_schema_uses_iterator_of_type(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/users-stream",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[
                            MediaTypeIR(
                                content_type="application/x-ndjson",
                                schema={
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "name": {"type": "string"},
                                    },
                                },
                            )
                        ],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[Iterator[dict[str, JsonValue]]]" in output
        assert "SuccessResponse[AsyncIterator[dict[str, JsonValue]]]" in output

    def test_ndjson_with_ref_schema_uses_iterator_of_model(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/pets-stream",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[
                            MediaTypeIR(
                                content_type="application/x-ndjson",
                                schema={"$ref": "#/components/schemas/Pet"},
                            )
                        ],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["Pet"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[Iterator[Pet]]" in output
        assert "SuccessResponse[AsyncIterator[Pet]]" in output

    def test_stream_json_with_schema_uses_iterator_of_type(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/events-stream",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[
                            MediaTypeIR(
                                content_type="application/stream+json",
                                schema={"type": "string"},
                            )
                        ],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[Iterator[str]]" in output
        assert "SuccessResponse[AsyncIterator[str]]" in output

    def test_request_body_ndjson_with_schema_uses_iterator_of_type(self) -> None:
        operations = [
            OperationIR(
                method="post",
                path="/upload-stream",
                operation_id=None,
                parameters=[],
                request_body=RequestBodyIR(
                    required=True,
                    content=[
                        MediaTypeIR(
                            content_type="application/x-ndjson",
                            schema={"$ref": "#/components/schemas/Event"},
                        )
                    ],
                ),
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/json", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["Event"], GenerationProfile.from_version("3.14")).code
        assert "body: Iterator[Event]" in output

    def test_json_schema_without_type_uses_json_value(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/data",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[
                            MediaTypeIR(
                                content_type="application/json",
                                schema={"description": "Some data without type field"},
                            )
                        ],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[JsonValue]" in output

    def test_ndjson_schema_without_type_uses_iterator_json_value(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/stream",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[
                            MediaTypeIR(
                                content_type="application/x-ndjson",
                                schema={"description": "Stream without type field"},
                            )
                        ],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[Iterator[JsonValue]]" in output
        assert "SuccessResponse[AsyncIterator[JsonValue]]" in output

    def test_xml_response_uses_str(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/xml-data",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/xml", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[str]" in output

    def test_text_xml_response_uses_str(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/xml-data2",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="text/xml", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[str]" in output

    def test_plus_xml_response_uses_str(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/xml-data3",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/atom+xml", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[str]" in output

    def test_html_response_uses_str(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/html-page",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="text/html", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[str]" in output

    def test_yaml_response_uses_json_value(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/yaml-config",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/yaml", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[JsonValue]" in output

    def test_image_response_uses_bytes(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/image",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="image/png", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[bytes]" in output

    def test_video_response_uses_bytes(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/video",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="video/mp4", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[bytes]" in output

    def test_audio_response_uses_bytes(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/audio",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="audio/mpeg", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[bytes]" in output

    def test_pdf_response_uses_bytes(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/document",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[MediaTypeIR(content_type="application/pdf", schema=None)],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "SuccessResponse[bytes]" in output

    def test_nested_object_without_properties_uses_json_value(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/nested",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[
                            MediaTypeIR(
                                content_type="application/json",
                                schema={
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "metadata": {"type": "object"},
                                    },
                                },
                            )
                        ],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        assert "dict[str, JsonValue]" in output

    def test_array_of_any_uses_json_value(self) -> None:
        operations = [
            OperationIR(
                method="get",
                path="/array-any",
                operation_id=None,
                parameters=[],
                request_body=None,
                responses=[
                    ResponseIR(
                        status="200",
                        description="ok",
                        content=[
                            MediaTypeIR(
                                content_type="application/json",
                                schema={
                                    "type": "object",
                                    "properties": {
                                        "items": {
                                            "type": "array",
                                        },
                                    },
                                },
                            )
                        ],
                    )
                ],
                extensions={},
            )
        ]
        output = generate_client(operations, ["User"], GenerationProfile.from_version("3.14")).code
        # Inline schemas are treated as dict[str, JsonValue]
        assert "dict[str, JsonValue]" in output
