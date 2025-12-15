from __future__ import annotations
import pygame
from enum import Enum
from dataclasses import dataclass
from typing import override
import time
import random
import json

from .entity import Entity
from src.sprites import Sprite
from src.core import GameManager
from src.core.services import input_manager, scene_manager, resource_manager
from src.utils import GameSettings, Direction, Position, PositionCamera, Logger
from src.interface.components import Button


class SellerClassification(Enum):
    STATIONARY = "stationary"


@dataclass
class IdleMovement:
    """Stationary or idle movement logic (stub)."""
    def update(self, seller: "Seller", dt: float) -> None:
        pass


class Seller(Entity):
    classification: SellerClassification
    max_tiles: int | None
    _movement: IdleMovement
    warning_sign: Sprite
    detected: bool
    los_direction: Direction
    hitbox: pygame.Rect
    shop_open: bool
    shop_items: list[dict[str, object]]
    shop_buttons: list[Button]
    shop_info: str
    font: pygame.font.Font

    @override
    def __init__(
        self,
        x: float,
        y: float,
        game_manager: GameManager,
        classification: SellerClassification = SellerClassification.STATIONARY,
        max_tiles: int | None = 2,
        facing: Direction | None = None,
    ) -> None:
        super().__init__(x, y, game_manager)

        # Seller properties
        self.classification = classification
        self.max_tiles = max_tiles
        self.detected = False

        # Hitbox
        self.hitbox = pygame.Rect(x, y, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)

        # Idle movement
        self._movement = IdleMovement()
        if facing is None and classification == SellerClassification.STATIONARY:
            facing = Direction.DOWN
        self._set_direction(facing)

        # Warning sign
        self.warning_sign = Sprite(
            "exclamation.png",
            (GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2),
        )
        self.warning_sign.update_pos(
            Position(x + GameSettings.TILE_SIZE // 4, y - GameSettings.TILE_SIZE // 2)
        )

        # Shop UI
        self.panel_w, self.panel_h = 900, 500
        self.overlay_rect = pygame.Rect(
            (GameSettings.SCREEN_WIDTH - self.panel_w) // 2,
            (GameSettings.SCREEN_HEIGHT - self.panel_h) // 2,
            self.panel_w,
            self.panel_h,
        )
        self.panel_sprite = Sprite("UI/raw/UI_Flat_Frame03a.png", (self.panel_w, self.panel_h))
        self.panel_sprite.update_pos(Position(self.overlay_rect.x, self.overlay_rect.y))

        self.shop_open = False
        self.shop_items = [
            {"name": "Potion", "price": 1,"sprite_path": "ingame_ui/potion.png","text":"Potion: 1 coin","y":230},
            {"name": "Pokeball", "price": 3,"sprite_path": "ingame_ui/ball.png","text":"Pokeball: 3 coin","y":290},
        ]
        self.shop_info = "Welcome to the shop! What do you want to buy?"
        self.shop_buttons: list[Button] = []

        # Back button
        self.back_button = Button(
            "UI/button_back.png",
            "UI/button_back_hover.png",
            self.overlay_rect.x + 60,
            self.overlay_rect.y + 30,
            60,
            50,
            self._close_shop,
        )

        # Font
        self.font = pygame.font.SysFont("Arial", 24)

    @override
    def update(self, dt: float) -> None:
        """Update seller movement, detection, and shop UI."""
        # Cooldown/ignore logic
        if getattr(self, "ignore_until", 0) > time.time():
            self._movement.update(self, dt)
            self._update_animation()
            return

        last_end = getattr(scene_manager, "last_battle_end", 0)
        global_cooldown = getattr(scene_manager, "last_battle_cooldown", 0.0)
        if last_end and (time.time() - last_end) < global_cooldown:
            self._movement.update(self, dt)
            self._update_animation()
            return

        # Normal update
        self._movement.update(self, dt)
        self._check_player_detection()
        self._update_animation()

        # Open shop if detected and player presses Space/E
        if self.detected and not self.shop_open:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE] or keys[pygame.K_e]:
                Logger.info("Seller → Opening shop")
                self.open_shop()

        # Update shop buttons
        if self.shop_open:
            for btn in self.shop_buttons:
                btn.update(dt)

        # Close shop if ESC pressed
        if pygame.key.get_pressed()[pygame.K_ESCAPE]:
            self._close_shop()

    def _update_animation(self) -> None:
        """Update animation position and hitbox."""
        self.animation.update_pos(self.position)
        self.hitbox.topleft = (self.position.x, self.position.y)

    def open_shop(self) -> None:
        """Open shop and create buttons for items."""
        self.shop_open = True
        self.shop_buttons.clear()
        self.shop_buttons.append(self.back_button)

        y = 230
        for item in self.shop_items:
            def make_click(item=item):
                def callback():
                    coins = self.game_manager.bag.get_coins()
                    if coins < item["price"]:
                        self.shop_info = "Not enough coins!"
                        return
                    # Deduct coins
                    self.game_manager.bag.update_item({"count": coins - item["price"]}, id=1)
                    # Add item to bag
                    for idx, it in enumerate(self.game_manager.bag._items_data):
                        if it["name"] == item["name"]:
                            self.game_manager.bag.update_item({"count": it["count"] + 1}, idx)
                            break
                    self.shop_info = f"Bought {item['name']}!"
                return callback

            btn = Button(
                "UI/button_shop.png",
                "UI/button_shop_hover.png",
                self.overlay_rect.x + 520,
                y,
                50,
                50,
                make_click(),
            )
            self.shop_buttons.append(btn)
            y += 60

    def _close_shop(self) -> None:
        self.shop_open = False
        self.shop_info = "Welcome to the shop! What do you want to buy?"
        self.detected = False

    @override
    def draw(self, screen: pygame.Surface, camera: PositionCamera) -> None:
        super().draw(screen, camera)
        if self.detected:
            self.warning_sign.draw(screen, camera)
        if GameSettings.DRAW_HITBOXES:
            los_rect = self._get_los_rect()
            if los_rect:
                pygame.draw.rect(screen, (255, 255, 0), camera.transform_rect(los_rect), 1)

        if self.shop_open:
            # Dim background
            dim = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 150))
            screen.blit(dim, (0, 0))

            # Panel
            self.panel_sprite.draw(screen)

            # Title & info
            screen.blit(self.font.render("Shop", True, (255, 255, 0)), (330, 150))
            screen.blit(self.font.render(self.shop_info, True, (255, 255, 255)), (260, 400))

            for btn in self.shop_buttons: btn.draw(screen)

            for data in self.shop_items:
                sprite_path=data["sprite_path"]
                text=self.font.render(
                data["text"], True, (255, 255, 255)
                )
                y=data["y"]

                img = resource_manager.get_image(sprite_path)
                img = pygame.transform.scale(img, (50,50))
                screen.blit(img, (260, y ))
                screen.blit(text, (350, y+15))



            # Coins
            coins_text = self.font.render(
                f"coins: ${self.game_manager.bag.get_coins()}", True, (255, 255, 255)
            )
            screen.blit(coins_text, (260, 440))

    # ----------------------------------------------------------
    # Helper methods
    # ----------------------------------------------------------
    def _set_direction(self, direction: Direction) -> None:
        self.direction = direction
        mapping = {
            Direction.RIGHT: "right",
            Direction.LEFT: "left",
            Direction.DOWN: "down",
            Direction.UP: "up",
        }
        self.animation.switch(mapping.get(direction, "down"))
        self.los_direction = self.direction

    def _get_los_rect(self) -> pygame.Rect | None:
        tile = GameSettings.TILE_SIZE
        length = 6 * tile
        width = tile // 2
        x, y = self.position.x, self.position.y

        if self.los_direction == Direction.UP:
            return pygame.Rect(x + tile // 4, y - length, width, length)
        if self.los_direction == Direction.DOWN:
            return pygame.Rect(x + tile // 4, y + tile, width, length)
        if self.los_direction == Direction.LEFT:
            return pygame.Rect(x - length, y + tile // 4, length, width)
        if self.los_direction == Direction.RIGHT:
            return pygame.Rect(x + tile, y + tile // 4, length, width)
        return None

    def _check_player_detection(self) -> None:
        player = self.game_manager.player
        if not player:
            self.detected = False
            return

        # Collision
        if self.hitbox.colliderect(player.animation.rect):
            self.detected = True
            return

        # LOS detection
        los_rect = self._get_los_rect()
        self.detected = los_rect.colliderect(player.animation.rect) if los_rect else False

    def get_hitbox(self) -> pygame.Rect:
        return self.hitbox

    @classmethod
    @override
    def from_dict(cls, data: dict, game_manager: GameManager) -> "Seller":
        classification = SellerClassification(data.get("classification", "stationary"))
        max_tiles = data.get("max_tiles")
        facing_val = data.get("facing")
        facing: Direction | None = None
        if facing_val:
            facing = Direction[facing_val] if isinstance(facing_val, str) else facing_val
        if facing is None and classification == SellerClassification.STATIONARY:
            facing = Direction.DOWN

        return cls(
            data["x"] * GameSettings.TILE_SIZE,
            data["y"] * GameSettings.TILE_SIZE,
            game_manager,
            classification,
            max_tiles,
            facing,
        )

    @override
    def to_dict(self) -> dict[str, object]:
        base = super().to_dict()
        base.update({
            "classification": self.classification.value,
            "facing": self.direction.name,
            "max_tiles": self.max_tiles,
        })
        return base
