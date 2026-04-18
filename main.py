import csv
import io
import json
import os
import secrets
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(title="MQM Translation Checker")

# Allow local file/front-end access during practice use.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()


def verify_credentials(
    credentials: HTTPBasicCredentials = Depends(security),
) -> str:
    expected_user = os.getenv("APP_USER")
    expected_password = os.getenv("APP_PASSWORD")
    if not expected_user or not expected_password:
        raise HTTPException(
            status_code=500,
            detail="APP_USER / APP_PASSWORD is not set on the server.",
        )

    user_ok = secrets.compare_digest(credentials.username, expected_user)
    pass_ok = secrets.compare_digest(credentials.password, expected_password)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


class ReviewRequest(BaseModel):
    source_text: str = Field(..., min_length=1)
    target_text: str = Field(..., min_length=1)
    purpose: str = "社内情報共有"
    audience: str = "ITエンジニア"
    tone: str = "自然で明確"
    terminology_policy: str = "特になし"
    priority: str = "内容把握とAccuracy重視"


# Strict JSON Schema for Structured Outputs.
MQM_REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "assumptions": {
            "type": "object",
            "properties": {
                "purpose": {"type": "string"},
                "audience": {"type": "string"},
                "tone": {"type": "string"},
                "terminology_policy": {"type": "string"},
                "priority": {"type": "string"},
            },
            "required": [
                "purpose",
                "audience",
                "tone",
                "terminology_policy",
                "priority",
            ],
            "additionalProperties": False,
        },
        "summary": {
            "type": "object",
            "properties": {
                "overall": {"type": "string"},
                "critical_count": {"type": "integer"},
                "major_count": {"type": "integer"},
                "minor_count": {"type": "integer"},
                "top_priority": {"type": "string"},
            },
            "required": [
                "overall",
                "critical_count",
                "major_count",
                "minor_count",
                "top_priority",
            ],
            "additionalProperties": False,
        },
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_span": {"type": "string"},
                    "target_span": {"type": "string"},
                    "mqm_category": {
                        "type": "string",
                        "enum": [
                            "Accuracy",
                            "Linguistic Conventions",
                            "Terminology",
                            "Style",
                            "Locale Conventions",
                        ],
                    },
                    "sub_category": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["Critical", "Major", "Minor"],
                    },
                    "reason": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
                "required": [
                    "source_span",
                    "target_span",
                    "mqm_category",
                    "sub_category",
                    "severity",
                    "reason",
                    "suggestion",
                ],
                "additionalProperties": False,
            },
        },
        "revised_translation": {"type": "string"},
    },
    "required": ["assumptions", "summary", "issues", "revised_translation"],
    "additionalProperties": False,
}


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in .env")
    return OpenAI(api_key=api_key)


def build_prompt(payload: ReviewRequest) -> str:
    return f"""
あなたはMQMに基づく翻訳品質レビュー担当者である。
原文と訳文を比較してレビューする。
目的、読者、文体、用語方針、重視点を前提として使う。
誤りと好みの違いを区別する。
Accuracyを最優先する。
MQMカテゴリは Accuracy / Linguistic Conventions / Terminology / Style / Locale Conventions を使う。
重大度は Critical / Major / Minor の3段階のみを使う。
問題ごとに理由と修正案を返す。
問題がない場合は issues を空配列にする。
訳文だけを見て推測で批判してはいけない。必ず原文と比較して判断する。
ITエンジニア向け社内文書のレビューであり、「最低限内容が把握できること」と「Accuracy優先」を重視する。

[レビュー前提]
- purpose: {payload.purpose}
- audience: {payload.audience}
- tone: {payload.tone}
- terminology_policy: {payload.terminology_policy}
- priority: {payload.priority}

[原文]
{payload.source_text}

[訳文]
{payload.target_text}

上記を踏まえて、指定のJSON Schemaに厳密に従って日本語で返答すること。
summary は全体評価と件数を簡潔にまとめること。
revised_translation には、必要に応じて修正後の全訳文を入れること。問題がなければ自然な現状訳を入れること。
""".strip()


def request_review(payload: ReviewRequest) -> dict[str, Any]:
    client = get_client()

    response = client.responses.create(
        model="gpt-4o-mini",
        store=False,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a precise MQM-based translation reviewer. "
                    "Return only schema-compliant JSON."
                ),
            },
            {"role": "user", "content": build_prompt(payload)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "mqm_review_result",
                "strict": True,
                "schema": MQM_REVIEW_SCHEMA,
            }
        },
    )

    if not getattr(response, "output_text", None):
        raise RuntimeError("OpenAI response did not include structured output text.")

    return json.loads(response.output_text)


def build_csv(issues: list[dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "source_span",
            "target_span",
            "mqm_category",
            "sub_category",
            "severity",
            "reason",
            "suggestion",
        ]
    )

    for issue in issues:
        writer.writerow(
            [
                issue.get("source_span", ""),
                issue.get("target_span", ""),
                issue.get("mqm_category", ""),
                issue.get("sub_category", ""),
                issue.get("severity", ""),
                issue.get("reason", ""),
                issue.get("suggestion", ""),
            ]
        )

    return output.getvalue()


@app.post("/review")
def review_translation(
    payload: ReviewRequest,
    _: str = Depends(verify_credentials),
) -> JSONResponse:
    try:
        result = request_review(payload)
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/review/csv")
def review_translation_csv(
    payload: ReviewRequest,
    _: str = Depends(verify_credentials),
) -> Response:
    try:
        result = request_review(payload)
        csv_text = build_csv(result.get("issues", []))
        # Excel opens UTF-8 CSV more reliably when a BOM is present.
        csv_bytes = ("\ufeff" + csv_text).encode("utf-8")
        headers = {"Content-Disposition": "attachment; filename=mqm_review.csv"}
        return Response(content=csv_bytes, media_type="text/csv", headers=headers)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
