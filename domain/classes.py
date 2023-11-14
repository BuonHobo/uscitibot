from __future__ import annotations
from abc import ABC, abstractmethod
from requests import get


class Server:
    def __init__(self, id: int, default_channel: Channel | None = None) -> None:
        self._id = id
        self._channels: list[Channel] = []
        self._default_channel = default_channel

    def add_channel(self, channel: Channel):
        self._channels.append(channel)

    def get_channels(self) -> list[Channel]:
        return self._channels

    def get_default_channel(self) -> Channel | None:
        return self._default_channel

    def set_default_channel(self, channel: Channel):
        self._default_channel = channel

    def get_id(self) -> int:
        return self._id


class Channel:
    def __init__(self, id: int, server: Server) -> None:
        self._websites: list[Website] = []
        self._id = id
        self._server = server
        server.add_channel(self)

    def add_website(self, website: Website):
        self._websites.append(website)

    def get_id(self) -> int:
        return self._id

    def get_websites(self) -> list[Website]:
        return self._websites

    def get_server(self) -> Server:
        return self._server


class Website:
    def __init__(
        self,
        name: str,
        url: str,
        channel: Channel,
        monitor: type[Monitor],
    ) -> None:
        self._name = name
        self._url = url
        self._channel = channel
        channel.add_website(self)
        self._users: list[User] = []
        self._monitor: Monitor = monitor(self)

    def get_name(self) -> str:
        return self._name

    def get_url(self) -> str:
        return self._url

    def get_monitor(self) -> Monitor:
        return self._monitor

    def get_channel(self) -> Channel:
        return self._channel

    def add_user(self, user: User):
        self._users.append(user)

    def get_users(self) -> list[User]:
        return self._users


class User:
    def __init__(self, id: int) -> None:
        self.__id = id
        self._websites: list[Website] = []

    def get_id(self) -> int:
        return self.__id

    def add_website(self, website: Website):
        self._websites.append(website)
        website.add_user(self)

    def get_websites(self) -> list[Website]:
        return self._websites


class Monitor(ABC):
    @abstractmethod
    def __init__(self, website: Website) -> None:
        self._website = website

    @abstractmethod
    def is_updated(self) -> bool:
        pass

    @abstractmethod
    def check_update(self):
        pass

    @abstractmethod
    def get_data(self) -> str:
        pass

    @abstractmethod
    def set_data(self, data: str):
        pass


class ETagMonitor(Monitor):
    def __init__(self, website: Website) -> None:
        super().__init__(website)
        self._etag: None | str = None
        self._updated: bool = False

    def check_update(self):
        res = get(self._website.get_url(), headers={"If-None-Match": str(self._etag)})

        if not res.ok:
            return

        if res.status_code != 304:
            self._updated = True
            self._etag = res.headers["ETag"]

    def is_updated(self) -> bool:
        res = self._updated
        self._updated = False
        return res

    def get_data(self) -> str:
        return f"{self._website.get_url()},{self._etag},{self._updated}"

    def set_data(self, data: str):
        _, etag, updated = data.split(",")
        if etag != "None":
            self._etag = etag
        self._updated = updated == "True"
