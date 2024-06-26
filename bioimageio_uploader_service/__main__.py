import sys
import asyncio
import subprocess
import os
import fire
from loguru import logger

from bioimageio_uploader_service.api import connect_server

__HYPHA_SERVER__ = "https://ai.imjoy.io"
# __HYPHA_SERVER__ = "https://hypha.bioimage.io"
__LOGIN_REQUIRED__ = True


def start(
    host: str = "0.0.0.0",
    port: int = 9000,
    public_base_url: str = "",
    login_required: bool = False,
):
    if login_required:
        os.environ["BIOIMAGEIO_LOGIN_REQUIRED"] = "true"
    else:
        os.environ["BIOIMAGEIO_LOGIN_REQUIRED"] = "false"
    command = [
        sys.executable,
        "-m",
        "hypha.server",
        f"--host={host}",
        f"--port={port}",
        f"--public-base-url={public_base_url}",
        "--startup-functions=bioimageio_uploader_service.api:register_uploader_service",
    ]
    subprocess.run(command)


def connect(
    server_url: str = __HYPHA_SERVER__, login_required: bool = __LOGIN_REQUIRED__
):
    logger.info("Connecting to server at : {}", server_url)
    if login_required:
        os.environ["BIOIMAGEIO_LOGIN_REQUIRED"] = "true"
    else:
        os.environ["BIOIMAGEIO_LOGIN_REQUIRED"] = "false"
    loop = asyncio.get_event_loop()
    loop.create_task(connect_server(server_url))
    loop.run_forever()


def main():
    fire.Fire(
        {
            "start": start,
            "connect": connect,
        }
    )


if __name__ == "__main__":
    main()
