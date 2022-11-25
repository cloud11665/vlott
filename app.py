from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse

import versions.v1
import versions.v2

app = FastAPI()
app.add_middleware(CORSMiddleware,
	allow_credentials = True,
	allow_origins = ["*"],
	allow_methods = ["*"],
	allow_headers = ["*"])
app.add_middleware(GZipMiddleware,
	minimum_size = 4096)

app.include_router(versions.v1.router, prefix="/v1", tags=["v1"])
app.include_router(versions.v2.router, prefix="/v2", tags=["v2"])
# app.include_router(versions.v2.router, prefix="", tags=["default"])

@app.get("/", include_in_schema=False)
async def redirect():
	return RedirectResponse("/docs")
