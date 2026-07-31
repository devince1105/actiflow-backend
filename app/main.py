# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import JSONResponse
from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import ActiFlowBusinessException

app = FastAPI(
    title="ActiFlow Backend",
    version="1.0.0",
)

@app.exception_handler(ActiFlowBusinessException)
async def actiflow_business_exception_handler(request, exc: ActiFlowBusinessException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "detail": exc.detail,
        },
    )

# ------------------------------------------------------------
# CORS 設定
# ------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------
# 掛上正式 API
# ------------------------------------------------------------
app.include_router(api_router)

# ------------------------------------------------------------
# Debug API（只在 dev 掛載）
# ------------------------------------------------------------
if settings.ENV == "dev":
    from app.api.utils.debug import router as debug_router
    app.include_router(debug_router)

# ------------------------------------------------------------
# Health / Root
# ------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "ActiFlow API is running!"}
