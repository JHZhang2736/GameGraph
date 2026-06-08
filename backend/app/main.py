from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes_graph import router as graph_router
from app.api.routes_import import router
from app.api.routes_profile import router as profile_router
from app.services.fixture_pipeline import ContractViolation

app = FastAPI(title="GameGraph Import API")

# 允许前端(Next dev server)跨域访问。来源用 FRONTEND_ORIGINS 环境变量配置
# (逗号分隔),默认本地开发端口。
_origins = [
    origin.strip()
    for origin in os.environ.get(
        "FRONTEND_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(profile_router)
app.include_router(graph_router)


@app.exception_handler(ContractViolation)
async def contract_violation_handler(
    request: Request, exc: ContractViolation
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})
