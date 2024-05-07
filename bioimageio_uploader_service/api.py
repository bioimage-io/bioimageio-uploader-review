import datetime
import json
import os
import traceback
from typing import Any
from functools import wraps
from dataclasses import dataclass, field, InitVar
from enum import IntEnum, auto, Enum

import requests
from imjoy_rpc.hypha import connect_to_server, login
from loguru import logger

from bioimageio_collection_backoffice._backoffice import BackOffice
from bioimageio_uploader_service import __version__
from bioimageio.spec import validate_format, ValidationContext

class MissingEnvironmentVariable(Exception):
    pass

CONNECTION_VARS = {"host": "S3_HOST", "bucket": "S3_BUCKET", "prefix": "S3_PREFIX"}
if not set(os.environ).issuperset(CONNECTION_VARS.values()):
    logger.error("Must be run with following env vars: {}", ", ".join(CONNECTION_VARS.values()))
    missing = [var for var in CONNECTION_VARS.values() if var not in os.environ]
    raise MissingEnvironmentVariable(f"Missing environment variables: {missing}")
BACKOFFICE_KWARGS = {var: os.environ[env_var] for var, env_var in CONNECTION_VARS.items()}
CI_STAGE_URL = os.environ['GITHUB_URL_STAGE']
CI_REF = os.environ['GITHUB_REF']
CI_TOKEN = os.environ['GITHUB_TOKEN']
CI_HEADERS = {
    'Accept': 'application/vnd.github.v3+json',
    'Authorization': f"token {CI_TOKEN}",
    'Content-Type': "application/json",
}
REVIEWERS_URL = os.environ['REVIEWERS_URL']


class Permission(IntEnum):
    NOT_LOGGED_IN = 0
    ANONYMOUS = 1
    LOGGED_IN = 2
    REVIEWER = 3

@dataclass
class ResourceData:
    resource_id: str
    version: str
    user_id: str
    timestamp: str = field(init=False)

    def __post_init__(self):
        self.timestamp = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

class ReviewAction(str, Enum):
    REQUESTCHANGES = "requestchanges"
    PUBLISH = "publish"

@dataclass
class ReviewData(ResourceData):
    action: ReviewAction
    message: str = ""

    def save(self, backoffice:  BackOffice):
        logger.info("Requesting review: {}", self)
        if self.action == ReviewAction.PUBLISH:
            backoffice.publish(resource_id=self.resource_id, version=self.version,  reviewer=self.user_id)
        elif self.action == ReviewAction.REQUESTCHANGES:
            backoffice.request_changes(resource_id=self.resource_id, version=self.version, reviewer=self.user_id, reason=self.message)
        else:
            raise ValueError("review_data must contain valid action field")

@dataclass
class ChatData(ResourceData):
    message: str

    def save(self, backoffice: BackOffice):
        backoffice.add_chat_message(
                resource_id=self.resource_id,
                version=self.version,
                chat_message=self.message,
                author=self.user_id)


@dataclass 
class JsonResponse(dict):
    data: InitVar[dict | None]
    error: InitVar[Exception | None]

    def __post_init__(self, data: Any | None, error: Exception | None):
        if data is not None:
            if isinstance(data, dict):
                self.update(data)
            else:
                self['data'] = data 
            self['success'] = True
        if error is not None:
            self['success'] = False
            self['error'] = traceback.format_exception(error)
        

def jsonify_async_handler(handler):
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        data = None
        error = None
        try:
            data = await handler(*args, **kwargs)
        except Exception as err:
            error = err
        return JsonResponse(data=data, error=error) 
    return wrapper
   

async def connect_server(server_url):
    """Connect to the server and register the chat service."""
    login_required = os.environ.get("BIOIMAGEIO_LOGIN_REQUIRED") == "true"
    if login_required:
        token = await login({"server_url": server_url})
    else:
        token = None
    server = await connect_to_server(
        {"server_url": server_url, "token": token, "method_timeout": 100}
    )
    await register_uploader_service(server)


def load_reviewer_ids() -> set[str]:
    """Loads reviewer ids from remote json file"""
    response = requests.get("https://raw.githubusercontent.com/bioimage-io/collection/main/reviewers.json")
    reviewers = response.json()
    reviewer_ids = set(reviewers)
    # Drop any accidental unset ids
    reviewer_ids.discard('')
    reviewer_ids.discard(None)
    return reviewer_ids


def save_latest_collection_template_json(
        url:str="https://raw.githubusercontent.com/bioimage-io/collection/main/collection_template.json",
        destination="collection_template.json",
    ):
    """
    Saves the latest collection_template.json file to the CWD
    """
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception('Unable to find collection_template.json at {}', url)
    with open(destination, 'wb') as file:
        file.write(response.content)
        

