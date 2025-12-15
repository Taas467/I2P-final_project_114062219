import pygame as pg
from src.scenes.scene import Scene
from src.core.services import scene_manager, resource_manager
from src.interface.components import Button
from src.sprites import Sprite
from src.utils import Position, GameSettings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.managers.game_manager import GameManager


class BagScene(Scene):
    def __init__(self):
        super().__init__()

        # panel 設定
        self.panel_w, self.panel_h = 900, 500
        self.overlay_rect = pg.Rect(
            (GameSettings.SCREEN_WIDTH - self.panel_w) // 2,
            (GameSettings.SCREEN_HEIGHT - self.panel_h) // 2,
            self.panel_w,
            self.panel_h,
        )

        # 背景 Sprite
        self.panel_sprite = Sprite(
            "UI/raw/UI_Flat_Frame03a.png", (self.panel_w, self.panel_h)
        )
        self.panel_sprite.update_pos(Position(self.overlay_rect.x, self.overlay_rect.y))

        # 返回按鈕
        self.close_button = Button(
            "UI/button_back.png",
            "UI/button_back_hover.png",
            self.overlay_rect.x + 20,
            self.overlay_rect.y + 20,
            50,
            35,
            self._on_close,
        )
        self.del_button = []

        # 字型
        try:
            self.title_font = pg.font.Font(None, 28)
            self.item_font = pg.font.Font(None, 20)
        except Exception:
            self.title_font = None
            self.item_font = None

        # 遊戲管理器 (在 enter() 時決定)
        self.game_manager: "GameManager | None" = None

        # 顯示參數
        self.padding = 12
        self.line_height = 22

    def enter(self):
        """找出 game_manager（SceneManager 會把 game 放在 pending_bag 或 previous_scene 裡）"""
        gm = getattr(scene_manager, "pending_bag", None)
        if gm is None:
            prev = getattr(scene_manager, "previous_scene", None)
            gm = getattr(prev, "game_manager", None)

        self.game_manager = gm
        self.bag = gm.bag if gm else None

        self.del_button = []
        self._create_delete_buttons()
        self.select_button = []
        self._create_select_buttons()

    def exit(self):
        """清掉暫存的 pending_bag"""
        if hasattr(scene_manager, "pending_bag"):
            delattr(scene_manager, "pending_bag")

    def _on_close(self):
        scene_manager.change_scene("game")

    def update(self, dt: float) -> None:
        self.close_button.update(dt)

        for btn in self.del_button:
            btn.update(dt)

        for btn in self.select_button:
            btn.update(dt)

        for e in pg.event.get():
            if e.type == pg.KEYDOWN and e.key in (pg.K_ESCAPE, pg.K_BACKSPACE):
                scene_manager.change_scene("game")

    def draw(self, screen: pg.Surface) -> None:
        # 半透明背景
        dim = pg.Surface(screen.get_size(), pg.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        screen.blit(dim, (0, 0))

        # Panel + buttons
        self.panel_sprite.draw(screen)
        self.close_button.draw(screen)
        for btn in self.del_button:
            btn.draw(screen)
        for btn in self.select_button:
            btn.draw(screen)
        # 主內容
        self._draw_bag_content(screen)

    def _delete_monster(self, idx: int):
        if not self.game_manager:
            return
        if self.game_manager.bag.sum_of_monster() <= 1:
            return
        self.game_manager.bag.delete_monster(idx)
        self.del_button.clear()
        self._create_delete_buttons()
        self.select_button.clear()
        self._create_select_buttons()
        print("Deleted monster:", idx)

    def _on_select_monster(self, idx: int):
        if not self.game_manager:
            return
        self.select_button .clear()
        self._create_select_buttons()
        self.game_manager.bag.change_pkmsel(idx)
        print("Selected monster:", idx)

    # -------------------------------------------------------------------------
    #  ★ 這裡開始就是原本 BackpackOverlay 的邏輯
    # -------------------------------------------------------------------------
    def _draw_bag_content(self, screen):
        if not self.game_manager:
            return

        bag = getattr(self.game_manager, "bag", None)
        if not bag:
            return

        monsters = getattr(bag, "_monsters_data", [])
        items = getattr(bag, "_items_data", [])

        # ==== UI 位置 ====
        px = self.overlay_rect.x
        py = self.overlay_rect.y
        pw = self.overlay_rect.w
        ph = self.overlay_rect.h

        padding = 12
        line_height = 22

        # Title
        font_title = pg.font.Font(None, 28)
        screen.blit(
            font_title.render("Bag", True, (0, 0, 0)),
            (px + padding + 70, py + padding + 18),
        )

        # Content area
        content_x = px + padding
        content_y = py + padding + 30
        content_w = pw - padding * 2

        col_gap = 10
        col_w = (content_w - col_gap) // 2
        font_item = pg.font.Font(None, 20)

        # Section titles
        screen.blit(
            font_item.render("Monsters", True, (0, 0, 0)),
            (content_x + 25, content_y + 30),
        )
        screen.blit(
            font_item.render("Items", True, (0, 0, 0)),
            (content_x + col_w + col_gap + 25, content_y + 30),
        )

        thumb_w, thumb_h = 40, 40
        # ==== Draw Monsters ====
        y = content_y + line_height + 30
        for idx, m in enumerate(monsters):
            text = m.get("name", "Unknown")
            lvl = m.get("level")
            hp = m.get("hp")
            exp = m.get("exp")

            if lvl is not None:
                text += f" (Lv{lvl})"
            if hp is not None:
                text += f" HP:{hp}"
            if exp is not None:
                text += f" EXP:{exp}"
            # Thumbnail
            sprite_path = m.get("sprite_path")
            if sprite_path:
                try:
                    img = resource_manager.get_image(sprite_path)
                    img = pg.transform.scale(img, (thumb_w, thumb_h))
                    screen.blit(img, (content_x + 18, y - 4))
                except:
                    pass

            # Text
            screen.blit(
                font_item.render(text, True, (10, 10, 10)),
                (content_x + thumb_w + 25, y + 20),
            )

            y += max(line_height, thumb_h)

        # ==== Draw Items ====
        y = content_y + line_height + 20
        for it in items:
            text = it.get("name", "Unknown")
            cnt = it.get("count")
            if cnt is not None:
                text += f" x{cnt}"

            sprite_path = it.get("sprite_path")
            if sprite_path:
                try:
                    img = resource_manager.get_image(sprite_path)
                    img = pg.transform.scale(img, (thumb_w, thumb_h))
                    screen.blit(img, (content_x + col_w + col_gap + 18, y + 6))
                except:
                    pass

            screen.blit(
                font_item.render(text, True, (10, 10, 10)),
                (content_x + col_w + col_gap + thumb_w + 32, y + 25),
            )

            y += max(line_height, thumb_h)

    def _create_delete_buttons(self):
        bag = getattr(self.game_manager, "bag", None)
        if not bag:
            return
        monsters = getattr(bag, "_monsters_data", [])
        if len(monsters) <= 1:
            return
        # UI 位置
        px = self.overlay_rect.x
        py = self.overlay_rect.y
        pw = self.overlay_rect.w
        ph = self.overlay_rect.h
        padding = 12
        line_height = 22
        content_x = px + padding
        content_y = py + padding + 30
        content_w = pw - padding * 2
        col_gap = 10
        col_w = (content_w - col_gap) // 2

        thumb_h = 40

        y = content_y + line_height + 30
        for idx, m in enumerate(monsters):
            btn = Button(
                "UI/button_back.png",
                "UI/button_back_hover.png",
                content_x + col_w - 80,
                y + 10,
                30,
                30,
                lambda idx=idx: self._delete_monster(idx),
            )
            self.del_button.append(btn)
            y += max(line_height, thumb_h)

    def _create_select_buttons(self):
        bag = getattr(self.game_manager, "bag", None)
        if not bag:
            return
        monsters = getattr(bag, "_monsters_data", [])
        if not monsters:
            return

        px = self.overlay_rect.x
        py = self.overlay_rect.y
        pw = self.overlay_rect.w
        ph = self.overlay_rect.h
        padding = 12
        line_height = 22
        content_x = px + padding
        content_y = py + padding + 30
        content_w = pw - padding * 2
        col_gap = 10
        col_w = (content_w - col_gap) // 2

        thumb_h = 40
        y = content_y + line_height + 30

        # 右移 40px
        for idx, m in enumerate(monsters):
            btn = Button(
                "UI/button_play.png",
                "UI/button_play_hover.png",
                content_x + col_w - 40,  
                y + 10,
                30,
                30,
                lambda idx=idx: self._on_select_monster(idx),
            )
            self.select_button.append(btn)
            y += max(line_height, thumb_h)
