import pygame as pg
import json
from src.utils import GameSettings
from src.utils.definition import Monster, Item


class Bag:
    _monsters_data: list[dict]
    _items_data: list[dict]

    def __init__(
        self,
        monsters_data: list[dict] | None = None,
        items_data: list[dict] | None = None,
    ):
        self._monsters_data = monsters_data if monsters_data else []
        self._items_data = items_data if items_data else []
        self.sel = 0
        self.evolute = False

    def update(self, dt: float):
        pass

    def draw(self, screen: pg.Surface):
        pass

    def to_dict(self) -> dict[str, object]:
        return {"monsters": self._monsters_data, "items": self._items_data}

    def add_monster(self, monster: dict) -> None:
        self._monsters_data.append(monster)

    def add_item(self, item: dict) -> None:
        self._items_data.append(item)

    def get_coins(self) -> int:
        """從 Bag 的 items 找 Coins 數量"""
        for item in self._items_data:
            if item.get("name") == "Coins":
                return item.get("count", 0)
        return 0

    def get_monster(self, id):
        return self._monsters_data[id]

    def update_monster(self, monster: dict, id):
        self._monsters_data[id].update(monster)

    def update_item(self, item, id):
        self._items_data[id].update(item)

    def delete_monster(self, id):
        self._monsters_data.pop(id)

    def sum_of_monster(self):
        return len(self._monsters_data)

    def change_pkmsel(self, id):
        self.sel = id

    def get_pkmsel(self):
        return self.sel

    def level_up(self):
        if self._monsters_data[self.sel]["exp"] < 150:
            return
        self._monsters_data[self.sel]["exp"] -= 150
        self._monsters_data[self.sel]["level"] += 1

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Bag":
        return cls(
            monsters_data=data.get("monsters", []), items_data=data.get("items", [])
        )
