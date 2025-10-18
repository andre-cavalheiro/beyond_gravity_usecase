import uvicorn

from fury_api.lib.settings import config

uvicorn.run(
    workers=config.server.WORKERS,
    app=config.server.APP_PATH,
    host=config.server.HOST,
    port=config.server.PORT,
    reload=config.server.RELOAD,
    reload_dirs=config.server.RELOAD_DIRS,
    timeout_keep_alive=config.server.KEEPALIVE,
)
