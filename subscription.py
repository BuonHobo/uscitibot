import requests
from hashlib import md5


class Subscription:
    def __init__(self, nome, website,checksum=None) -> None:
        self.nome: str = nome
        self.website: str = website
        self.iscritti: set[int] = set()
        self.last_checksum: None | str = checksum

        self.check_update()

    def add_sub(self, subscriber: int) -> bool:
        """Returns True if this subscriber was not in the list"""
        if subscriber in self.iscritti:
            return False
        self.iscritti.add(subscriber)
        return True

    def rem_sub(self, subscriber: int) -> bool:
        """Returns True if this subscriber was in the list"""
        try:
            self.iscritti.remove(subscriber)
        except KeyError:
            return False
        else:
            return True

    def check_update(self) -> bool:
        """Returns True if there was an old checksum and the new one is different"""
        response = requests.get(self.website)
        new_checksum = (
            md5(response.text.encode(response.encoding)).hexdigest()
            if response.status_code == 200
            else None
        )

        changed: bool = False

        if (self.last_checksum is not None) and (self.last_checksum != new_checksum):
            changed = True

        self.last_checksum = new_checksum
        return changed

    def __eq__(self, __o: object) -> bool:
        if __o is not None and type(__o) == Subscription:
            return self.nome == __o.nome

    def __ne__(self, __o: object) -> bool:
        if __o is not None and type(__o) == Subscription:
            return self.nome != __o.nome

    def __str__(self) -> str:
        return f"{self.nome} at '{self.website}'"

    def __hash__(self) -> int:
        self.nome.__hash__()