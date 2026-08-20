from fastapi import APIRouter, Depends

from auth import require_api_key
from models import Message
from services import PushService

router = APIRouter(
    prefix="/push",
    tags=["push"],
    dependencies=[Depends(require_api_key)],
    responses={404: {"description": "Not found"}},
)


@router.post("/send", response_model=dict[str, str])
def send_push(message: Message, push_service: PushService = Depends()):
    """
    Sends a push notification to each recipient.

    Args:
        message (Message): The message to send.
        push_service (PushService): The push service to use. Injected by FastAPI.

    Returns:
        dict[str, str]: A mapping of each device token to "Success" or the
            APNs failure reason.
    """
    return push_service.send_push(message)
