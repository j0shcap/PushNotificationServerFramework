# Push Notification Server Framework

## Introduction
`PushNotificationServerFramework` is an open-source template for building remote push notification servers for iOS applications using the [Apple Push Notification service](https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server/sending_notification_requests_to_apns). It handles device registration and delivers notifications through APNs.

### Features
- **Device registration**: Idempotent registration keyed by device token, with optional device metadata.
- **Push delivery**: Per-token results; tokens Apple reports as gone are pruned automatically.
- **APNs client**: Persistent HTTP/2 connection, token (.p8) or certificate authentication, current APNs push types and error reasons.
- **API key authentication**: Bearer-token protection on push and admin endpoints.
- **Data persistence**: SQLAlchemy 2.0 with PostgreSQL.
- **Tested**: Unit, API, and Postgres-backed integration suites run in CI with lint and type checks.

### Project Structure
- `apis/`: API endpoints.
- `auth.py`: API key dependency.
- `database.py`: Database engine and session dependency.
- `entities/`: SQLAlchemy entities.
- `models/`: Pydantic request and response models.
- `push/`: APNs client and push handling.
- `services/`: Application services.
- `tests/`: Unit, API, and integration tests.
- `utils/`: Environment helpers.

## Prerequisites
- Python 3.11+
- PostgreSQL (any reachable instance; a disposable Docker one is shown below)

## Quickstart
```bash
git clone https://github.com/j0shcap/PushNotificationServerFramework.git
cd PushNotificationServerFramework
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.template .env   # then fill in your values
docker run -d --name pnsf-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16-alpine
python main.py
```
Interactive API documentation is served at `http://127.0.0.1:8000/docs`.

## Configuration
Configure the application through the `.env` file. Database and APNs identifiers are required; the notable options:

- `API_KEY` (required): the secret protected endpoints require. The server refuses to start without it.
- `APNS_CERT_PATH`: switches from token auth (the default, recommended by Apple) to certificate auth. Points to a PEM file containing the provider certificate and private key; `APNS_CERT_PASSWORD` supplies its passphrase if any.
- `APNS_USE_SANDBOX`: set to `true` when testing with development builds; their device tokens are only valid against the APNs sandbox environment.
- `CORS_ORIGINS`: comma-separated origins allowed to make cross-origin requests. Unset by default, which disables CORS entirely — iOS apps do not use CORS; only set this when serving a web frontend.
- `DB_ECHO`: set to `true` to log SQL statements during development. Off by default because statements include device tokens.

## Authentication
Endpoints that send pushes or expose device data require the API key:

```
Authorization: Bearer <API_KEY>
```

Requests without a valid key receive `401 Unauthorized`. `/devices/register` is deliberately open: it is called by the iOS app itself, and shipping the key inside the app binary would expose it. The worst an unauthenticated caller can do is register junk tokens, which APNs pruning removes on the next push.

## Client-Side Implementation
To implement push notifications in an iOS application:
1. Register the application for push notifications ([Apple Developer documentation](https://developer.apple.com/documentation/usernotifications/registering_your_app_with_apns)).
2. Request permission from the user to send push notifications.
3. Post the device token to the `/devices/register` endpoint.

## Device Endpoints
#### Register a Device
- **Endpoint**: `/devices/register`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "token": "hex_apns_device_token"
  }
  ```
  Also accepts the optional device fields listed under Design Notes. Server-managed fields (`id`, timestamps) are ignored if sent.
- **Response**: The registered device, including its server-assigned `id` and timestamps. Registration is idempotent by token: re-registering updates the stored fields.

#### Retrieve Devices Information
- **Endpoint**: `/devices/all`
- **Method**: `GET`
- **Auth**: Requires API key

#### Delete All Devices
- **Endpoint**: `/devices`
- **Method**: `DELETE`
- **Auth**: Requires API key

## Push Endpoints
#### Send a Push Notification
- **Endpoint**: `/push/send`
- **Method**: `POST`
- **Auth**: Requires API key
- **Body**:
  ```json
  {
    "recipients": ["device_token_1", "device_token_2"],
    "body": "notification_body"
  }
  ```
- **Response**: A mapping of each device token to `"Success"` or the APNs failure reason. A failure for one token does not prevent delivery to the others.
  ```json
  {
    "device_token_1": "Success",
    "device_token_2": "Unregistered"
  }
  ```
  Devices whose tokens APNs reports as `Unregistered` are automatically removed from the database.

## Design Notes

### Device Entity and Models

The `Device` entity and its model represent a device registered with the server. This device includes the device token and optionally additional device information available in the [UIDevice class](https://developer.apple.com/documentation/uikit/uidevice).

- `token`: The device token used to send push notifications to the device. (Required, String)
- `name`: The name of the device. (Optional, String)
- `systemName`: The name of the operating system running on the device. (Optional, String)
- `systemVersion`: The current version of the operating system. (Optional, String)
- `model`: The model of the device. (Optional, String)
- `localizedModel`: The model of the device as a localized string. (Optional, String)

### CORS
Cross-origin requests are disabled by default. To develop a web frontend against the server, set `CORS_ORIGINS` to the exact origins you serve it from (never a wildcard in production).

**Note**: CORS is a browser security feature that prevents cross-origin requests. It does not affect requests from iOS applications.

## Testing
Run the unit and API test suite:
```bash
pytest
```

Integration tests boot the real server against a real Postgres and drive it over HTTP. Point them at any Postgres instance (for example, a disposable container):
```bash
docker run -d --name pnsf-test-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16-alpine
INTEGRATION_DB_HOST=localhost pytest tests/integration
```
CI runs both suites, plus ruff and mypy, on every push and pull request.

## Contributing
Contributions to this repository are welcome. Please follow the standard GitHub pull request process to propose changes.

## License
This project is licensed under the [MIT License](LICENSE).

## Acknowledgements
- Pydantic for data validation and serialization.
- SQLAlchemy ORM for database management.
- FastAPI for the server framework.
- The Python `apns2` package, from which the vendored APNs client is derived.
