import os
import json
import datetime
import pkg_resources
from enum import IntEnum, StrEnum, auto
from dataclasses import dataclass, field

from loguru import logger

from bioimageio_collection_backoffice._backoffice import BackOffice
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

    def save(self, backoffice:  BackOffice):
        if self.action == ReviewAction.PUBLISH:
            backoffice.publish(resource_id=self.resource_id, version=self.version,  reviewer=self.user)
        elif self.action == ReviewAction.REQUESTCHANGES:
            backoffice.request_changes(resource_id=self.resource_id, version=self.version, reviewer=self.user)
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


CONNECTION_VARS = {"host": "S3_HOST", "bucket": "S3_BUCKET", "folder": "S3_FOLDER"}


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
    await register_review_service(server)


async def register_review_service(server):
    """Hypha startup function."""
    debug = os.environ.get("BIOIMAGEIO_DEBUG") == "true"
    login_required = os.environ.get("BIOIMAGEIO_LOGIN_REQUIRED") == "true"
    review_logs_path = os.environ.get("BIOIMAGEIO_REVIEW_LOGS_PATH", "./review_logs")

    if not set(os.environ).issuperset(CONNECTION_VARS.values()):
        logger.error("Must be run with following env vars: {}", ", ".join(CONNECTION_VARS.values()))
        missing = [var for var in CONNECTION_VARS.values() if var not in os.environ]
        raise MissingEnvironmentVariable(f"Missing environment variables: {missing}")

    backoffice = BackOffice({var: os.environ[env_var] for var, env_var in CONNECTION_VARS.items()})

    assert (
        review_logs_path is not None
    ), "Please set the BIOIMAGEIO_REVIEW_LOGS_PATH environment variable to the path of the chat logs folder."
    if not os.path.exists(review_logs_path):
        print(
            f"The review session folder is not found at {review_logs_path}, will create one now."
        )
        os.makedirs(review_logs_path, exist_ok=True)


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

    async def review(review_message, context=None):
        if login_required and context and context.get("user"):
            assert check_permission(
                context.get("user")
            ) == Permission.REVIEWER, "You don't have permission to review resources."
        # get the review-service version
        review_data = {
            "timestamp": str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "user": context.get("user"),
            "version": version,
        }
        review_data.save(backoffice)

    async def chat(resource_id: str, version: str, message: str, context=None):
        logger.info(f"User: {context.get('user')}, Message: {message}")
        if context and context.get("user"):
            assert check_permission(
                context.get("user")
            ) >= Permission.LOGGED_IN, "You don't have permission to comment on the review."
        # get the review-service version
        chat_data = ChatData(
            resource_id=resource_id,
            version=version,
            message=message,
            user=context.get("user"),
            )

        chat_data.save(backoffice)

    async def ping(context=None):
        if login_required and context and context.get("user"):
            assert check_permission(
                context.get("user")
            ) > Permission.NOT_LOGGED_IN, "You don't have permission to use the review service, please sign up and wait for approval"
        return "pong"



    version = pkg_resources.get_distribution("bioimageio-upload-review").version
    hypha_service_info = await server.register_service(
        {
            "name": "BioImage.IO Upload Review",
            "id": "bioimageio-upload-review",
            "config": {"visibility": "public", "require_context": True},
            "version": version,
            "ping": ping,
            "chat": chat,
            "review": review,
        }
    )

    server_url = server.config["public_base_url"]

    service_id = hypha_service_info["id"]
    print(
        f"\nThe BioImage.IO Upload Review endpoint is available at: https://bioimage.io/upload-review?server={server_url}&service_id={service_id}\n"
    )
