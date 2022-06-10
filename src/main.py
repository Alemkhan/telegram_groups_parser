import asyncio
import csv
import dataclasses
import os
import sys
from asyncio import sleep
from typing import Any, NamedTuple

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import UsernameNotOccupiedError
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.types import ChannelParticipantsSearch, InputChannel, User

load_dotenv()

api_id = os.getenv("TELEGRAM_APP_ID")
api_hash = os.getenv("TELEGRAM_APP_HASH")
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_names: list[str] = os.getenv("CHAT_NAMES").split(",")
limit = 200


class ChatInformation(NamedTuple):
    chat_id: int
    chat_name: str
    access_hash: int


@dataclasses.dataclass
class UserInformation:
    first_name: str | None
    last_name: str | None
    username: str
    phone: str | None

    @classmethod
    def get_field_names(cls) -> list[str]:
        return ["first_name", "last_name", "username", "phone"]

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "username": self.username,
            "phone": self.phone,
        }


async def get_chat_information(chat_name: str, client: TelegramClient):
    try:
        chat = await client(ResolveUsernameRequest(chat_name))
    except UsernameNotOccupiedError:
        print("Chat/channel not found!")
        sys.exit()

    chat_info = ChatInformation(
        chat_id=chat.peer.channel_id, chat_name=chat_name, access_hash=chat.chats[0].access_hash
    )

    return chat_info


async def get_chat_users(chat: ChatInformation, client: TelegramClient):
    offset = 0
    chat_object = InputChannel(chat.chat_id, chat.access_hash)
    all_participants = []
    while True:
        participants: list[User] = (
            await client(
                GetParticipantsRequest(
                    chat_object,
                    ChannelParticipantsSearch(""),
                    offset,
                    limit,
                    chat.access_hash,
                )
            )
        ).users

        if not participants:
            break

        offset += len(participants)

        all_participants.extend(
            [
                UserInformation(
                    first_name=participant.first_name,
                    last_name=participant.last_name,
                    username="@" + participant.username if participant.username else participant.username,
                    phone=participant.phone,
                )
                for participant in participants
                if not participant.bot
            ]
        )

        await sleep(2)

    print(f"Gathered {len(all_participants)} from {chat.chat_name}")

    with open(f"users_{chat.chat_name}.csv", "w", encoding="UTF-16") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=UserInformation.get_field_names())
        writer.writeheader()
        for participant in all_participants:
            writer.writerow(participant.to_dict)

    return all_participants


async def main():
    client: TelegramClient = await TelegramClient("current-session", api_id, api_hash).start(
        bot_token=bot_token
    )
    async with client:
        tasks = []
        for chat_name in chat_names:
            chat_info = await get_chat_information(chat_name, client)
            tasks.append(asyncio.create_task(get_chat_users(chat_info, client)))
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
