from enum import Enum
from pydantic import BaseModel, field_validator

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
    channel: str
    blocks: list[
        DividerBlock | SectionBlock | HeaderBlock | ContextBlock | ActionsBlock
    ]
    text: str

    class Config:
        arbitrary_types_allowed = True

    def post(self):
        payload = self.model_dump_json(exclude_none=True)
        headers = {
            "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            "https://slack.com/api/chat.postMessage", data=payload, headers=headers
        )
        return {
            "message": response.text,
            "slack_status": response.status_code,
        }

