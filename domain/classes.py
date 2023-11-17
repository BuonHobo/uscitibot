from __future__ import annotations
from abc import ABC, abstractmethod
from requests import head


class Base:
    def __init__(self, servers: list[Server] = []) -> None:
        self._servers: dict[int, Server] = {}
        for server in servers:
            self.add_server(server)

    def add_server(self, server: Server):
        self._servers[server.get_id()] = server

    def get_servers(self) -> list[Server]:
        return list(self._servers.values())

    def get_server(self, id: int) -> Server | None:
        return self._servers.get(id)


class Server:
    def __init__(self, id: int, default_channel: Channel | None = None) -> None:
        self._id = id
        self._channels: dict[int, Channel] = {}
        self._users: dict[int, User] = {}

    def add_channel(self, channel: Channel):
        self._channels[channel.get_id()] = channel

    def add_user(self, user: User):
        self._users[user.get_id()] = user

    def get_user(self, id: int) -> User | None:
        return self._users.get(id)

    def get_channels(self) -> list[Channel]:
        return list(self._channels.values())

    def get_id(self) -> int:
        return self._id

    def get_websites(self) -> list[Website]:
        res: list[Website] = []
        for channel in self.get_channels():
            res.extend(channel.get_websites())

        return res

    def get_website(self, name: str) -> Website | None:
        for channel in self.get_channels():
            res = channel.get_website(name)
            if res is not None:
                return res

    def remove_website(self, name: str) -> Website | None:
        for channel in self.get_channels():
            res = channel.remove_website(name)
            if res is not None:
                return res


class Channel:
    def __init__(self, id: int, server: Server) -> None:
        self._websites: dict[str, Website] = {}
        self._id = id
        self._server = server
        server.add_channel(self)

    def add_website(self, website: Website):
        self._websites[website.get_name()] = website

    def get_id(self) -> int:
        return self._id

    def get_websites(self) -> list[Website]:
        return list(self._websites.values())

    def get_website(self, name: str) -> Website | None:
        return self._websites.get(name)

    def get_server(self) -> Server:
        return self._server

    def remove_website(self, name: str) -> Website | None:
        if name not in self._websites:
            return None
        website = self._websites.pop(name)
        website.removal()
        return website

    def get_hyperlink(self) -> str:
        return f"<#{self.get_id()}>"


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
        self._users: dict[int, User] = {}
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
        self._users[user.get_id()] = user

    def get_users(self) -> list[User]:
        return list(self._users.values())

    def get_hyperlink(self) -> str:
        return f"[{self.get_name()}]({self.get_url()})"

    def removal(self):
        for user in self.get_users():
            user.remove_website(self._name)


class User:
    def __init__(self, id: int, website: Website | None = None) -> None:
        self.__id = id
        self._websites: dict[str, Website] = {}
        if website:
            self.add_website(website)

    def register(self, website: Website):
        website.get_channel().get_server().add_user(self)

    def get_id(self) -> int:
        return self.__id

    def add_website(self, website: Website):
        self._websites[website.get_name()] = website
        website.add_user(self)
        self.register(website)

    def remove_website(self, name: str) -> Website | None:
        if name not in self._websites:
            return None
        return self._websites.pop(name)

    def get_websites(self) -> list[Website]:
        return list(self._websites.values())

    def get_hyperlink(self) -> str:
        return f"<@{self.get_id()}>"


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
        res = head(self._website.get_url(), headers={"If-None-Match": str(self._etag)})

        if not res.ok:
            return

        if self._etag is None:
            self._etag = res.headers["ETag"]
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
