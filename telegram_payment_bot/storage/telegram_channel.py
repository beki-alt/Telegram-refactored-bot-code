"""
storage/telegram_channel.py
────────────────────────────
Phase 3 — Telegram Channel Storage Service

Uses a private Telegram channel as secondary large-file storage.
Supabase free tier stores only message IDs and metadata.
The actual files live in the Telegram channel as archived messages.

Architecture:
  - upload(bot, file_id, caption)  → stores file in channel, returns message_id
  - retrieve(bot, message_id)      → forwards or fetches file from channel
  - All message IDs stored in Supabase settings / payments tables.

Supports:
  - Photos (receipt screenshots)
  - Documents
  - Automatic fallback when channel is unconfigured
"""

import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)


class TelegramStorageService:
    """
    Abstraction layer for storing and retrieving large files via a private
    Telegram channel. Gracefully degrades when STORAGE_CHANNEL_ID is unset.
    """

    def __init__(self, storage_channel_id: Optional[str] = None):
        self.channel_id = storage_channel_id or config.STORAGE_CHANNEL_ID
        if self.channel_id:
            try:
                self._channel_id_int = int(self.channel_id)
            except ValueError:
                logger.error(
                    f"STORAGE_CHANNEL_ID '{self.channel_id}' is not a valid integer. "
                    "Telegram storage disabled."
                )
                self._channel_id_int = None
        else:
            self._channel_id_int = None

    @property
    def is_configured(self) -> bool:
        return self._channel_id_int is not None

    async def upload_photo(
        self,
        bot,
        file_id: str,
        caption: str = "",
    ) -> Optional[int]:
        """
        Send a photo to the storage channel and return the resulting message_id.
        Returns None if the channel is not configured or the upload fails.
        """
        if not self.is_configured:
            logger.warning("Telegram storage: channel not configured, skipping upload.")
            return None
        try:
            msg = await bot.send_photo(
                chat_id    = self._channel_id_int,
                photo      = file_id,
                caption    = caption,
                parse_mode = "Markdown",
            )
            logger.info(f"Stored photo in channel, message_id={msg.message_id}")
            return msg.message_id
        except Exception as exc:
            logger.error(f"Telegram storage upload failed: {exc}")
            return None

    async def upload_document(
        self,
        bot,
        document,  # bytes or file-like object
        filename: str,
        caption: str = "",
    ) -> Optional[int]:
        """
        Upload a document (e.g. Excel report bytes) to the storage channel.
        Returns message_id or None.
        """
        if not self.is_configured:
            logger.warning("Telegram storage: channel not configured, skipping upload.")
            return None
        try:
            msg = await bot.send_document(
                chat_id  = self._channel_id_int,
                document = document,
                filename = filename,
                caption  = caption,
            )
            logger.info(f"Stored document '{filename}' in channel, message_id={msg.message_id}")
            return msg.message_id
        except Exception as exc:
            logger.error(f"Telegram storage document upload failed: {exc}")
            return None

    async def forward_to(
        self,
        bot,
        source_message_id: int,
        target_chat_id: int,
    ) -> bool:
        """
        Forward a stored message from the storage channel to another chat.
        Used to show receipts to admins.
        Returns True on success.
        """
        if not self.is_configured:
            return False
        try:
            await bot.forward_message(
                chat_id      = target_chat_id,
                from_chat_id = self._channel_id_int,
                message_id   = source_message_id,
            )
            return True
        except Exception as exc:
            logger.error(
                f"Telegram storage: forward failed "
                f"(msg_id={source_message_id} → chat={target_chat_id}): {exc}"
            )
            return False

    async def get_photo_file_id(
        self,
        bot,
        source_message_id: int,
    ) -> Optional[str]:
        """
        Copy a message to a temporary location to retrieve its file_id.
        Used to re-send stored photos without forwarding.

        Note: Telegram does not provide a direct "get message" API for bots;
        we use copy_message to the same channel and read the returned message.
        """
        if not self.is_configured:
            return None
        try:
            msg = await bot.copy_message(
                chat_id      = self._channel_id_int,
                from_chat_id = self._channel_id_int,
                message_id   = source_message_id,
            )
            # msg.message_id is the copy; we can't easily get the file_id here
            # without reading the copy — fall back to forward_to for display
            return None
        except Exception as exc:
            logger.error(f"Telegram storage: get_photo_file_id failed: {exc}")
            return None

    async def send_photo_to_admin(
        self,
        bot,
        admin_chat_id: int,
        file_id: Optional[str],
        channel_msg_id: Optional[int],
        caption: str,
        reply_markup=None,
    ) -> bool:
        """
        Send a receipt photo to an admin.
        Strategy:
          1. If file_id is available (stored directly), use send_photo.
          2. Else forward from storage channel.
          3. Fall back to text-only message with caption.
        Returns True if a message was sent.
        """
        # Strategy 1: use stored file_id directly
        if file_id:
            try:
                await bot.send_photo(
                    chat_id      = admin_chat_id,
                    photo        = file_id,
                    caption      = caption,
                    parse_mode   = "Markdown",
                    reply_markup = reply_markup,
                )
                return True
            except Exception as exc:
                logger.warning(f"send_photo by file_id failed: {exc}")

        # Strategy 2: forward from channel
        if channel_msg_id and self.is_configured:
            try:
                await bot.forward_message(
                    chat_id      = admin_chat_id,
                    from_chat_id = self._channel_id_int,
                    message_id   = channel_msg_id,
                )
                # Send caption + buttons separately
                if caption or reply_markup:
                    await bot.send_message(
                        chat_id      = admin_chat_id,
                        text         = caption,
                        parse_mode   = "Markdown",
                        reply_markup = reply_markup,
                    )
                return True
            except Exception as exc:
                logger.warning(f"forward from channel failed: {exc}")

        # Strategy 3: text-only fallback
        try:
            await bot.send_message(
                chat_id      = admin_chat_id,
                text         = caption,
                parse_mode   = "Markdown",
                reply_markup = reply_markup,
            )
            return True
        except Exception as exc:
            logger.error(f"Text fallback also failed for admin {admin_chat_id}: {exc}")
            return False


# Module-level singleton
storage = TelegramStorageService()
