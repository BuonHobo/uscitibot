from subscription import Subscription


class Watchlist:
    def __init__(self, channel: int, guild: int) -> None:
        self.guild: int = guild
        self.channel: int = channel
        self.monitoring: dict[str, Subscription] = {}

    def add_website(self, name: str, url: str) -> bool:
        """Returns True if this website was not in the list"""
        website = Subscription(name, url)
        if name in self.monitoring:
            return False
        self.monitoring[name] = website
        return True
    
    def _add(self,sub:Subscription):
        self.monitoring[sub.nome]=sub

    def rem_website(self, name: str) -> bool:
        """Returns True if this website was in the list"""
        try:
            self.monitoring.pop(name)
        except KeyError:
            return False
        else:
            return True

    def subscribe(self, user: int, name: str) -> bool:
        """Returns True if the user was successfully subscribed"""
        if name in self.monitoring:
            return self.monitoring[name].add_sub(user)
        else:
            return False

    def unsubscribe(self, user: int, name: str) -> bool:
        """Returns True if the user was successfully unsubscribed"""
        if name in self.monitoring:
            return self.monitoring[name].rem_sub(user)
        else:
            return False

    def __str__(self) -> str:
        output = ""
        for sub in self.monitoring:
            output += f"* {sub}\n"
        return output

    def __hash__(self) -> int:
        self.guild.__hash__()
