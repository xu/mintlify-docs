import json
from pathlib import Path


OPENAPI_FILE = Path(__file__).resolve().parents[1] / "openapi.json"
METHODS = {"get", "post", "put", "delete", "patch"}
LIST_HINTS = ("/list", "/orders", "/fills", "/positions", "/bills", "/balance", "/currencies")
EMPTY_HINTS = ("/login", "/logout", "/update", "/delete", "/transfer", "/create")


def guess_data_schema(path: str, method: str):
    low = path.lower()
    if method == "get" and any(k in low for k in LIST_HINTS):
        return {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": True,
            },
        }, []
    if any(k in low for k in EMPTY_HINTS):
        return {
            "type": "object",
            "nullable": True,
            "additionalProperties": True,
        }, {}
    return {
        "type": "object",
        "additionalProperties": True,
    }, {}


def normalize_servers(openapi_obj: dict):
    for server in openapi_obj.get("servers", []):
        url = server.get("url")
        if isinstance(url, str) and url.startswith("//"):
            server["url"] = f"http:{url}"
        if "description" not in server:
            server["description"] = "测试环境"


def apply_response_examples(openapi_obj: dict) -> int:
    updated = 0
    for path, path_item in openapi_obj.get("paths", {}).items():
        for method, op in path_item.items():
            if method not in METHODS or not isinstance(op, dict):
                continue

            response = op.get("responses", {}).get("200")
            if not isinstance(response, dict):
                continue

            app_json = response.get("content", {}).get("application/json")
            if not isinstance(app_json, dict):
                continue

            schema = app_json.get("schema")
            if not (isinstance(schema, dict) and schema.get("$ref") == "#/components/schemas/model.Response"):
                continue

            data_schema, data_example = guess_data_schema(path, method)
            app_json["schema"] = {
                "type": "object",
                "required": ["code", "data", "message"],
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": data_schema,
                    "message": {"type": "string", "example": "成功"},
                },
            }
            app_json["example"] = {"code": 200, "data": data_example, "message": "成功"}
            updated += 1
    return updated


def main():
    openapi_obj = json.loads(OPENAPI_FILE.read_text(encoding="utf-8"))
    openapi_obj["info"]["title"] = "Dcore 接口文档"
    normalize_servers(openapi_obj)
    updated = apply_response_examples(openapi_obj)
    OPENAPI_FILE.write_text(json.dumps(openapi_obj, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print(f"postprocess done, updated responses: {updated}")


if __name__ == "__main__":
    main()
