from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

from pathlib import Path

from swagger_ui_bundle import swagger_ui_3_path

from app.config.settings import get_settings
from .api.routes_story import router as story_router
from .api.routes_tasks import router as tasks_router
from .api.routes_config import router as config_router
from .api.routes_assets import router as assets_router
from .api.routes_storage import router as storage_router
from .api.routes_style_presets import router as style_presets_router
from .api.routes_subtitle_styles import router as subtitle_styles_router
from .api.routes_runninghub import router as runninghub_router
from .api.routes_gemini_console import router as gemini_console_router
from .utils.timezone import apply_timezone_settings

apply_timezone_settings()

app = FastAPI(title='Aistory Backend', docs_url=None, redoc_url=None, openapi_version='3.0.3')
app.openapi_version = '3.0.3'

settings = get_settings()
cors_allow_origins = list(settings.cors_allow_origins)

if settings.API_HOST and settings.API_PORT and settings.API_HOST not in ('0.0.0.0', '::'):
    inferred_origin = f"http://{settings.API_HOST}:{settings.API_PORT}"
    if inferred_origin not in cors_allow_origins:
        cors_allow_origins.append(inferred_origin)

BASE_DIR = Path(__file__).resolve().parent
REDOC_STATIC_DIR = BASE_DIR / 'static' / 'redoc'

if REDOC_STATIC_DIR.exists():
    app.mount('/redoc-static', StaticFiles(directory=REDOC_STATIC_DIR), name='redoc-static')
    REDOC_JS_URL = '/redoc-static/redoc.standalone.js'
else:
    REDOC_JS_URL = 'https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js'

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(story_router)
app.include_router(tasks_router)
app.include_router(config_router)
app.include_router(assets_router)
app.include_router(storage_router)
app.include_router(style_presets_router)
app.include_router(subtitle_styles_router)
app.include_router(runninghub_router)
app.include_router(gemini_console_router)

app.mount('/swagger-ui', StaticFiles(directory=swagger_ui_3_path), name='swagger-ui')

@app.get('/')
def health():
    return {'status': 'ok'}


@app.get('/docs', include_in_schema=False)
def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url='/swagger-ui/swagger-ui-bundle.js',
        swagger_css_url='/swagger-ui/swagger-ui.css',
        swagger_ui_parameters={'defaultModelsExpandDepth': -1},
        swagger_favicon_url='/swagger-ui/favicon-32x32.png'
    )


@app.get('/redoc', include_in_schema=False)
def custom_redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url=REDOC_JS_URL
    )

if __name__ == '__main__':
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        'app.main:app',
        host=(settings.API_HOST or '127.0.0.1'),
        port=(settings.API_PORT or 8000),
        reload=(settings.DEBUG if settings.DEBUG is not None else True),
    )
