from enum import Enum
from pydantic import BaseModel, Field, field_validator

import requests

from config import settings


class ButtonStyle(Enum):
    """Slack button styles"""

    PRIMARY = "primary"
    DANGER = "danger"


# SECTION: Add more objects as per need ---------------------------


class MDText(BaseModel):
    """Slack markdown text object"""

    text: str
    type: str = "mrkdwn"

class PlainText(BaseModel):
    """Slack plain text object"""

    text: str
    emoji: bool = True
    type: str = "plain_text"

class Image(BaseModel):
    """Slack image object"""

    image_url: str
    alt_text: str
    type: str = "image"


class Button(BaseModel):
    """Slack button object"""

    text: MDText | PlainText
    action_id: str
    value: str
    style: ButtonStyle = ButtonStyle.PRIMARY
    url: str | None = None
    type: str = "button"

    @field_validator("style", mode="before")
    @classmethod
    def validate_text_type(cls, value):
        if isinstance(value, str):
            return ButtonStyle(value.lower())
        if not isinstance(value, ButtonStyle):
            raise ValueError(f"Invalid button style type: {value}")
        return value


class Option(BaseModel):
    value: str
    text: MDText | PlainText


class MultiSelect(BaseModel):
    placeholder: MDText | PlainText
    options: list[Option]
    action_id: str
    type: str = "multi_static_select"


# SECTION: Add more block types as per need ---------------------------


class DividerBlock(BaseModel):
    type: str = "divider"


class SectionBlock(BaseModel):
    text: MDText | PlainText
    accessory: Button | MultiSelect | None = None
    type: str = "section"


class HeaderBlock(BaseModel):
    text: MDText | PlainText
    type: str = "header"


class ContextBlock(BaseModel):
    elements: list[MDText | PlainText | Image]
    type: str = "context"


class ActionsBlock(BaseModel):
    elements: list[Button]
    type: str = "actions"


class Payload(BaseModel):
    """
    A Slack message payload.

    You can use this to send a message to a Slack channel.
    If you provide a `user`, it will send an ephemeral message to that user.
    """

    channel: str
    blocks: list[
        DividerBlock | SectionBlock | HeaderBlock | ContextBlock | ActionsBlock
    ]
    text: str
    user: str | None = Field(default=None)

    model_config = {
        "arbitrary_types_allowed": True,
        "use_enum_values": True,
    }

    def post(self) -> dict[str, str | int]:
        """
        Posts the payload to the Slack API.

        If `user` is provided, it will send an ephemeral message to that user.
        Otherwise, it will send a regular message to the channel.

        Returns:
            A dictionary with the message text and Slack status code.
        """
        if self.user:
            endpoint = "/chat.postEphemeral"
        else:
            endpoint = "/chat.postMessage"
        
        payload = self.model_dump(exclude_none=True, mode="json")
        headers = {
            "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        }
        response = requests.post(
            f"https://slack.com/api{endpoint}", json=payload, headers=headers
        )
        return {
            "message": response.text,
            "slack_status": response.status_code,
        }