async def register_uploader_service(server):
    """Hypha startup function."""
    # debug = os.environ.get("BIOIMAGEIO_DEBUG") == "true"
    # login_required = os.environ.get("BIOIMAGEIO_LOGIN_REQUIRED") == "true"
    # login_required = True
    uploader_logs_path = os.environ.get("BIOIMAGEIO_REVIEW_LOGS_PATH", "./uploader_logs")

    backoffice = BackOffice(**BACKOFFICE_KWARGS)

    assert (
        uploader_logs_path is not None
    ), "Please set the BIOIMAGEIO_REVIEW_LOGS_PATH environment variable to the path of the chat logs folder."
    if not os.path.exists(uploader_logs_path):
        print(
            f"The uploader log folder is not found at {uploader_logs_path}, will create one now."
        )
        os.makedirs(uploader_logs_path, exist_ok=True)

    reviewer_ids = load_reviewer_ids()
    save_latest_collection_template_json()

    def check_permission(user):
        if user is None:
            return Permission.NOT_LOGGED_IN
        if user['is_anonymous']:
            return Permission.ANONYMOUS
        if user['id'] in reviewer_ids:
            return Permission.REVIEWER
        if user['email']:
            return Permission.LOGGED_IN
        return Permission.NOT_LOGGED_IN

    def check_context_permission(context):
        if context is None:
            return Permission.NOT_LOGGED_IN
        user = context.get("user")
        return check_permission(user)

    @jsonify_async_handler
    async def review(resource_id:str, version:str, action:str, message:str, context=None):
        if check_context_permission(context) is not Permission.REVIEWER:
            raise PermissionError("You must be logged in and have permission for this function")
        # get the review-service version
        assert context is not None, "Context cannot be none"
        review_data = ReviewData(
                resource_id=resource_id,
                version=version,
                action=ReviewAction(action),
                message=message,
                user_id=context.get("user").get("id"),
            )
        logger.info("Created review:")
        logger.info(review_data)
        review_data.save(backoffice)

    @jsonify_async_handler
    async def chat(resource_id: str, version: str, message: str, context=None):
        if check_context_permission(context) < Permission.LOGGED_IN:
            raise PermissionError("You must be logged in to comment on the review")
        assert context is not None
        logger.info(f"User: {context.get('user')}, Message: {message}")

        chat_data = ChatData(
            resource_id=resource_id,
            version=version,
            message=message,
            user_id=context.get("user", {}).get('email'),
            )
        chat_data.save(backoffice)

    @jsonify_async_handler
    async def proxy(url:str, context=None, is_json=False) -> dict:
        """
        Basically just a 'middle-man' function to bridge get requests to resources that currently block
        the serving domain
        """
        if check_context_permission(context) == Permission.NOT_LOGGED_IN:
            raise PermissionError("Forbidden")
        response = requests.get(url)
        if is_json:
            return response.json()
        return {'body': requests.get(url).content.decode('utf-8', errors='ignore')}

    @jsonify_async_handler
    async def ping(context=None) -> str:
        """
        Check the server status, as long as we're nominally logged in (can be anonymous)
        """
        if check_context_permission(context) == Permission.NOT_LOGGED_IN:
            raise PermissionError("Forbidden")
        return "pong"

    @jsonify_async_handler
    async def test(context=None):
        # TODO: REMOVE ME
        """
        Test function
        """
        if check_context_permission(context) == Permission.NOT_LOGGED_IN:
            raise PermissionError("Forbidden")
        return f"We is here: {str(context)}"

    @jsonify_async_handler
    async def test_auth(context=None):
        # TODO: REMOVE ME
        """
        Test function
        """
        if check_context_permission(context) < Permission.LOGGED_IN:
            raise PermissionError("You don't have permission to use the uploader service, please sign up and wait for approval")
        return f"We is here: {str(context)}"

    @jsonify_async_handler
    async def is_reviewer(context=None) -> bool:
        """
        Return true if the current user is a reviewer
        """
        return check_context_permission(context) == Permission.REVIEWER

    async def stage(resource_path: str, package_url: str, sandbox: bool=False, context=None) -> dict:
        """
        Notify the CI of a stage
        """

        inputs = {
            'resource_id': resource_path,
            'package_url': package_url,
            'sandbox': sandbox,
        }
        print("IN STAGE:")
        print("    INPUTS:")
        print(inputs)
        return await notify_ci(CI_STAGE_URL, inputs, context=context)

    async def validate(rdf_dict, context=None):
        ctx = ValidationContext(perform_io_checks=False)
        summary = validate_format(rdf_dict, context=ctx)
        return summary.format()

    @jsonify_async_handler
    async def notify_ci(url:str, inputs: dict, context=None) -> dict:
        if check_context_permission(context) < Permission.LOGGED_IN:
            raise PermissionError("You don't have permission to use the uploader service, please sign up and wait for approval")
        data = {'ref': CI_REF, 'inputs': inputs}
        print("NOTIFYING GITHUB:")
        print("data")
        print(data)

        resp = requests.post(url,
                             data=json.dumps(data),
                             headers=CI_HEADERS)
        if resp.status_code == 204:
            # According to API docs, just expect a 204
            return { 'status': resp.status_code }
        else:
            return {'message': f"Failed :(  {resp.content}", 'status':500}



    hypha_service_info = await server.register_service(
        {
            "name": "BioImage.IO Uploader Service",
            "id": "bioimageio-uploader-service",
            "config": {"visibility": "public", "require_context": True, "run_in_executor": True},
            "version": __version__,
            "ping": ping,
            "proxy": proxy,
            "chat": chat,
            "test": test,
            "test_auth": test_auth,
            "is_reviewer": is_reviewer,
            "review": review,
            "stage": stage,
            "validate": validate
        }
    )

    server_url = server.config["public_base_url"]

    # service_id = hypha_service_info["id"]
    # print(
        # f"\nThe BioImage.IO Upload Review service is available at the Hypha server running at {server_url}"
    # )
    print(server.config)
    print(hypha_service_info)
    print(f"Test it with the HTTP proxy: {server_url}/{server.config.workspace}/services/bioimageio-uploader-service/test?")
