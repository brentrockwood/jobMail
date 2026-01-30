"""Gmail API client wrapper with OAuth2 authentication."""

import logging
import pickle
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Gmail API scopes
# Using gmail.modify instead of full gmail scope for better security
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


class GmailClient:
    """Gmail API client with OAuth2 authentication."""

    def __init__(self, credentials_file: Path, token_file: Path) -> None:
        """
        Initialize Gmail client.

        Args:
            credentials_file: Path to OAuth2 credentials JSON file
            token_file: Path to store/load OAuth2 token
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service: Any = None
        self.creds: Credentials | None = None

    def authenticate(self) -> None:
        """
        Authenticate with Gmail API using OAuth2.

        For headless/unattended operation:
        1. First run: Requires user interaction to authorize and save token
        2. Subsequent runs: Uses saved token, refreshes automatically if expired

        Raises:
            FileNotFoundError: If credentials file doesn't exist
            Exception: If authentication fails
        """
        if not self.credentials_file.exists():
            raise FileNotFoundError(
                f"Credentials file not found: {self.credentials_file}\n"
                "Download it from Google Cloud Console:\n"
                "1. Go to https://console.cloud.google.com/apis/credentials\n"
                "2. Create OAuth 2.0 Client ID (Desktop app)\n"
                "3. Download JSON and save as credentials.json"
            )

        # Load existing token if available
        if self.token_file.exists():
            logger.info(f"Loading existing token from {self.token_file}")
            with open(self.token_file, "rb") as token:
                self.creds = pickle.load(token)

        # Refresh or authenticate
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("Refreshing expired token")
                self.creds.refresh(Request())
            else:
                logger.info("Starting OAuth2 flow (user authorization required)")
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file), SCOPES)
                # Use run_local_server for initial auth
                # For truly headless operation, token must be generated first
                # on a machine with browser access
                self.creds = flow.run_local_server(port=0)

            # Save token for future runs
            logger.info(f"Saving token to {self.token_file}")
            with open(self.token_file, "wb") as token:
                pickle.dump(self.creds, token)

        # Build Gmail service
        logger.info("Building Gmail API service")
        self.service = build("gmail", "v1", credentials=self.creds)
        logger.info("Gmail authentication successful")

    def list_messages(
        self, query: str = "", max_results: int = 100, label_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        List messages matching query.

        Args:
            query: Gmail search query (e.g., "is:unread in:inbox")
            max_results: Maximum number of messages to return
            label_ids: Filter by label IDs (e.g., ["INBOX"])

        Returns:
            List of message metadata dicts

        Raises:
            Exception: If API call fails
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        logger.debug(f"Listing messages: query={query}, max_results={max_results}")
        try:
            request_params: dict[str, Any] = {
                "userId": "me",
                "maxResults": max_results,
            }
            if query:
                request_params["q"] = query
            if label_ids:
                request_params["labelIds"] = label_ids

            results = self.service.users().messages().list(**request_params).execute()
            messages = results.get("messages", [])
            logger.info(f"Found {len(messages)} messages")
            return messages
        except Exception as e:
            logger.error(f"Failed to list messages: {e}")
            raise

    def get_message(self, message_id: str, format: str = "full") -> dict[str, Any]:
        """
        Get full message details.

        Args:
            message_id: Gmail message ID
            format: Response format (minimal, full, raw, metadata)

        Returns:
            Message details dict

        Raises:
            Exception: If API call fails
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        logger.debug(f"Getting message: {message_id}")
        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format=format)
                .execute()
            )
            return message
        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            raise

    def modify_message(
        self,
        message_id: str,
        add_label_ids: list[str] | None = None,
        remove_label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Modify message labels.

        Args:
            message_id: Gmail message ID
            add_label_ids: Label IDs to add
            remove_label_ids: Label IDs to remove

        Returns:
            Modified message dict

        Raises:
            Exception: If API call fails
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        body: dict[str, Any] = {}
        if add_label_ids:
            body["addLabelIds"] = add_label_ids
        if remove_label_ids:
            body["removeLabelIds"] = remove_label_ids

        logger.debug(f"Modifying message {message_id}: {body}")
        try:
            result = (
                self.service.users()
                .messages()
                .modify(userId="me", id=message_id, body=body)
                .execute()
            )
            logger.info(f"Modified message {message_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to modify message {message_id}: {e}")
            raise

    def create_label(self, name: str) -> dict[str, Any]:
        """
        Create a new label.

        Args:
            name: Label name

        Returns:
            Label details dict

        Raises:
            Exception: If API call fails
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        label_object = {
            "name": name,
            "messageListVisibility": "show",
            "labelListVisibility": "labelShow",
        }

        logger.debug(f"Creating label: {name}")
        try:
            result = self.service.users().labels().create(userId="me", body=label_object).execute()
            logger.info(f"Created label: {name} (id: {result['id']})")
            return result
        except Exception as e:
            logger.error(f"Failed to create label {name}: {e}")
            raise

    def list_labels(self) -> list[dict[str, Any]]:
        """
        List all labels.

        Returns:
            List of label dicts

        Raises:
            Exception: If API call fails
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        logger.debug("Listing labels")
        try:
            results = self.service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])
            logger.info(f"Found {len(labels)} labels")
            return labels
        except Exception as e:
            logger.error(f"Failed to list labels: {e}")
            raise

    def get_or_create_label(self, name: str) -> str:
        """
        Get label ID by name, creating it if it doesn't exist.

        Args:
            name: Label name

        Returns:
            Label ID

        Raises:
            Exception: If API call fails
        """
        labels = self.list_labels()
        for label in labels:
            if label["name"] == name:
                logger.debug(f"Label '{name}' exists with ID: {label['id']}")
                return label["id"]

        # Label doesn't exist, create it
        logger.info(f"Label '{name}' doesn't exist, creating it")
        result = self.create_label(name)
        return result["id"]

    def archive_message(self, message_id: str) -> dict[str, Any]:
        """
        Archive a message by removing the INBOX label.

        Args:
            message_id: Gmail message ID

        Returns:
            Modified message dict

        Raises:
            Exception: If API call fails
        """
        logger.debug(f"Archiving message: {message_id}")
        return self.modify_message(message_id, remove_label_ids=["INBOX"])

    def apply_label(self, message_id: str, label_name: str) -> dict[str, Any]:
        """
        Apply a label to a message, creating the label if it doesn't exist.

        Args:
            message_id: Gmail message ID
            label_name: Name of the label to apply

        Returns:
            Modified message dict

        Raises:
            Exception: If API call fails
        """
        label_id = self.get_or_create_label(label_name)
        logger.debug(f"Applying label '{label_name}' to message {message_id}")
        return self.modify_message(message_id, add_label_ids=[label_id])
