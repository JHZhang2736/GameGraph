from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes_import import router
from app.api.routes_opportunity import router as opportunity_router
from app.api.routes_profile import router as profile_router
from app.services.fixture_pipeline import ContractViolation

app = FastAPI(title="GameGraph Import API")
app.include_router(router)
app.include_router(profile_router)
app.include_router(opportunity_router)


@app.exception_handler(ContractViolation)
async def contract_violation_handler(
    request: Request, exc: ContractViolation
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})
