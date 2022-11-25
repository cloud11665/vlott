import os

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import StreamingResponse
from starlette.background import BackgroundTask
import httpx

router = APIRouter(tags = ["v1"])

client = httpx.AsyncClient(base_url="http://"+os.environ["VLOTT_LEGACY_ADDR"])

async def legacy_proxy(req: Request):
	url = httpx.URL(path=req.url.path[3:], query=req.url.query.encode("utf-8"))
	rp_req = client.build_request(
		req.method, url,
		headers=req.headers.raw,
		content=await req.body()
	)
	rp_resp = await client.send(rp_req, stream=True)
	return StreamingResponse(
		rp_resp.aiter_text(),
		status_code=rp_resp.status_code,
		headers=rp_resp.headers,
		background=BackgroundTask(rp_resp.aclose)
	)

router.add_route("/{path:path}", legacy_proxy, ["GET"])
