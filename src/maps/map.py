import pygame as pg
import pytmx

from src.utils import load_tmx, Position, GameSettings, PositionCamera, Teleport

class Map:
    # Map Properties
    path_name: str
    tmxdata: pytmx.TiledMap
    # Position Argument
    spawn: Position
    teleporters: list[Teleport]
    # Rendering Properties
    _surface: pg.Surface
    _collision_map: list[pg.Rect]

    def __init__(self, path: str, tp: list[Teleport], spawn: Position):
        self.path_name = path
        self.tmxdata = load_tmx(path)
        self.spawn = spawn
        self.teleporters = tp

        pixel_w = self.tmxdata.width * GameSettings.TILE_SIZE
        pixel_h = self.tmxdata.height * GameSettings.TILE_SIZE
        self.pixel_w=pixel_w
        self.pixel_h=pixel_h

        # Prebake the map
        self._surface = pg.Surface((pixel_w, pixel_h), pg.SRCALPHA)
        
        self._render_all_layers(self._surface)

        self.minimap_scale = 0.15  # 小地圖縮放比例（可調）
        self._minimap = pg.transform.smoothscale(
            self._surface,
            (int(pixel_w * self.minimap_scale), int(pixel_h * self.minimap_scale))
        )
        # Prebake the collision map
        self._collision_map = self._create_collision_map()
        

    def update(self, dt: float):
        return

    def draw(self, screen: pg.Surface, camera: PositionCamera):
        # Draw full map by camera
        screen.blit(self._surface, camera.transform_position(Position(0, 0)))
        
        if GameSettings.DRAW_HITBOXES:
            for rect in self._collision_map:
                pg.draw.rect(screen, (255, 0, 0), camera.transform_rect(rect), 1)
        
    def draw_minimap(self, pos: Position, screen: pg.Surface):
        player_rect = pg.Rect(pos.x, pos.y, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)

        scale = self.minimap_scale

        # 玩家縮放後位置
        px = int(player_rect.x * scale)
        py = int(player_rect.y * scale)

        # 小地圖視窗設定
        view = 180
        half = view // 2

        # 小地圖 surface 將要畫的位置
        sx = px - half
        sy = py - half

        mw, mh = self._minimap.get_size()

        # === 1. 建立固定大小的小地圖視窗 ===
        minimap_view = pg.Surface((view, view))
        minimap_view.fill((0, 0, 0))  # 世界外填黑

        # === 2. 計算貼到 minimap_view 的位置 ===
        # 小地圖的實際來源框
        src_rect = pg.Rect(sx, sy, view, view)

        # clamp 來源，但同時要紀錄偏移量
        src_rect_clamped = src_rect.clip(pg.Rect(0, 0, mw, mh))

        # 貼到小地圖視窗時的 offset
        offset_x = src_rect_clamped.x - src_rect.x
        offset_y = src_rect_clamped.y - src_rect.y

        # === 3. 將存在的小地圖貼到視窗（空缺處保持黑色） ===
        minimap_view.blit(self._minimap, (offset_x, offset_y), src_rect_clamped)

        # === 4. 畫玩家點（永遠在中心）===
        pg.draw.circle(minimap_view, (255, 0, 0), (half, half), 4)

        # === 5. 加上黑色外框 ===
        frame = pg.Surface((view + 4, view + 4))
        frame.fill((0, 0, 0))
        frame.blit(minimap_view, (2, 2))

        # === 6. 貼到螢幕左上角 ===
        screen.blit(frame, (10, 10))


    def check_collision(self, rect: pg.Rect) -> bool:
        '''
        [TODO HACKATHON 4]
        Return True if collide if rect param collide with self._collision_map
        Hint: use API colliderect and iterate each rectangle to check
        '''
        for coll_rect in self._collision_map:
            if rect.colliderect(coll_rect):
                return True
        return False
        
    def check_teleport(self, pos: Position) -> Teleport | None:
        '''[TODO HACKATHON 6 ] 
        Teleportation: Player can enter a building by walking into certain tiles defined inside saves/*.json, and the map will be changed
        Hint: Maybe there is an way to switch the map using something from src/core/managers/game_manager.py called switch_... 
        '''
        player_rect = pg.Rect(pos.x, pos.y, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
        for tp in self.teleporters:
            if player_rect.colliderect(tp.rect):
                return tp
        return None

    def _render_all_layers(self, target: pg.Surface) -> None:
        for layer in self.tmxdata.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                self._render_tile_layer(target, layer)
            # elif isinstance(layer, pytmx.TiledImageLayer) and layer.image:
            #     target.blit(layer.image, (layer.x or 0, layer.y or 0))
 
    def _render_tile_layer(self, target: pg.Surface, layer: pytmx.TiledTileLayer) -> None:
        for x, y, gid in layer:
            if gid == 0:
                continue
            image = self.tmxdata.get_tile_image_by_gid(gid)
            if image is None:
                continue

            image = pg.transform.scale(image, (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
            target.blit(image, (x * GameSettings.TILE_SIZE, y * GameSettings.TILE_SIZE))
    
    def _create_collision_map(self) -> list[pg.Rect]:
        rects = []
        for layer in self.tmxdata.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer) and ("collision" in layer.name.lower() or "house" in layer.name.lower()):
                for x, y, gid in layer:
                    if gid != 0:
                        '''
                        [TODO HACKATHON 4]
                        rects.append(pg.Rect(...))
                        Append the collision rectangle to the rects[] array
                        Remember scale the rectangle with the TILE_SIZE from settings
                        '''
                        rect = pg.Rect(
                            x * GameSettings.TILE_SIZE,
                            y * GameSettings.TILE_SIZE,
                            GameSettings.TILE_SIZE,
                            GameSettings.TILE_SIZE
                        )
                        rects.append(rect)
        return rects

    @classmethod
    def from_dict(cls, data: dict) -> "Map":
        tp = [Teleport.from_dict(t) for t in data["teleport"]]
        pos = Position(data["player"]["x"] * GameSettings.TILE_SIZE, data["player"]["y"] * GameSettings.TILE_SIZE)
        return cls(data["path"], tp, pos)

    def to_dict(self):
        return {
            "path": self.path_name,
            "teleport": [t.to_dict() for t in self.teleporters],
            "player": {
                "x": self.spawn.x // GameSettings.TILE_SIZE,
                "y": self.spawn.y // GameSettings.TILE_SIZE,
            }
        }
    
    def is_pokemon_bush_at(self, pos) -> bool:
        ts = GameSettings.TILE_SIZE

        # ----- 0.5 倍縮放後的小框大小 -----
        shrink = 0.5
        half = ts * shrink / 2

        # 以玩家中心為基準
        center_x = pos.x + ts / 2
        center_y = pos.y + ts / 2

        # 小判定框中的五個取樣點（四角 + 中心）
        sample_points = [
            (center_x - half, center_y - half),
            (center_x + half, center_y - half),
            (center_x - half, center_y + half),
            (center_x + half, center_y + half),
            (center_x, center_y),
        ]

        # 對應到地圖 tile
        sample_tiles = set(
            (int(sx) // ts, int(sy) // ts)
            for sx, sy in sample_points
        )

        # ----- 檢查 TMX 草叢 Layer -----
        for layer in self.tmxdata.visible_layers:
            lname = getattr(layer, "name", "")
            if "bush" not in lname.lower():
                continue

            for x, y, gid in layer:
                if gid == 0:
                    continue
                if (x, y) in sample_tiles:
                    return True

        return False
    
class Teleport:
    def __init__(self, x: int, y: int, destination: str):
        self.x = x        # tile X
        self.y = y        # tile Y
        self.destination = destination
        self.rect = pg.Rect(
            x * GameSettings.TILE_SIZE,
            y * GameSettings.TILE_SIZE,
            GameSettings.TILE_SIZE,
            GameSettings.TILE_SIZE
        )

    @classmethod
    def from_dict(cls, data: dict) -> "Teleport":
        return cls(
            data["x"],
            data["y"],
            data["destination"]
        )

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "destination": self.destination
        }