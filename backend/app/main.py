from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes_graph import router as graph_router
from app.api.routes_import import router
from app.api.routes_opportunity import router as opportunity_router
from app.api.routes_profile import router as profile_router
from app.services.fixture_pipeline import ContractViolation

app = FastAPI(title="GameGraph Import API")

# 允许前端跨域访问。本地任意端口(localhost / 127.0.0.1,含 dev 的 3000 与
# docker-compose 暴露的 3100)由正则放行;生产部署的具体来源(如公网 IP/域名)
# 用 FRONTEND_ORIGINS 环境变量(逗号分隔)显式追加。
_origins = [
    origin.strip()
    for origin in os.environ.get("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(profile_router)
app.include_router(graph_router)
app.include_router(opportunity_router)


@app.exception_handler(ContractViolation)
async def contract_violation_handler(
    request: Request, exc: ContractViolation
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})
