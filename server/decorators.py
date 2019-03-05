from jsonschema import validate, ValidationError, draft7_format_checker
from werkzeug.exceptions import *
from functools import wraps
from flask import (
    current_app,
    jsonify,
    request,
)


def validate_json(f):
    @wraps(f)
    def wrapper(*args, **kw):
        try:
            request.json
        except BadRequest as e:
            msg = "payload must be a valid json"
            return jsonify({"error": msg}), 400
        return f(*args, **kw)

    return wrapper


def validate_schema(schema):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kw):
            try:
                a = validate(
                    instance=request.json,
                    schema=schema,
                    format_checker=draft7_format_checker)
            except ValidationError as e:
                return jsonify({"msg": e.message}), 400
            return f(*args, **kw)

        return wrapper

    return decorator
