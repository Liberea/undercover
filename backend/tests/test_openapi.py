from backend.main import app


def operations():
    for path, methods in app.openapi()["paths"].items():
        for method, operation in methods.items():
            yield f"{method.upper()} {path}", operation


def body_schema(operation):
    content = operation.get("requestBody", {}).get("content", {})
    ref = content.get("application/json", {}).get("schema", {}).get("$ref")
    return ref and app.openapi()["components"]["schemas"][ref.split("/")[-1]]


def test_every_operation_has_an_id_and_one_line_docstring():
    for name, operation in operations():
        assert operation.get("operationId"), name
        assert operation.get("description"), name
        assert "\n" not in operation["description"], name


def test_no_optional_inputs():
    for name, operation in operations():
        for parameter in operation.get("parameters", []):
            assert parameter["required"], f"{name} {parameter['name']}"
        schema = body_schema(operation)
        if schema:
            assert set(schema.get("required", [])) == set(schema["properties"]), name
