from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes_graph import router as graph_router
from app.api.routes_import import router
from app.api.routes_concept import router as concept_router
from app.api.routes_opportunity import router as opportunity_router
from app.api.routes_profile import router as profile_router
from app.services.fixture_pipeline import ContractViolation

# 本地直接跑(uvicorn / pytest)时,把 backend/.env 读进 os.environ,这样 LLM_* 等
# 配置无需手动 export 或加 --env-file。override=False:docker(env_file)或 shell 注入
# 的真实变量始终优先;文件不存在(如容器镜像内)则是无副作用的 no-op。路由模块只在
# 请求时惰性读取环境变量,故此处在建 app 前加载已足够早。
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

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
app.include_router(concept_router)


@app.exception_handler(ContractViolation)
async def contract_violation_handler(
    request: Request, exc: ContractViolation
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})
