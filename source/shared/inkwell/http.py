import base64
import binascii
import functools
import json
import logging
import os

MAX_BODY_BYTES = 4096

log = logging.getLogger()
log.setLevel(logging.INFO)


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def respond(status, body=None, cache="no-store"):
    headers = {"Content-Type": "application/json", "Cache-Control": cache}
    origin = os.environ.get("ALLOWED_ORIGIN")
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Vary"] = "Origin"
    return {
        "statusCode": status,
        "headers": headers,
        "body": "" if body is None else json.dumps(body),
    }


def api_handler(fn):
    @functools.wraps(fn)
    def wrapper(event, context):
        try:
            return fn(event, context)
        except ApiError as err:
            return respond(err.status, {"error": {"code": err.code, "message": err.message}})
        except Exception:
            log.exception("Unhandled error")
            return respond(500, {"error": {"code": "INTERNAL", "message": "Something went wrong"}})

    return wrapper


def user_id(event):
    claims = ((event.get("requestContext") or {}).get("authorizer") or {}).get("claims") or {}
    sub = claims.get("sub")
    if not sub:
        raise ApiError(401, "UNAUTHORIZED", "Missing identity")
    return sub


def header(event, name):
    wanted = name.lower()
    for key, value in (event.get("headers") or {}).items():
        if key.lower() == wanted:
            return value
    return None


def path_param(event, name):
    return (event.get("pathParameters") or {}).get(name)


def query_param(event, name):
    return (event.get("queryStringParameters") or {}).get(name)


def json_body(event):
    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        try:
            raw = base64.b64decode(raw, validate=True).decode("utf-8", errors="replace")
        except binascii.Error:
            raise ApiError(400, "INVALID_JSON", "Request body must be valid JSON") from None
    if len(raw.encode("utf-8")) > MAX_BODY_BYTES:
        raise ApiError(413, "TOO_LARGE", f"Request body must be at most {MAX_BODY_BYTES} bytes")
    try:
        data = json.loads(raw)
    except ValueError:
        raise ApiError(400, "INVALID_JSON", "Request body must be valid JSON") from None
    if not isinstance(data, dict):
        raise ApiError(400, "INVALID_JSON", "Request body must be a JSON object")
    return data
