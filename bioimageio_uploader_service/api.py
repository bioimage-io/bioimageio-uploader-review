import os
import json
import datetime
from enum import IntEnum, StrEnum, auto
from dataclasses import dataclass, field

from loguru import logger


from bioimageio_collection_backoffice._backoffice import BackOffice
from bioimageio_uploader_service import __version__
from imjoy_rpc.hypha import login, connect_to_server


class MissingEnvironmentVariable(Exception):
    pass

class Permission(IntEnum):
    NOT_LOGGED_IN = 0
    ANONYMOUS = 1
    LOGGED_IN = 2
    REVIEWER = 3

@dataclass
class ResourceData:
    resource_id: str
    version: str
    user: str
    timestamp: str = field(init=False)

    def __post_init__(self):
        self.timestamp = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),

class ReviewAction(StrEnum):
    REQUESTCHANGES = auto()
    PUBLISH = auto()

@dataclass
class ReviewData(ResourceData):
    action: ReviewAction
    message: str = ""

    def save(self, backoffice:  BackOffice):
        if self.action == ReviewAction.PUBLISH:
            backoffice.publish(resource_id=self.resource_id, version=self.version,  reviewer=self.user)
        elif self.action == ReviewAction.REQUESTCHANGES:
            backoffice.request_changes(resource_id=self.resource_id, version=self.version, reviewer=self.user, reason=self.message)
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
                author=self.user)


CONNECTION_VARS = {"host": "S3_HOST", "bucket": "S3_BUCKET", "prefix": "S3_FOLDER"}


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


async def register_uploader_service(server):
    """Hypha startup function."""
    debug = os.environ.get("BIOIMAGEIO_DEBUG") == "true"
    login_required = os.environ.get("BIOIMAGEIO_LOGIN_REQUIRED") == "true"
    login_required = True
    uploader_logs_path = os.environ.get("BIOIMAGEIO_REVIEW_LOGS_PATH", "./uploader_logs")

    if not set(os.environ).issuperset(CONNECTION_VARS.values()):
        logger.error("Must be run with following env vars: {}", ", ".join(CONNECTION_VARS.values()))
        missing = [var for var in CONNECTION_VARS.values() if var not in os.environ]
        raise MissingEnvironmentVariable(f"Missing environment variables: {missing}")

    backoffice = BackOffice(**{var: os.environ[env_var] for var, env_var in CONNECTION_VARS.items()})

    assert (
        uploader_logs_path is not None
    ), "Please set the BIOIMAGEIO_REVIEW_LOGS_PATH environment variable to the path of the chat logs folder."
    if not os.path.exists(uploader_logs_path):
        print(
            f"The uploader log folder is not found at {uploader_logs_path}, will create one now."
        )
        os.makedirs(uploader_logs_path, exist_ok=True)

    def user_has_email(context):
        return context and context.get("user") and context.get("user").get("email")


    def load_reviewer_emails():
        if login_required:
            authorized_reviewers_path = os.environ.get("BIOIMAGEIO_AUTHORIZED_REVIEWERS_PATH")
            if authorized_reviewers_path:
                assert os.path.exists(
                    authorized_reviewers_path
                ), f"The authorized reviewers file is not found at {authorized_reviewers_path}"
                with open(authorized_reviewers_path, "r") as f:
                    authorized_users = json.load(f)["users"]
                authorized_emails = [
                    user["email"] for user in authorized_users if "email" in user
                ]
            else:
                authorized_emails = ()
        else:
            authorized_emails = ()
        return authorized_emails

    reviewer_emails = load_reviewer_emails()

    def check_permission(user):
        if user['is_anonymous']:
            return Permission.ANONYMOUS
        if user["email"] in reviewer_emails:
            return Permission.REVIEWER
        if user["email"]:
            return Permission.LOGGED_IN
        return Permission.NOT_LOGGED_IN

    def check_context_permission(context):
        if context is None:
            return Permission.NOT_LOGGED_IN
        user = context.get("user")
        if user is None:
            return Permission.NOT_LOGGED_IN

        if user['is_anonymous']:
            return Permission.ANONYMOUS
        if user['email'] in reviewer_emails:
            return Permission.REVIEWER
        if user['email']:
            return Permission.LOGGED_IN
        raise PermissionError("Context invalid while checking for permission")

    async def review(resource_id=str, version=str, action=str, message=str, context=None):
        if check_context_permission(context) is not Permission.REVIEWER:
            raise PermissionError("You must be logged in and have permission for this function")
        # get the review-service version
        review_data = ReviewData(
                resource_id=resource_id,
                version=version,
                action=ReviewAction(action),
                message=message,
                user= context.get("user"),
            )
        review_data.save(backoffice)

    async def chat(resource_id: str, version: str, message: str, context=None):
        logger.info(f"User: {context.get('user')}, Message: {message}")
        if check_context_permission(context) < Permission.LOGGED_IN:
            raise PermissionError("You must be logged in to comment on the review")

        chat_data = ChatData(
            resource_id=resource_id,
            version=version,
            message=message,
            user=context.get("user"),
            )

        chat_data.save(backoffice)

    async def get_from_storage(url:str, context=None):
        """
        Basically just a 'middle-man' function to bridge get requests to S3 resource that currently blocks
        all but a small number of domains
        """

    async def ping(context=None):
        """
        Check the server status, as long as we're nominally logged in (can be anonymous)
        """
        if check_context_permission(context) == Permission.NOT_LOGGED_IN:
            raise PermissionError("You don't have permission to use the uploader service, please sign up and wait for approval")
        return "pong"

    async def test(context=None):
        # TODO: REMOVE ME
        """
        Test function
        """
        if check_context_permission(context) == Permission.NOT_LOGGED_IN:
            raise PermissionError("You don't have permission to use the uploader service, please sign up and wait for approval")
        return f"We is here: {str(context)}"

    async def test_auth(context=None):
        # TODO: REMOVE ME
        """
        Test function
        """
        if check_context_permission(context) < Permission.LOGGED_IN:
            raise PermissionError("You don't have permission to use the uploader service, please sign up and wait for approval")
        return f"We is here: {str(context)}"

    async def notify_ci(payload: dict, context=None):
        """
        Notify the CI of a job to perform
        """
        if check_context_permission(context) < Permission.LOGGED_IN:
            raise PermissionError("You don't have permission to use the uploader service, please sign up and wait for approval")
        raise NotImplementedError("Move netlify function to here")


    hypha_service_info = await server.register_service(
        {
            "name": "BioImage.IO Uploader Service",
            "id": "bioimageio-uploader-service",
            "config": {"visibility": "public", "require_context": True},
            "version": __version__,
            "ping": ping,
            "chat": chat,
            "test": test,
            "review": review,
            "notify_ci": notify_ci,
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