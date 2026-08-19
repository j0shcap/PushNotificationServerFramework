# Push Notification Server Framework

## Introduction
`PushNotificationServerFramework` is an open-source project designed to offer a template for creating remote push notification servers for iOS applications via [Apple Push Notification service](https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server/sending_notification_requests_to_apns).

It simplifies the process of registering devices with the server and provides services for storing, fetching, and clearing device information, in addition to providing endpoints for sending push notifications to these devices.

### Features
- **Premade Models and Entities**: Includes premade models and entities for device and message information.
- **Device Endpoints**: Facilitates registering and fetching devices with the server.
- **Push Endpoints**: Provides endpoints for sending push notifications to devices.
- **Data Persistence**: Utilizes SQLAlchemy ORM for managing database operations.
- **Pydantic Models**: Ensures validation and serialization of device and message entities.
- **Modified APNS2**: Includes a modified version of the Python `apns2` package, updated for Python 3.11 compatibility.
- **FastAPI Framework**: Leverages the FastAPI framework for efficient and easy server development.

### Project Structure
- `apis/`: Contains the API endpoints for the server.
- `entities/`: Contains the SQLAlchemy entities for the server.
- `models/`: Contains the Pydantic models for the server.
- `push/`: Contains the push notification services for the server.
- `services/`: Contains the services for the server.
- `utils/`: Contains utility functions for the server.

## Prerequisites
Before installing this repository, ensure you have the following:
- Python 3.11
- Pip package manager

## Installation
To install this repository, follow these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/JoshCap20/PushNotificationServerFramework.git
   ```
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration
Configure the application by creating an .env file based off the template. Set the necessary parameters like database connection parameters and APNs identifiers.

Set `APNS_USE_SANDBOX=true` when testing with development builds; their device tokens are only valid against the APNs sandbox environment.

## Running the Server
To start the server, run the following command:
```bash
python main.py
```

## Client-Side Implementation
To implement push notifications in an iOS application, follow the steps below:
1. Register the application for push notifications. 
    - See [Apple Developer documentation](https://developer.apple.com/documentation/usernotifications/registering_your_app_with_apns) for more information.
2. Request permission from the user to send push notifications.
3. Register the device with the server.
    - Post the device token to the `/devices/register` endpoint.


## Device Endpoints
#### Register a Device
- **Endpoint**: `/devices/register`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "token": "unique_device_id",
  }
  ```

#### Retrieve Devices Information
- **Endpoint**: `/devices/all`
- **Method**: `GET`

#### Clear Devices Information
- **Endpoint**: `/devices/clear`
- **Method**: `GET`

## Push Endpoints
#### Send a Push Notification
- **Endpoint**: `/push/send`
- **Method**: `POST`
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

### FastAPI CORS Middleware
This middleware was left in the project to allow for cross-origin requests during development. This decision was made to enable CORS with frontend applications during development. However, it is not recommended to enable CORS in production environments as it can lead to security vulnerabilities.

**Note**: CORS is a browser security feature that prevents cross-origin requests. It does not affect requests from iOS applications.

## Contributing
Contributions to this repository are welcome. Please follow the standard GitHub pull request process to propose changes.

## License
This project is licensed under the [MIT License](LICENSE).

## Acknowledgements
- Pydantic for data validation and serialization.
- SQLAlchemy ORM for database management.
- FastAPI for the server framework.
- Modified Python `apns2` package for handling Apple Push Notification services.
