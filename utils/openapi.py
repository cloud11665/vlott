from typing import Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse

def build_docs(
    app: FastAPI,
    prefix: str,
    tags: List[str],
	title: str,
    custom_openapi: Dict[str, str] = {},
) -> None:
    async def get_openapi(request: Request):
        nonlocal custom_openapi
        if prefix not in custom_openapi:
            custom_openapi[prefix] = request.app.openapi()

            # Remove not valid tags on openapi schema.
            for path in custom_openapi[prefix]["paths"].copy():
                for method in custom_openapi[prefix]["paths"][path].copy():
                    _tags = custom_openapi[prefix]["paths"][path][method]["tags"]
                    if not set(_tags).issuperset(set(tags)):
                        del custom_openapi[prefix]["paths"][path][method]

            # Clean empty paths.
            for path in custom_openapi[prefix]["paths"].copy():
                if not custom_openapi[prefix]["paths"][path]:
                    del custom_openapi[prefix]["paths"][path]
        return custom_openapi[prefix]

    get_openapi.__name__ = get_openapi.__name__ + prefix
    app.add_api_route(prefix + "/openapi.json", get_openapi, include_in_schema=False)

    async def get_redoc() -> HTMLResponse:
        return get_redoc_html(
            openapi_url=prefix + "/openapi.json", title="Developer Documentation"
        )

    get_redoc.__name__ = get_redoc.__name__ + prefix
    app.add_api_route(prefix + "/redoc", get_redoc, include_in_schema=False)

    async def swagger_ui_html(req: Request) -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url=prefix + "/openapi.json",
            title=title + " - Swagger UI",
            # oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            # init_oauth=app.swagger_ui_init_oauth,
        )

    swagger_ui_html.__name__ = swagger_ui_html.__name__ + prefix
    app.add_api_route(prefix + "/docs", swagger_ui_html, include_in_schema=False)
