"""Manual end-to-end check against Apple's real APNs sandbox.

Sends one notification through the real PushHandler using the APNs credentials
from the environment (or .env). Not part of the automated test suite because
it performs a real network call to Apple.

Usage:
    python scripts/e2e_apns_sandbox.py [device_token]

With real credentials and a sandbox device token from a development build, the
device receives the notification and the result is "Success". With throwaway
credentials the expected result is "InvalidProviderToken" — Apple rejecting
the key still proves connectivity, HTTP/2, JWT signing, and response parsing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from push import PushHandler
from push.config import PushConfig

if not PushConfig.get_use_sandbox():
    sys.exit("Set APNS_USE_SANDBOX=true; this script only targets the sandbox.")

device_token = sys.argv[1] if len(sys.argv) > 1 else "deadbeef00"
results = PushHandler().send_multiple_push(
    to_device_tokens=[device_token], body="PushNotificationServerFramework e2e test"
)
print(results)
result = results[device_token]
if result not in ("Success", "InvalidProviderToken", "ExpiredProviderToken", "BadDeviceToken"):
    sys.exit(f"Unexpected result: {result}")
print("PASS: reached the APNs sandbox and parsed its response.")
