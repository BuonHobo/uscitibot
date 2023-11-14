from pathlib import Path
from domain.classes import Channel, Server, User, Website, Monitor
import domain.classes


class CSVDomainLoader:
    @staticmethod
    def load(folder: Path) -> list[Server]:
        data: dict[str, list[str]] = {
            "servers.csv": [],
            "channels.csv": [],
            "websites.csv": [],
            "users.csv": [],
            "users_websites.csv": [],
        }

        monitor_data: dict[str, dict[str, str]] = {}

        for file, content in data.items():
            with folder.joinpath(file).open("r") as f:
                content.extend([line.strip() for line in f.readlines()[1:]])

        for file in folder.joinpath("monitors").iterdir():
            with file.open("r") as f:
                monitor_data = {
                    file.name.removesuffix(".csv"): {
                        line.split(",")[0]: line.strip() for line in f.readlines()
                    }
                }

        res = CSVDomainLoader.load_servers(data)
        res = list(res.values())
        CSVDomainLoader.load_monitors(res, monitor_data)
        return res

    @staticmethod
    def load_servers(data: dict[str, list[str]]) -> dict[int, Server]:
        servers: dict[int, Server] = {}
        defaults: dict[Server, int] = {}
        for line in data["servers.csv"]:
            id, default_channel = line.split(",")
            id = int(id)
            server = Server(id)
            servers[id] = server
            if default_channel != "None":
                defaults[server] = int(default_channel)

        channels = CSVDomainLoader.load_channels(servers, data)
        for server, defa in defaults.items():
            server.set_default_channel(channels[defa])

        return servers

    @staticmethod
    def load_channels(
        servers: dict[int, Server], data: dict[str, list[str]]
    ) -> dict[int, Channel]:
        channels: dict[int, Channel] = {}
        for line in data["channels.csv"]:
            chid, servid = line.split(",")
            chid = int(chid)
            servid = int(servid)
            channels[chid] = Channel(chid, servers[servid])

        CSVDomainLoader.load_websites(channels, data)
        return channels

    @staticmethod
    def load_websites(channels: dict[int, Channel], data: dict[str, list[str]]):
        websites: dict[str, Website] = {}
        for line in data["websites.csv"]:
            url, name, chid, monitor_class = line.split(",")
            chid = int(chid)
            websites[url] = Website(
                name, url, channels[chid], getattr(domain.classes, monitor_class)
            )
        CSVDomainLoader.load_users(websites, data)

    @staticmethod
    def load_users(websites: dict[str, Website], data: dict[str, list[str]]):
        users: dict[int, User] = {}
        for line in data["users.csv"]:
            id = int(line)
            users[id] = User(id)

        for line in data["users_websites.csv"]:
            usid, weburl = line.split(",")
            usid = int(usid)
            users[usid].add_website(websites[weburl])

    @staticmethod
    def load_monitors(servers: list[Server], monitor_data: dict[str, dict[str, str]]):
        websites: list[Website] = []

        for server in servers:
            for channel in server.get_channels():
                websites.extend(channel.get_websites())

        for website in websites:
            monitor = website.get_monitor()
            monitor_class = monitor.__class__.__name__
            monitor.set_data(monitor_data[monitor_class][website.get_url()])


class CSVDomainSaver:
    @staticmethod
    def save(servers: list[Server], folder: Path):
        data: dict[str, list[str]] = {
            "servers.csv": [],
            "channels.csv": [],
            "websites.csv": [],
            "users.csv": [],
            "users_websites.csv": [],
        }

        CSVDomainSaver.save_servers(servers, data)
        folder.joinpath("monitors").mkdir(exist_ok=True)

        for filename, lines in data.items():
            with folder.joinpath(filename).open("w") as f:
                f.writelines(lines)

    @staticmethod
    def save_servers(servers: list[Server], data: dict[str, list[str]]):
        channels: list[Channel] = []
        data["servers.csv"].append(f"server id, default channel id (if present)\n")
        for server in servers:
            channels.extend(server.get_channels())
            default_channel = server.get_default_channel()
            data["servers.csv"].append(
                f"{server.get_id()},{default_channel.get_id() if default_channel is not None else None}\n"
            )

        CSVDomainSaver.save_channels(channels, data)

    @staticmethod
    def save_channels(channels: list[Channel], data: dict[str, list[str]]):
        websites: list[Website] = []
        data["channels.csv"].append(f"channel id, server id\n")
        for channel in channels:
            websites.extend(channel.get_websites())
            data["channels.csv"].append(
                f"{channel.get_id()},{channel.get_server().get_id()}\n"
            )

        CSVDomainSaver.save_websites(websites, data)

    @staticmethod
    def save_websites(websites: list[Website], data: dict[str, list[str]]):
        users: list[User] = []
        monitors: list[Monitor] = []
        data["websites.csv"].append(
            f"website url, website name, channel id, monitor class\n"
        )
        for website in websites:
            users.extend(website.get_users())
            monitors.append(website.get_monitor())
            data["websites.csv"].append(
                f"{website.get_url()},{website.get_name()}, {website.get_channel().get_id()},{website.get_monitor().__class__.__name__}\n"
            )

        for monitor in monitors:
            filename = f"monitors/{monitor.__class__.__name__}.csv"
            if filename not in data:
                data[filename] = []
            data[filename].append(f"{monitor.get_data()}\n")

        CSVDomainSaver.save_users(users, data)

    @staticmethod
    def save_users(users: list[User], data: dict[str, list[str]]):
        data["users.csv"].append(f"user id\n")
        for user in users:
            data["users.csv"].append(f"{user.get_id()}\n")
        data["users_websites.csv"].append(f"user id, website url\n")
        for user in users:
            for website in user.get_websites():
                data["users_websites.csv"].append(
                    f"{user.get_id()},{website.get_url()}\n"
                )
