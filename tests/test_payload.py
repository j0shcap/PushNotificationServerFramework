"""Tests for APNs payload serialization.

Key names and nesting must match Apple's payload schema exactly; a wrong key
is silently ignored by APNs rather than rejected, so these tests are the only
guard against that class of bug.
"""

from push.apn_handler import Payload
from push.apn_handler.payload import PayloadAlert


def test_string_alert():
    assert Payload(alert="hello").dict() == {"aps": {"alert": "hello"}}


def test_empty_payload_has_empty_aps():
    assert Payload().dict() == {"aps": {}}


def test_alert_with_sound_and_badge():
    result = Payload(alert="hello", sound="default", badge=3).dict()

    assert result == {"aps": {"alert": "hello", "sound": "default", "badge": 3}}


def test_badge_zero_is_included():
    # badge=0 is meaningful: it clears the app icon badge.
    assert Payload(badge=0).dict()["aps"]["badge"] == 0


def test_background_push():
    result = Payload(content_available=True).dict()

    assert result == {"aps": {"content-available": 1}}


def test_mutable_content_flag():
    assert Payload(alert="hi", mutable_content=True).dict()["aps"]["mutable-content"] == 1


def test_category_and_thread_id():
    result = Payload(alert="hi", category="MESSAGE", thread_id="chat-42").dict()

    assert result["aps"]["category"] == "MESSAGE"
    assert result["aps"]["thread-id"] == "chat-42"


def test_url_args():
    assert Payload(url_args=["a", "b"]).dict()["aps"]["url-args"] == ["a", "b"]


def test_custom_data_merges_at_top_level():
    result = Payload(alert="hi", custom={"conversation_id": 7}).dict()

    assert result["conversation_id"] == 7
    assert "conversation_id" not in result["aps"]


def test_payload_alert_full_fields():
    alert = PayloadAlert(
        title="Title",
        title_localized_key="TITLE_KEY",
        title_localized_args=["t1"],
        subtitle="Subtitle",
        subtitle_localized_key="SUBTITLE_KEY",
        subtitle_localized_args=["s1"],
        body="Body",
        body_localized_key="BODY_KEY",
        body_localized_args=["b1"],
        action_localized_key="ACTION_KEY",
        action="View",
        launch_image="launch.png",
    )

    assert alert.dict() == {
        "title": "Title",
        "title-loc-key": "TITLE_KEY",
        "title-loc-args": ["t1"],
        "subtitle": "Subtitle",
        "subtitle-loc-key": "SUBTITLE_KEY",
        "subtitle-loc-args": ["s1"],
        "body": "Body",
        "loc-key": "BODY_KEY",
        "loc-args": ["b1"],
        "action-loc-key": "ACTION_KEY",
        "action": "View",
        "launch-image": "launch.png",
    }


def test_payload_alert_omits_unset_fields():
    assert PayloadAlert(title="Title").dict() == {"title": "Title"}


def test_structured_alert_nests_inside_aps():
    alert = PayloadAlert(title="Title", body="Body")

    result = Payload(alert=alert).dict()

    assert result["aps"]["alert"] == {"title": "Title", "body": "Body"}
