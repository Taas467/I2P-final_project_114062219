from __future__ import annotations
import pygame
from enum import Enum
from dataclasses import dataclass
from typing import override
import time

from .entity import Entity
from src.sprites import Sprite
from src.core import GameManager
from src.core.services import input_manager , scene_manager
from src.utils import GameSettings, Direction, Position, PositionCamera,Logger
from types import SimpleNamespace
import random
import json
class EnemyTrainerClassification(Enum):
    STATIONARY = "stationary"

@dataclass
class IdleMovement:
    def update(self, enemy: "EnemyTrainer", dt: float) -> None:
        return

class EnemyTrainer(Entity):
    classification: EnemyTrainerClassification
    max_tiles: int | None
    _movement: IdleMovement
    warning_sign: Sprite
    detected: bool
    los_direction: Direction
    hitbox: pygame.Rect

    @override
    def __init__(
        self,
        x: float,
        y: float,
        game_manager: GameManager,
        classification: EnemyTrainerClassification = EnemyTrainerClassification.STATIONARY,
        max_tiles: int | None = 2,
        facing: Direction | None = None,
    ) -> None:
        super().__init__(x, y, game_manager)
        self.classification = classification
        self.max_tiles = max_tiles
        self.detected = False

        # Hitbox
        self.hitbox = pygame.Rect(x, y, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)

        # Movement
        if classification == EnemyTrainerClassification.STATIONARY:
            self._movement = IdleMovement()
            if facing is None:
                facing = Direction.DOWN
            self._set_direction(facing)

        # Warning sign
        self.warning_sign = Sprite(
            "exclamation.png", 
            (GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2)
        )
        self.warning_sign.update_pos(
            Position(x + GameSettings.TILE_SIZE // 4, y - GameSettings.TILE_SIZE // 2)
        )

    @override
    def update(self, dt: float) -> None:
        # 若 NPC 被指定短暫忽略（例如剛結束的戰鬥觸發），則在 ignore_until 前跳過偵測
        if getattr(self, "ignore_until", 0) > time.time():
            # 仍需更新移動/動畫等，但不進行戰鬥偵測
            self._movement.update(self, dt)
            self.animation.update_pos(self.position)
            self.hitbox.topleft = (self.position.x, self.position.y)
            return

        # 補充：全域 last_battle_end cooldown（備援，若 engine 設定此值）
        last_end = getattr(scene_manager, "last_battle_end", 0)
        global_cooldown = getattr(scene_manager, "last_battle_cooldown", 0.0)
        if last_end and (time.time() - last_end) < global_cooldown:
            # 在全域 cooldown 時段內不觸發戰鬥（但繼續一般更新）
            self._movement.update(self, dt)
            self.animation.update_pos(self.position)
            self.hitbox.topleft = (self.position.x, self.position.y)
            return

        # 原本的移動/偵測邏輯（繼續執行）
        self._movement.update(self, dt)

        
        self._check_player_detection()

       
        self.animation.update_pos(self.position)
        self.hitbox.topleft = (self.position.x, self.position.y)
        # 當偵測到玩家並顯示警告標誌時，如果玩家按下互動鍵（預設 Space 或 E），切換到戰鬥場景
        if self.detected:
            pressed = False
            keys = pygame.key.get_pressed()
            pressed = keys[pygame.K_SPACE] or keys[pygame.K_e]
            if pressed:
                try:
                    with open("src/pokemon.json", "r") as f:
                        pokemon_data = json.load(f)
                    if self.max_tiles==3:
                        candidates=pokemon_data.get("sp_candidates",[])
                    else:
                        candidates = pokemon_data.get("candidates", [])
                    wild = random.choice(candidates)
                    # Create a lightweight battle target object that BattleScene can read
                    target = SimpleNamespace()
                    target.game_manager = self.game_manager
                    target.name= wild.get("name","unknow")
                    target.base= wild.get("base",1)
                    target.level= wild.get("level",1)
                    target.property= wild.get("property","Normal")
                    target.sprite_path = wild.get("sprite_path")
                    target.is_wild = True

                    try:
                        setattr(scene_manager, "battle_target", target)
                        scene_manager.change_scene("battle")
                    except Exception:
                        Logger.warning("Failed to start wild battle via scene_manager")
                except Exception:
                    pass
                
    @override
    def draw(self, screen: pygame.Surface, camera: PositionCamera) -> None:
        super().draw(screen, camera)
        if self.detected:
            self.warning_sign.draw(screen, camera)
        if GameSettings.DRAW_HITBOXES:
            los_rect = self._get_los_rect()
            if los_rect:
                pygame.draw.rect(screen, (255, 255, 0), camera.transform_rect(los_rect), 1)

    def _set_direction(self, direction: Direction) -> None:
        self.direction = direction
        if direction == Direction.RIGHT:
            self.animation.switch("right")
        elif direction == Direction.LEFT:
            self.animation.switch("left")
        elif direction == Direction.DOWN:
            self.animation.switch("down")
        else:
            self.animation.switch("up")
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

        # 玩家碰撞檢測
        if self.hitbox.colliderect(player.animation.rect):
            self.detected = True
        else:
            # LOS 檢測
            los_rect = self._get_los_rect()
            if los_rect and los_rect.colliderect(player.animation.rect):
                self.detected = True
            else:
                self.detected = False

    def get_hitbox(self) -> pygame.Rect:
        return self.hitbox

    @classmethod
    @override
    def from_dict(cls, data: dict, game_manager: GameManager) -> "EnemyTrainer":
        classification = EnemyTrainerClassification(data.get("classification", "stationary"))
        max_tiles = data.get("max_tiles")
        facing_val = data.get("facing")
        facing: Direction | None = None
        if facing_val is not None:
            if isinstance(facing_val, str):
                facing = Direction[facing_val]
            elif isinstance(facing_val, Direction):
                facing = facing_val
        if facing is None and classification == EnemyTrainerClassification.STATIONARY:
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
        base: dict[str, object] = super().to_dict()
        base["classification"] = self.classification.value
        base["facing"] = self.direction.name
        base["max_tiles"] = self.max_tiles
        return base