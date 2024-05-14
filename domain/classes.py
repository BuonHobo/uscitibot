from __future__ import annotations

import difflib
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from requests import get


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

    def get_channel(self, id: int) -> Channel:
        return self._channels.get(id)

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
        self._monitor.unmonitor()
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
    def is_updated(self) -> None | str:
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

    @abstractmethod
    def unmonitor(self):
        pass


class ETagMonitor(Monitor):
    data_dir = Path("./data/ETagMonitor")

    def __init__(self, website: Website) -> None:
        super().__init__(website)
        self._etag: None | str = None
        self._last_update: None | datetime = None
        self._updated: bool = False
        self._diff: None | str = None
        self._content: str = ""
        self._target: Path = self.data_dir.joinpath(self._website.get_name() + ".html")
        self.load_content()

    def load_content(self):
        if Path(self.data_dir).exists() and self._target.exists():
            self._content = self._target.read_text(encoding="utf-8")
        else:
            try:
                self._content = get(self._website.get_url(),timeout=10).text
                self.save_content()
            except Exception:
                self._content = ""

    def save_content(self):
        if not Path(self.data_dir).exists():
            os.mkdir(self.data_dir)
        self._target.write_text(self._content)

    def check_update(self):
        headers = {
            "If-None-Match": self._etag,
            "If-Modified-Since": self._last_update.strftime("%a, %d %b %Y %H:%M:%S GMT") if self._last_update else None,
        }

        print(f"[{datetime.now()}] Sending request to {self._website.get_url()} with headers: {headers}")

        res = get(self._website.get_url(), headers=headers, timeout=10)

        if not res.ok:
            return

        if self._etag is None:
            if "ETag" in res.headers:
                self._etag = res.headers["ETag"]

        if self._last_update is None:
            self._last_update = datetime.utcnow()

        if res.status_code != 304:
            print("Update detected")
            self._updated = True
            if "ETag" in res.headers:
                self._etag = res.headers["ETag"]
            self._last_update = datetime.utcnow()
            if self._content != "":
                self._diff = "\n".join(
                    difflib.unified_diff(self._content.splitlines(), res.text.splitlines(), fromfile="Before",
                                         tofile="After"))
            else:
                self._diff = None
            self._content = res.text
            self.save_content()

    def is_updated(self) -> None | str:
        res = self._updated
        self._updated = False
        if res:
            return self._diff
        else:
            return None

    def get_data(self) -> str:
        return f"{self._website.get_url()},{self._etag},{self._updated},{self._last_update.isoformat()}"

    def set_data(self, data: list[str]):
        etag = data[1]
        if etag != "None":
            self._etag = f'"{etag}"'
        updated = data[2]
        self._updated = updated == "True"
        try:
            last_update = data[3]
            self._last_update = datetime.fromisoformat(last_update)
        except IndexError as e:
            return
        try:
            content = data[4]
            self._content = content
        except IndexError as e:
            return

    def unmonitor(self):
        os.remove(self._target)
