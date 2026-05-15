"""Application metadata routes."""

import json
from datetime import datetime

from fastapi import APIRouter

router = APIRouter(prefix="/app", tags=["meta"])


@router.get("/version")
def get_version():
    try:
        with open("package.json", "r", encoding="utf-8") as file:
            version = json.load(file).get("version", "2.0.0")
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        version = "2.0.0"
    return {
        "version": version,
        "build_date": datetime.now().strftime("%Y-%m-%d"),
        "api_version": "2.0.0",
    }
