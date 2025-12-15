import pygame as pg
import threading
import time
import os

from src.scenes.scene import Scene
from src.core import GameManager, OnlineManager
from src.utils import Logger, PositionCamera, GameSettings, Position
from src.core.services import scene_manager, sound_manager, input_manager
from src.sprites import Sprite
from src.interface.components import Button

from typing import override

class GameScene(Scene):
    game_manager: GameManager
    online_manager: OnlineManager | None
    sprite_online: Sprite
    # volume slider for overlay
    volume_rect: pg.Rect
    volume_slider_rect: pg.Rect
    volume: float

    def __init__(self):
        super().__init__()
        # Game Manager
        manager = GameManager.load("saves/game0.json")
        if manager is None:
            Logger.error("Failed to load game manager")
            exit(1)
        self.game_manager = manager

        # Online Manager
        if GameSettings.IS_ONLINE:
            self.online_manager = OnlineManager()
        else:
            self.online_manager = None

        # UI overlay geometry (defined once)
        overlay_w, overlay_h = 420, 180
        self.overlay_rect = pg.Rect(
            (GameSettings.SCREEN_WIDTH - overlay_w) // 2,
            (GameSettings.SCREEN_HEIGHT - overlay_h) // 2,
            overlay_w,
            overlay_h,
        )
        self.overlay_visible = False
        self.bag_overlay_visible = False

        self.sprite_online = Sprite("ingame_ui/options1.png", (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
        # Setting panel sprite
        self.Gsetting_UI =Sprite(
            "UI/raw/UI_Flat_Frame03a.png", (overlay_w,overlay_h)
        )
        self.Gsetting_UI.update_pos(Position(self.overlay_rect.x, self.overlay_rect.y))

        # volume slider 放在 overlay 裡
        self.volume = getattr(sound_manager, "volume", 0.7)
        self.volume_rect = pg.Rect(
            self.overlay_rect.x + 40,
            self.overlay_rect.y + 70,
            self.overlay_rect.w - 80,
            20,
        )
        self.volume_slider_rect = pg.Rect(0, 0, 20, 30)
        self.update_slider_pos()

        # overlay control buttons
        self.button_close_overlay = Button(
            "UI/button_back.png",
            "UI/button_back_hover.png",
            self.overlay_rect.x + 20,
            self.overlay_rect.y + 20,
            50,
            35,
            self.close_overlay,
        )
        # overlay 的 Save / Load 按鈕
        self.save_button = Button(
            "UI/button_save.png",
            "UI/button_save_hover.png",
            self.overlay_rect.x + 160,
            self.overlay_rect.y + 20,
            60,
            35,
            self.save_game,
        )
        self.load_button = Button(
            "UI/button_load.png",
            "UI/button_load_hover.png",
            self.overlay_rect.x + 230,
            self.overlay_rect.y + 20,
            60,
            35,
            self.load_game,
        )

        # 靜音開關（使用提供的圖示）
        self.prev_volume = getattr(sound_manager, "volume", 0.7)
        self.is_muted = (getattr(sound_manager, "volume", 0.7) == 0.0)
        mute_img = "UI/raw/UI_Flat_ButtonCross01a.png" if self.is_muted else "UI/raw/UI_Flat_ButtonCheck01a.png"
        self.mute_button = Button(
            mute_img,
            mute_img,
            self.overlay_rect.x + 300,
            self.overlay_rect.y + 20,
            40,
            35,
            self.toggle_mute,
        )

        # bag button (保留用來切換到 bag 場景)
        self.bag_button_options = Button(
            "UI/button_backpack.png",
            "UI/button_backpack_hover.png",
            GameSettings.SCREEN_WIDTH - 140,
            20,
            50,
            50,
            self.open_bag_overlay,
        )
        # setting button (右上)
        self.setting_button = Button(
            "UI/button_setting.png","UI/button_setting_hover.png",
            GameSettings.SCREEN_WIDTH - 80,
            20,
            50,
            50,
            self.open_overlay,
        )
        self.info={"remaining":0,"text":""}

    def update_slider_pos(self):
        self.volume_slider_rect.centerx = self.volume_rect.x + int(self.volume_rect.width * self.volume)
        self.volume_slider_rect.centery = self.volume_rect.centery
    
    def open_overlay(self):
        self.overlay_visible = True
    
    def close_overlay(self):
        self.overlay_visible = False
        
    @override
    def enter(self) -> None:
        sound_manager.play_bgm("RBY 103 Pallet Town.ogg")
        if self.online_manager:
            self.online_manager.enter()

    @override
    def exit(self) -> None:
        if self.online_manager:
            self.online_manager.exit()


    @override
    def update(self, dt: float):
        # 如果 overlay 開啟 → 暫停遊戲邏輯，只更新 UI 按鈕
        if  self.info["remaining"]>0:

            self.info["remaining"] -= dt
            if self.info["remaining"] > 0:
                return

            self.info["remaining"]=0

        if self.game_manager.call_gscene():
            self.info=self.game_manager.end_call_gscene()


        if self.overlay_visible:
            # 更新 overlay UI（含音量滑桿）
            self.Gsetting_UI.update(dt)

            self.button_close_overlay.update(dt)
            self.save_button.update(dt)
            self.load_button.update(dt)
            self.mute_button.update(dt)
            # 處理滑鼠拖動音量
            mouse_pressed = pg.mouse.get_pressed()[0]
            mouse_pos = pg.mouse.get_pos()
            if mouse_pressed and self.volume_rect.collidepoint(mouse_pos):
                rel_x = mouse_pos[0] - self.volume_rect.x
                vol = max(0.0, min(1.0, rel_x / self.volume_rect.width))
                sound_manager.volume = vol
                GameSettings.AUDIO_VOLUME = vol
                if getattr(sound_manager, "current_bgm", None):
                    try:
                        sound_manager.current_bgm.set_volume(vol)
                    except Exception:
                        pass
                self.volume = vol
                self.update_slider_pos()
            return

        # 保持右上按鈕可互動（僅在 overlay 未開啟時）
        try:
            self.bag_button_options.update(dt)
            self.setting_button.update(dt)
        except Exception:
            pass

        # Check if there is assigned next scene
        self.game_manager.try_switch_map()

        # Update player and other data
        if self.game_manager.player:
            self.game_manager.player.update(dt)
        for enemy in self.game_manager.current_enemy_trainers:
            enemy.update(dt)
        for seller in self.game_manager.current_seller:
            seller.update(dt)

        # Update others
        self.game_manager.bag.update(dt)

        if self.game_manager.player is not None and self.online_manager is not None:
            _ = self.online_manager.update(
                self.game_manager.player.position.x,
                self.game_manager.player.position.y,
                self.game_manager.current_map.path_name
            )

    @override
    def draw(self, screen: pg.Surface):


        m = self.game_manager.current_map

        # 地圖像素寬高（自動支援 tile map 或 pixel map）
        map_pixel_w = m.pixel_w
        map_pixel_h = m.pixel_h

        # -- 計算相機 --
        if self.game_manager.player:
            ppos = self.game_manager.player.position

            # 玩家位置（像素）
            player_px_x = ppos.x
            player_px_y = ppos.y

            # 讓玩家置中
            desired_x = int(player_px_x - GameSettings.SCREEN_WIDTH / 2)
            desired_y = int(player_px_y - GameSettings.SCREEN_HEIGHT / 2)

            # 限制相機邊界
            max_cam_x = max(0, map_pixel_w - GameSettings.SCREEN_WIDTH)
            max_cam_y = max(0, map_pixel_h - GameSettings.SCREEN_HEIGHT)

            cam_x = max(0, min(desired_x, max_cam_x))
            cam_y = max(0, min(desired_y, max_cam_y))

            camera = PositionCamera(cam_x, cam_y)
        else:
            camera = PositionCamera(0, 0)


        # 先畫地圖
        self.game_manager.current_map.draw(screen, camera)

        # 繪製玩家
        if self.game_manager.player:
            self.game_manager.player.draw(screen, camera)

        # 敵人
        for enemy in self.game_manager.current_enemy_trainers:
            enemy.draw(screen, camera)

        for seller in self.game_manager.current_seller:
            seller.draw(screen, camera)

        # 背包 UI
        self.game_manager.bag.draw(screen)

        # 右上角按鈕
        self.bag_button_options.draw(screen)
        self.setting_button.draw(screen)

        # 在線玩家
        if self.online_manager and self.game_manager.player:
            list_online = self.online_manager.get_list_players()
            for player in list_online:
                if player["map"] == self.game_manager.current_map.path_name:
                    cam = self.game_manager.player.camera
                    pos = cam.transform_position_as_position(Position(player["x"], player["y"]))
                    self.sprite_online.update_pos(pos)
                    self.sprite_online.draw(screen)

        # overlay
        if self.overlay_visible:
            dim_surf = pg.Surface(screen.get_size(), pg.SRCALPHA)
            dim_surf.fill((0, 0, 0, 150))
            screen.blit(dim_surf, (0, 0))
            self.Gsetting_UI.draw(screen)

            self.button_close_overlay.draw(screen)
            self.save_button.draw(screen)
            self.load_button.draw(screen)
            self.mute_button.draw(screen)

            pg.draw.rect(screen, (180, 180, 180), self.volume_rect)
            pg.draw.rect(screen, (255, 0, 0), self.volume_slider_rect)

        if self.info["remaining"]>0:
            self.Gsetting_UI.draw(screen)
            txt = self.info.get("text", "Oh...h,hello...")
            font_item = pg.font.Font(None, 35)
            info_txt = font_item.render(txt, True, (0, 0, 0))
            screen.blit(info_txt ,(465, 345))



    def save_game(self):
        try:
            # Save current game manager state to default save file
            self.game_manager.save("saves/game0.json")
            Logger.info("Game saved (overlay)")
        except Exception as e:
            Logger.warning(f"Failed to save game from overlay: {e}")

    def load_game(self):
        try:
            manager = GameManager.load("saves/game0.json")

            if manager is None:
                Logger.error("Failed to load game from saves/game0.json or backup")
                return

            # Replace current game manager with loaded one
            self.game_manager = manager

            # --- 防止讀檔後立即遇敵 ---
            # Prevent immediate wild encounters on load: mark player as already "on bush"
            try:
                if self.game_manager.player is not None:
                    setattr(self.game_manager.player, "_on_bush", True)
            except Exception:
                pass
            # -------------------------------------

            # Close overlay after successful load
            self.overlay_active = False
            Logger.info("Game loaded (overlay)")

        except Exception as e:
            Logger.warning(f"Failed to load game from overlay: {e}")


    def toggle_mute(self):
        """切換靜音狀態，並更新按鈕圖示與 sound_manager 音量"""
        try:
            if self.is_muted:
                new_vol = getattr(self, "prev_volume", GameSettings.AUDIO_VOLUME)
                new_vol = max(0.0, min(1.0, new_vol))
                sound_manager.volume = new_vol
                GameSettings.AUDIO_VOLUME = new_vol
                if getattr(sound_manager, "current_bgm", None):
                    try:
                        sound_manager.current_bgm.set_volume(new_vol)
                    except Exception:
                        pass
                self.is_muted = False
                img = "UI/raw/UI_Flat_ButtonCheck01a.png"
            else:
                self.prev_volume = getattr(sound_manager, "volume", GameSettings.AUDIO_VOLUME)
                sound_manager.volume = 0.0
                GameSettings.AUDIO_VOLUME = 0.0
                if getattr(sound_manager, "current_bgm", None):
                    try:
                        sound_manager.current_bgm.set_volume(0.0)
                    except Exception:
                        pass
                self.is_muted = True
                img = "UI/raw/UI_Flat_ButtonCross01a.png"
            # 重建按鈕並保持與初始化相同位置/尺寸
            self.mute_button = Button(
                img,
                img,
                self.overlay_rect.x + 300,
                self.overlay_rect.y + 20,
                40,
                35,
                self.toggle_mute,
            )
        except Exception as e:
            Logger.warning(f"toggle_mute failed: {e}")

    def open_bag_overlay(self):
        # 切換到 bag scene（BagScene 會在 enter 取用 pending_bag）
        scene_manager.pending_bag = self.game_manager
        scene_manager.change_scene("bag")

    def close_bag_overlay(self):
        # 保留接口（如果有其他代碼呼叫）
        scene_manager.change_scene("game")

    

