'''
[TODO HACKATHON 5 ]
Try to mimic the menu_scene.py or game_scene.py to create this new scene
'''
import pygame as pg
from src.utils import GameSettings
from src.sprites import BackgroundSprite
from src.scenes.scene import Scene
from src.interface.components import Button
from src.core.services import scene_manager, input_manager, sound_manager
from typing import override

class SettingScene(Scene):
    background: BackgroundSprite
    fullscreen_button: Button
    back_button: Button
    volume_rect: pg.Rect
    volume_slider_rect: pg.Rect
    volume: float

    def __init__(self):
        super().__init__()
        self.background = BackgroundSprite("backgrounds/background2.png")
        px = GameSettings.SCREEN_WIDTH // 2
        py_start = GameSettings.SCREEN_HEIGHT // 3
        gap = 120

        # 全螢幕按鈕
        self.fullscreen_button = Button(
            "UI/button_setting.png", "UI/button_setting_hover.png",
            px, py_start, 100, 100,
            lambda: self.toggle_fullscreen()
        )

        # 返回按鈕
        self.back_button = Button(
            "UI/button_back.png", "UI/button_back_hover.png",
            px, py_start + gap * 2, 100, 100,
            lambda: scene_manager.change_scene("menu")
        )

        # 音量滑桿
        self.volume = sound_manager.volume
        self.volume_rect = pg.Rect(px - 150, py_start + gap, 300, 20)
        self.volume_slider_rect = pg.Rect(0, 0, 20, 30)
        self.update_slider_pos()

    def update_slider_pos(self):
        self.volume_slider_rect.centerx = self.volume_rect.x + int(self.volume_rect.width * self.volume)
        self.volume_slider_rect.centery = self.volume_rect.centery

    @override
    def enter(self) -> None:
        sound_manager.play_bgm("RBY 101 Opening (Part 1).ogg")

    @override
    def exit(self) -> None:
        pass

    @override
    def update(self, dt: float) -> None:
        self.fullscreen_button.update(dt)
        self.back_button.update(dt)

        # 滑鼠拖動音量
        mouse_pressed = pg.mouse.get_pressed()[0]
        mouse_pos = pg.mouse.get_pos()
        if mouse_pressed and self.volume_rect.collidepoint(mouse_pos):
            self.update_slider_pos()
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

        # 快捷鍵返回
        if input_manager.key_pressed(pg.K_ESCAPE):
            scene_manager.change_scene("menu")

    @override
    def draw(self, screen: pg.Surface) -> None:
        self.background.draw(screen)
        self.fullscreen_button.draw(screen)
        self.back_button.draw(screen)

        # 畫音量滑桿
        pg.draw.rect(screen, (180, 180, 180), self.volume_rect)  # 滑軌
        pg.draw.rect(screen, (255, 0, 0), self.volume_slider_rect)  # 滑塊

    def toggle_fullscreen(self):
        GameSettings.SCREEN_FULLSCREEN = not GameSettings.SCREEN_FULLSCREEN
        pg.display.set_mode(
            (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT),
            pg.FULLSCREEN if GameSettings.SCREEN_FULLSCREEN else 0
        )
