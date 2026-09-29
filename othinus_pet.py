#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""欧提努斯桌宠：透明窗口、系统托盘、成长系统与互动小游戏。"""

from __future__ import annotations

import json
import math
import os
import random
import sys
import time
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QDir, QLockFile, QPoint, QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
    QRegion,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "欧提努斯桌宠"
APP_VERSION = "2.6.2"
SPRITE_TRANSITION_SECONDS = 0.52
PET_WINDOW_WIDTH = 460
PET_WINDOW_HEIGHT = 520
PET_SPRITE_SIZE = 286
PET_GROUND_Y = 486
EDGE_TRIGGER_DISTANCE = 6
SPEAR_DEFAULT_OFFSET = (88.0, -182.0)
SPEAR_DEFAULT_ANGLE = 8.0
SPEAR_DEFAULT_SCALE = 1.25
SPEAR_SCALE_RANGE = (0.65, 1.45)
SPEAR_BASE_SIZE = (62.0, 248.0)
ACTION_EDGE_INSETS = {
    "jump": 72,
    "angry": 8,
    "battle": 10,
    "victory": 8,
    "tired": 5,
    "surprise": 4,
    "walk": 5,
    "destroy": 12,
}
DEFAULT_SCREEN_MARGIN = (10, 10, 10, 10)
ACTION_MOTION_MARGINS = {
    # left, top, right, bottom；预留动画位移与旋转空间，防止角色被真实屏幕边缘裁掉。
    "jump": (14, 76, 14, 10),
    "angry": (16, 12, 16, 10),
    "battle": (14, 14, 14, 12),
    "destroy": (14, 16, 14, 12),
    "victory": (12, 14, 12, 10),
    "surprise": (12, 16, 12, 10),
    "walk": (12, 12, 12, 10),
}
ACTION_MIN_DURATIONS = {
    "idle": 0.0,
    "wave": 4.2,
    "jump": 4.0,
    "pat": 4.6,
    "angry": 4.2,
    "magic": 5.2,
    "surprise": 4.0,
    "eat": 5.4,
    "sleep": 12.0,
    "cry": 5.0,
    "laugh": 4.5,
    "confused": 4.6,
    "shy": 4.6,
    "yawn": 5.0,
    "bored": 5.2,
    "gift": 4.8,
    "spear_idle": 5.5,
    "battle": 6.4,
    "victory": 4.5,
    "tired": 4.8,
    "drag": 0.0,
    "walk": 0.0,
    "edge": 5.2,
    "destroy": 9.0,
}
ACTION_VARIANTS = {
    "idle": ("idle_neutral", "idle_smile", "idle_smug"),
    "wave": ("wave_cheer", "idle_smile"),
    "jump": ("jump_excited", "laugh_happy"),
    "pat": ("pat_bliss", "shy_blush", "idle_smile"),
    "angry": ("angry_pout", "bored_sit"),
    "magic": ("magic_focus", "magic_smug"),
    "surprise": ("surprise_shock", "confused"),
    "eat": ("eat_happy", "eat_smug", "tea_calm"),
    "sleep": ("sleep_touma_a", "sleep_touma_b"),
    "cry": ("cry_sad",),
    "laugh": ("laugh_happy",),
    "confused": ("confused", "surprise_shock"),
    "shy": ("shy_blush", "pat_bliss"),
    "yawn": ("yawn_sleepy",),
    "bored": ("bored_sit", "idle_neutral"),
    "gift": ("gift_heart", "idle_smile"),
    "spear_idle": ("spear_float",),
    "battle": ("spear_ready", "spear_thrust", "spear_spin", "spear_guard"),
    "victory": ("spear_victory",),
    "tired": ("spear_tired",),
    "drag": ("drag_dangle",),
    "walk": ("walk_step",),
    # 侧边不只重复一个姿势：探头、招手和观察都会按各自可见轮廓重新贴边。
    "edge": ("edge_peek", "wave_cheer", "confused"),
    "destroy": ("spear_victory", "spear_ready"),
}
SPRITES = tuple(sorted({name for variants in ACTION_VARIANTS.values() for name in variants}))
SMOKE_MODE = "--smoke-test" in sys.argv


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def data_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    return base / "OthinusDesktopPet" / "save.json"


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


class SaveData:
    BOND_STAGES = (
        (0, "初次相遇"),
        (12, "掌心旅伴"),
        (35, "理解萌芽"),
        (80, "可靠的理解者"),
        (150, "世界的见证者"),
        (260, "唯一的理解者"),
    )
    MASTERY_NAMES = {
        "rune": "符文追迹",
        "gungnir": "主神之枪",
        "phase": "相位记忆",
    }

    DEFAULT = {
        "name": "欧提努斯",
        "level": 1,
        "xp": 0,
        "affection": 0,
        "fullness": 78.0,
        "energy": 82.0,
        "mood": 76.0,
        "coins": 8,
        "scale": 1.0,
        "sound": True,
        "auto_wander": True,
        "spear_float": False,
        "spear_offset": [SPEAR_DEFAULT_OFFSET[0], SPEAR_DEFAULT_OFFSET[1]],
        "spear_angle": SPEAR_DEFAULT_ANGLE,
        "spear_scale": SPEAR_DEFAULT_SCALE,
        "rest_minutes": 5,
        "daily_streak": 0,
        "best_daily_streak": 0,
        "phase_fragments": 0,
        "mastery": {"rune": 0, "gungnir": 0, "phase": 0},
        "game_records": {
            "rune_best": 0, "gungnir_best": 0, "phase_best": 0,
            "total": 0, "perfects": 0, "best_combo": 0,
        },
        "unlocks": [],
        "last_seen": "",
        "last_daily": "",
        "position": None,
        "counters": {
            "pat": 0, "feed": 0, "play": 0, "magic": 0,
            "battle": 0, "game": 0, "game_rune": 0, "game_gungnir": 0,
            "game_phase": 0, "destroy": 0, "oracle": 0,
        },
        "achievements": [],
    }

    def __init__(self) -> None:
        self.values = json.loads(json.dumps(self.DEFAULT, ensure_ascii=False))
        if not SMOKE_MODE:
            self.load()

    def load(self) -> None:
        try:
            saved = json.loads(data_path().read_text(encoding="utf-8"))
            for key in self.values:
                if key in saved:
                    if isinstance(self.values[key], dict) and isinstance(saved[key], dict):
                        self.values[key].update(saved[key])
                    else:
                        self.values[key] = saved[key]
        except (OSError, ValueError, TypeError):
            pass
        self.apply_offline_progress()

    def apply_offline_progress(self) -> None:
        raw = self.values.get("last_seen")
        if raw:
            try:
                seconds = max(0.0, min(72 * 3600, (datetime.now() - datetime.fromisoformat(raw)).total_seconds()))
                hours = seconds / 3600
                self.values["fullness"] = clamp(float(self.values["fullness"]) - hours * 2.8)
                self.values["energy"] = clamp(float(self.values["energy"]) + hours * 11)
                self.values["mood"] = clamp(float(self.values["mood"]) - hours * 1.1)
            except (ValueError, TypeError):
                pass

    def save(self) -> None:
        if SMOKE_MODE:
            return
        try:
            path = data_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            self.values["last_seen"] = datetime.now().isoformat(timespec="seconds")
            path.write_text(json.dumps(self.values, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        self.values[key] = value

    @staticmethod
    def xp_needed(level: int) -> int:
        return 45 + level * 35

    @property
    def title(self) -> str:
        level = int(self["level"])
        titles = [
            (1, "掌心魔神"), (3, "熟悉的理解者"), (5, "符文旅伴"),
            (8, "独眼的盟友"), (12, "世界的观察者"), (18, "完全魔神"),
        ]
        result = titles[0][1]
        for requirement, title in titles:
            if level >= requirement:
                result = title
        return result

    @property
    def bond_rank(self) -> int:
        affection = int(self["affection"])
        rank = 0
        for index, (requirement, _name) in enumerate(self.BOND_STAGES):
            if affection >= requirement:
                rank = index
        return rank

    @property
    def bond_title(self) -> str:
        return self.BOND_STAGES[self.bond_rank][1]

    @property
    def bond_progress(self) -> int:
        rank = self.bond_rank
        if rank >= len(self.BOND_STAGES) - 1:
            return 100
        low = self.BOND_STAGES[rank][0]
        high = self.BOND_STAGES[rank + 1][0]
        return round((int(self["affection"]) - low) / max(1, high - low) * 100)

    def mastery_level(self, key: str) -> int:
        return min(10, 1 + int(self["mastery"].get(key, 0)) // 45)

    def mastery_label(self, key: str) -> str:
        level = self.mastery_level(key)
        ranks = ("入门", "熟悉", "娴熟", "精通", "共鸣")
        rank = ranks[min(len(ranks) - 1, (level - 1) // 2)]
        return f"{self.MASTERY_NAMES[key]} Lv.{level}·{rank}"


class PetWindow(QWidget):
    clicked = Signal()
    double_clicked = Signal()
    drag_started = Signal()
    context_requested = Signal(QPoint)
    scale_changed = Signal(float)
    moved_by_user = Signal(QPoint)
    sprite_changed = Signal(str)
    inline_game_finished = Signal(str, int, int)
    spear_transform_committed = Signal()

    def __init__(self, state: SaveData) -> None:
        super().__init__()
        self.state = state
        # 给跳跃、帽尖、披风和脚部留下透明安全边距；角色本身仍保持原显示尺寸。
        self.setFixedSize(PET_WINDOW_WIDTH, PET_WINDOW_HEIGHT)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(str(resource_path("assets/othinus_icon_v4_fullbody.ico"))))
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)

        self.pixmaps = {
            name: QPixmap(str(resource_path(f"assets/sprites_v2/{name}.png"))) for name in SPRITES
        }
        # 由每张 PNG 的真实 alpha 轮廓得到边界，避免用透明窗口外框判断贴屏位置。
        self.sprite_alpha_bounds = {
            name: QRegion(pixmap.mask()).boundingRect() for name, pixmap in self.pixmaps.items()
        }
        self.gungnir_pixmap = QPixmap(str(resource_path("assets/sprites_v2/gungnir_float.png")))
        self.action = "idle"
        self.sprite_name = random.choice(ACTION_VARIANTS["idle"])
        self.previous_sprite_name: str | None = None
        self.transition_started = time.monotonic()
        self.action_started = time.monotonic()
        self.action_duration = 0.0
        self.bubble = ""
        self.bubble_until = 0.0
        self.phase = 0.0
        self.particles: list[dict[str, object]] = []
        self.drag_origin: QPoint | None = None
        self.window_origin: QPoint | None = None
        self.drag_distance = 0
        self.drag_visual_active = False
        self.mirror_sprite = False
        self.spear_adjust_mode = False
        self.spear_drag_active = False
        self.spear_drag_origin = QPointF()
        self.spear_offset_origin = SPEAR_DEFAULT_OFFSET
        self.game_mode: str | None = None
        self.game_started_at = 0.0
        self.game_deadline = 0.0
        self.game_last_tick = 0.0
        self.game_score = 0
        self.game_combo = 0
        self.game_aux = 0
        self.game_mastery = 1
        self.game_hit_radius = 28
        self.game_target = QPointF(self.width() / 2, self.height() / 2)
        self.game_velocity = QPointF(0, 0)
        self.game_decoys: list[QPointF] = []
        self.game_zone_center = 0.5
        self.game_zone_half = 0.12
        self.game_round = 0
        self.game_round_started = 0.0
        self.game_results: list[int] = []
        self.game_sequence: list[int] = []
        self.game_input_index = 0
        self.game_state = ""
        self.game_show_started = 0.0
        self.game_flash_index = -1
        self.game_flash_until = 0.0
        self.game_show_interval = 0.68

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.animate)
        self.anim_timer.start(33)

    def change_sprite(self, sprite_name: str) -> None:
        if sprite_name == self.sprite_name:
            return
        self.previous_sprite_name = self.sprite_name
        self.sprite_name = sprite_name
        self.transition_started = time.monotonic()
        self.sprite_changed.emit(sprite_name)

    def sprite_draw_rect(self) -> QRect:
        """所有动作共用同一个绘制尺寸；动作切换只改变姿势，不再改变模型大小。"""
        sprite_size = round(PET_SPRITE_SIZE * float(self.state["scale"]))
        sprite_size = max(205, min(330, sprite_size))
        return QRect(
            round((self.width() - sprite_size) / 2),
            PET_GROUND_Y - sprite_size,
            sprite_size,
            sprite_size,
        )

    def sprite_content_rect(self, sprite_name: str | None = None, mirrored: bool | None = None) -> QRect:
        """返回贴图在窗口内的真实可见矩形，包含当前缩放和镜像。"""
        name = sprite_name or self.sprite_name
        source = self.pixmaps[name]
        alpha = self.sprite_alpha_bounds[name]
        target = self.sprite_draw_rect()
        use_mirror = self.mirror_sprite if mirrored is None else mirrored
        if use_mirror:
            source_left = source.width() - alpha.x() - alpha.width()
        else:
            source_left = alpha.x()
        left = target.x() + round(source_left * target.width() / source.width())
        top = target.y() + round(alpha.y() * target.height() / source.height())
        width = max(1, round(alpha.width() * target.width() / source.width()))
        height = max(1, round(alpha.height() * target.height() / source.height()))
        return QRect(left, top, width, height)

    def global_sprite_content_rect(self, sprite_name: str | None = None, mirrored: bool | None = None) -> QRect:
        local = self.sprite_content_rect(sprite_name, mirrored)
        return local.translated(self.pos())

    def spear_offset(self) -> tuple[float, float]:
        value = self.state["spear_offset"]
        try:
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return float(value[0]), float(value[1])
        except (TypeError, ValueError):
            pass
        return SPEAR_DEFAULT_OFFSET

    def spear_angle(self) -> float:
        try:
            return max(-180.0, min(180.0, float(self.state["spear_angle"])))
        except (TypeError, ValueError):
            return SPEAR_DEFAULT_ANGLE

    def spear_scale(self) -> float:
        try:
            return clamp(float(self.state["spear_scale"]), *SPEAR_SCALE_RANGE)
        except (TypeError, ValueError):
            return SPEAR_DEFAULT_SCALE

    def spear_draw_rect(self, floating: bool = True) -> QRectF:
        """以人物脚下锚点为原点，用逻辑坐标计算神枪矩形；缩放时相对关系保持不变。"""
        scale = float(self.state["scale"])
        spear_scale = self.spear_scale()
        offset_x, offset_y = self.spear_offset()
        width = SPEAR_BASE_SIZE[0] * scale * spear_scale
        height = SPEAR_BASE_SIZE[1] * scale * spear_scale
        bob = math.sin(self.phase * 1.7) * 2.0 * scale if floating and not self.spear_adjust_mode else 0.0
        center = QPointF(
            self.width() / 2 + offset_x * scale,
            PET_GROUND_Y + offset_y * scale + bob,
        )
        return QRectF(center.x() - width / 2, center.y() - height / 2, width, height)

    def spear_polygon(self, floating: bool = False) -> QPolygonF:
        rect = self.spear_draw_rect(floating)
        center = rect.center()
        transform = QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(self.spear_angle())
        transform.translate(-center.x(), -center.y())
        return transform.map(QPolygonF([rect.topLeft(), rect.topRight(), rect.bottomRight(), rect.bottomLeft()]))

    def spear_hit_test(self, point: QPointF) -> bool:
        return self.spear_polygon(False).containsPoint(point, Qt.FillRule.WindingFill)

    def clamp_spear_offset(self, offset_x: float, offset_y: float, angle: float | None = None) -> tuple[float, float]:
        """限制神枪在透明画布内，允许任意角度但不允许再次被画布裁切。"""
        scale = float(self.state["scale"])
        spear_scale = self.spear_scale()
        radians = math.radians(self.spear_angle() if angle is None else angle)
        half_width = SPEAR_BASE_SIZE[0] * scale * spear_scale / 2
        half_height = SPEAR_BASE_SIZE[1] * scale * spear_scale / 2
        extent_x = abs(math.cos(radians)) * half_width + abs(math.sin(radians)) * half_height
        extent_y = abs(math.sin(radians)) * half_width + abs(math.cos(radians)) * half_height
        center_x = self.width() / 2 + offset_x * scale
        center_y = PET_GROUND_Y + offset_y * scale
        center_x = max(extent_x + 8, min(self.width() - extent_x - 8, center_x))
        center_y = max(extent_y + 8, min(self.height() - extent_y - 8, center_y))
        return (center_x - self.width() / 2) / scale, (center_y - PET_GROUND_Y) / scale

    def set_spear_transform(
        self,
        offset_x: float,
        offset_y: float,
        angle: float | None = None,
        spear_scale: float | None = None,
    ) -> None:
        if angle is not None:
            normalized = ((float(angle) + 180.0) % 360.0) - 180.0
            self.state["spear_angle"] = round(normalized, 1)
        if spear_scale is not None:
            self.state["spear_scale"] = round(clamp(float(spear_scale), *SPEAR_SCALE_RANGE), 2)
        offset_x, offset_y = self.clamp_spear_offset(offset_x, offset_y)
        self.state["spear_offset"] = [round(offset_x, 1), round(offset_y, 1)]
        self.update()

    def set_action(self, action: str, duration: float = 2.0, text: str = "") -> None:
        if action not in ACTION_VARIANTS:
            action = "idle"
        if action not in ("walk", "edge"):
            self.mirror_sprite = False
        variants = ACTION_VARIANTS[action]
        choices = [name for name in variants if name != self.sprite_name] or list(variants)
        self.change_sprite(random.choice(choices))
        self.action = action
        self.action_started = time.monotonic()
        self.action_duration = max(duration, ACTION_MIN_DURATIONS[action])
        self.phase = 0.0
        if text:
            self.say(text, max(2.2, min(4.5, len(text) * 0.16)))
        if action in ("magic", "spear_idle", "battle", "victory", "destroy"):
            self.spawn_particles("magic", 38 if action == "destroy" else 25)
        elif action in ("jump", "surprise"):
            self.spawn_particles("star", 14)
        elif action == "eat":
            self.spawn_particles("heart", 10)
        self.update()

    def say(self, text: str, seconds: float = 3.0) -> None:
        self.bubble = text
        self.bubble_until = time.monotonic() + seconds
        self.update()

    def spawn_particles(self, kind: str, count: int) -> None:
        colors = {
            "magic": [(255, 224, 92), (255, 181, 45), (255, 247, 174)],
            "star": [(255, 221, 65), (255, 153, 68), (255, 255, 180)],
            "heart": [(255, 90, 150), (255, 160, 190), (255, 210, 80)],
        }
        for _ in range(count):
            angle = random.uniform(math.pi, math.tau)
            speed = random.uniform(25, 95)
            self.particles.append({
                "x": random.uniform(self.width() / 2 - 60, self.width() / 2 + 60),
                "y": random.uniform(PET_GROUND_Y - 190, PET_GROUND_Y - 55),
                "vx": math.cos(angle) * speed, "vy": math.sin(angle) * speed,
                "life": random.uniform(0.65, 1.35), "kind": kind,
                "color": random.choice(colors[kind]), "size": random.uniform(3, 7),
            })

    def animate(self) -> None:
        self.phase += 0.033
        now = time.monotonic()
        if self.game_mode:
            self.update_inline_game(now)
        if self.action != "idle" and self.action_duration and now - self.action_started >= self.action_duration:
            expired_action = self.action
            self.action = "idle"
            if expired_action == "edge":
                self.mirror_sprite = False
            choices = [name for name in ACTION_VARIANTS["idle"] if name != self.sprite_name]
            self.change_sprite(random.choice(choices or ACTION_VARIANTS["idle"]))
            self.action_duration = 0.0
            self.action_started = now
        if self.previous_sprite_name and now - self.transition_started >= SPRITE_TRANSITION_SECONDS:
            self.previous_sprite_name = None
        for p in self.particles:
            p["x"] = float(p["x"]) + float(p["vx"]) * 0.033
            p["y"] = float(p["y"]) + float(p["vy"]) * 0.033
            p["vy"] = float(p["vy"]) + 25 * 0.033
            p["life"] = float(p["life"]) - 0.033
        self.particles = [p for p in self.particles if float(p["life"]) > 0]
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        now = time.monotonic()
        elapsed = now - self.action_started
        progress = min(1.0, elapsed / max(0.01, self.action_duration)) if self.action_duration else 0.0
        # 静止待机不做整模位移；鲜活感由表情和真实动作承担，避免无意义上下抖动。
        dx = 0.0
        dy = 0.0
        rotation = 0.0
        if self.action == "jump":
            dy -= abs(math.sin(progress * math.pi)) * 62
            rotation = math.sin(progress * math.tau) * 2.2
        elif self.action == "angry":
            dx = math.sin(self.phase * 22) * 2.2
            rotation = math.sin(self.phase * 16) * 0.7
        elif self.action == "magic":
            rotation = math.sin(self.phase * 2.1) * 0.25
        elif self.action == "spear_idle":
            dy += math.sin(self.phase * 1.8) * 1.0
        elif self.action == "battle":
            dx = math.sin(self.phase * 8) * 0.8
            rotation = math.sin(self.phase * 6) * 0.45
        elif self.action == "destroy":
            dy = -abs(math.sin(self.phase * 1.2)) * 2.0
            rotation = math.sin(self.phase * 1.5) * 0.32
        elif self.action == "victory":
            dy -= abs(math.sin(self.phase * 1.8)) * 1.5
        elif self.action == "tired":
            dy = math.sin(self.phase * 1.2) * 0.6
            rotation = -0.35
        elif self.action == "surprise":
            entrance = min(1.0, elapsed / 0.7)
            dy -= math.sin(entrance * math.pi) * 1.2
        elif self.action == "sleep":
            dy = math.sin(self.phase * 1.1) * 0.6
            rotation = -0.35
        elif self.action == "cry":
            dx = math.sin(self.phase * 7) * 0.7
        elif self.action == "walk":
            # 只有移动时才出现轻微踏步起伏。
            dy = -abs(math.sin(self.phase * 5.2)) * 1.4
            rotation = math.sin(self.phase * 2.6) * 0.3

        # 柔和落地阴影。
        if self.action == "drag":
            shadow_alpha = 0
        elif self.action == "jump":
            shadow_alpha = max(15, round(42 * (1 - abs(math.sin(progress * math.pi)))))
        else:
            shadow_alpha = 42
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, shadow_alpha))
        shadow_left = round((self.width() - 146) / 2)
        painter.drawEllipse(QRect(shadow_left, PET_GROUND_Y - 14, 146, 22))

        # 浮动神枪始终先绘制，因此与人物重叠时位于人物贴图之下。
        if (bool(self.state["spear_float"]) or self.spear_adjust_mode) and self.action not in ("spear_idle", "battle", "victory", "tired", "destroy"):
            spear_rect = self.spear_draw_rect(floating=True)
            spear_center = spear_rect.center()
            painter.save()
            painter.setOpacity(0.94)
            painter.translate(spear_center)
            painter.rotate(self.spear_angle())
            painter.translate(-spear_center)
            painter.drawPixmap(spear_rect.toRect(), self.gungnir_pixmap)
            painter.restore()

        absolute_target = self.sprite_draw_rect()
        target = QRect(
            -absolute_target.width() // 2,
            -absolute_target.height(),
            absolute_target.width(),
            absolute_target.height(),
        )
        transition = min(1.0, max(0.0, (now - self.transition_started) / SPRITE_TRANSITION_SECONDS))
        transition = transition * transition * (3.0 - 2.0 * transition)
        painter.save()
        painter.translate(round(self.width() / 2 + dx), round(PET_GROUND_Y + dy))
        if self.mirror_sprite:
            painter.scale(-1, 1)
        painter.rotate(rotation)
        if self.previous_sprite_name and transition < 1.0:
            painter.setOpacity(1.0 - transition)
            painter.drawPixmap(target, self.pixmaps[self.previous_sprite_name])
        painter.setOpacity(transition if self.previous_sprite_name else 1.0)
        painter.drawPixmap(target, self.pixmaps[self.sprite_name])
        painter.restore()

        if self.spear_adjust_mode:
            self.draw_spear_adjust_overlay(painter)

        self.draw_particles(painter)
        if self.game_mode:
            self.draw_inline_game(painter, now)
        elif self.bubble and now < self.bubble_until:
            self.draw_bubble(painter, self.bubble)

    def draw_particles(self, painter: QPainter) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.particles:
            life = max(0.0, min(1.0, float(p["life"])))
            r, g, b = p["color"]
            color = QColor(r, g, b, round(230 * life))
            painter.setBrush(color)
            x, y = round(float(p["x"])), round(float(p["y"]))
            size = max(2, round(float(p["size"]) * life))
            if p["kind"] == "heart":
                painter.drawEllipse(QRect(x - size, y - size, size * 2, size * 2))
                painter.drawEllipse(QRect(x, y - size, size * 2, size * 2))
                points = [QPoint(x - size, y), QPoint(x + size * 2, y), QPoint(x + size // 2, y + size * 3)]
                painter.drawPolygon(points)
            else:
                painter.drawEllipse(QRect(x - size, y - size, size * 2, size * 2))

    def draw_bubble(self, painter: QPainter, text: str) -> None:
        font = QFont("Microsoft YaHei UI", 10)
        font.setBold(True)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        lines = []
        current = ""
        for char in text:
            if metrics.horizontalAdvance(current + char) > 295 and current:
                lines.append(current)
                current = char
            else:
                current += char
        if current:
            lines.append(current)
        lines = lines[:3]
        width = min(332, max(112, max(metrics.horizontalAdvance(line) for line in lines) + 30))
        height = 29 + (len(lines) - 1) * 18
        x = (self.width() - width) // 2
        y = 8
        painter.setPen(QPen(QColor(218, 183, 72, 240), 2))
        painter.setBrush(QColor(12, 25, 28, 235))
        painter.drawRoundedRect(QRect(x, y, width, height), 13, 13)
        painter.setPen(QColor(241, 255, 238))
        for index, line in enumerate(lines):
            painter.drawText(QRect(x + 12, y + 5 + index * 18, width - 24, 18), Qt.AlignmentFlag.AlignCenter, line)

    def draw_spear_adjust_overlay(self, painter: QPainter) -> None:
        painter.save()
        polygon = self.spear_polygon(False)
        pen = QPen(QColor(255, 226, 116, 235), 2)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(polygon)
        center = self.spear_draw_rect(False).center()
        painter.setPen(QPen(QColor(104, 219, 178, 190), 1.3))
        painter.drawLine(QPointF(self.width() / 2, PET_GROUND_Y - 125), center)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 236, 152, 245))
        painter.drawEllipse(center, 6, 6)

        offset_x, offset_y = self.spear_offset()
        panel = QRectF(30, 12, self.width() - 60, 62)
        painter.setPen(QPen(QColor(223, 187, 73, 230), 1.5))
        painter.setBrush(QColor(7, 19, 23, 232))
        painter.drawRoundedRect(panel, 13, 13)
        font = QFont("Microsoft YaHei UI", 10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(255, 239, 174))
        painter.drawText(QRect(40, 18, self.width() - 80, 22), Qt.AlignmentFlag.AlignCenter, "主神之枪调整模式 · 直接拖动神枪")
        painter.setPen(QColor(193, 232, 216))
        painter.drawText(
            QRect(40, 42, self.width() - 80, 22), Qt.AlignmentFlag.AlignCenter,
            f"X {offset_x:+.0f}  Y {offset_y:+.0f}　角度 {self.spear_angle():+.1f}°　尺寸 {self.spear_scale() * 100:.0f}%",
        )
        painter.restore()

    def start_inline_game(self, mode: str, mastery: int = 1) -> bool:
        """在桌宠透明窗口内部开始游戏，不创建额外窗口。"""
        if self.game_mode or mode not in ("rune", "gungnir", "phase"):
            return False
        now = time.monotonic()
        self.game_mode = mode
        self.game_started_at = now
        self.game_last_tick = now
        self.game_score = 0
        self.game_combo = 0
        self.game_aux = 0
        self.game_mastery = max(1, int(mastery))
        self.game_round = 0
        self.game_results = []
        self.game_sequence = []
        self.game_input_index = 0
        self.game_flash_index = -1
        self.bubble_until = 0.0

        if mode == "rune":
            self.game_deadline = now + 18.0
            self.game_hit_radius = min(36, 27 + self.game_mastery)
            self.place_rune_target()
            self.set_action("magic", 19.0)
        elif mode == "gungnir":
            self.game_deadline = now + 24.0
            self.game_round_started = now
            self.game_zone_center = random.uniform(0.26, 0.74)
            self.game_zone_half = min(0.18, 0.105 + self.game_mastery * 0.006)
            self.set_action("battle", 25.0)
        else:
            length = min(7, 3 + (self.game_mastery - 1) // 2)
            self.game_sequence = [random.randrange(4) for _ in range(length)]
            self.game_show_interval = min(0.82, 0.58 + self.game_mastery * 0.025)
            self.game_state = "show"
            self.game_show_started = now + 0.75
            self.game_deadline = now + 18.0 + length * 1.5
            self.set_action("magic", self.game_deadline - now + 1.0)
        self.update()
        return True

    def cancel_inline_game(self) -> None:
        if not self.game_mode:
            return
        self.game_mode = None
        self.game_sequence = []
        self.game_decoys = []
        self.set_action("idle", 0.0, "演练暂时中止。")

    def place_rune_target(self) -> None:
        radius = 25 + min(4, self.game_mastery // 2)
        self.game_target = QPointF(
            random.uniform(radius + 24, self.width() - radius - 24),
            random.uniform(105, PET_GROUND_Y - radius - 20),
        )
        angle = random.uniform(0, math.tau)
        speed = random.uniform(54, 76)
        self.game_velocity = QPointF(math.cos(angle) * speed, math.sin(angle) * speed)
        self.game_decoys = []
        for _ in range(2):
            for _attempt in range(12):
                point = QPointF(random.uniform(48, self.width() - 48), random.uniform(115, PET_GROUND_Y - 42))
                if math.hypot(point.x() - self.game_target.x(), point.y() - self.game_target.y()) > 92:
                    self.game_decoys.append(point)
                    break

    def game_marker_position(self, now: float) -> float:
        speed = 2.65 + self.game_round * 0.18
        return 0.5 + 0.48 * math.sin((now - self.game_round_started) * speed - math.pi / 2)

    def phase_centers(self) -> tuple[QPointF, ...]:
        return (
            QPointF(67, 145), QPointF(self.width() - 67, 145),
            QPointF(67, 385), QPointF(self.width() - 67, 385),
        )

    def update_inline_game(self, now: float) -> None:
        mode = self.game_mode
        if not mode:
            return
        if now >= self.game_deadline:
            self.finish_inline_game()
            return
        if mode == "rune":
            dt = min(0.06, max(0.0, now - self.game_last_tick))
            radius = 30
            x = self.game_target.x() + self.game_velocity.x() * dt
            y = self.game_target.y() + self.game_velocity.y() * dt
            if x < radius or x > self.width() - radius:
                self.game_velocity.setX(-self.game_velocity.x())
                x = max(radius, min(self.width() - radius, x))
            if y < 102 or y > PET_GROUND_Y - radius:
                self.game_velocity.setY(-self.game_velocity.y())
                y = max(102, min(PET_GROUND_Y - radius, y))
            self.game_target = QPointF(x, y)
        elif mode == "phase" and self.game_state == "show":
            elapsed = now - self.game_show_started
            if elapsed < 0:
                self.game_flash_index = -1
            else:
                slot = int(elapsed / self.game_show_interval)
                within = elapsed % self.game_show_interval
                if slot < len(self.game_sequence):
                    self.game_flash_index = self.game_sequence[slot] if within < self.game_show_interval * 0.62 else -1
                else:
                    self.game_state = "input"
                    self.game_flash_index = -1
        if now >= self.game_flash_until and self.game_state == "input":
            self.game_flash_index = -1
        self.game_last_tick = now

    def handle_inline_game_click(self, point: QPointF) -> None:
        mode = self.game_mode
        if not mode:
            return
        now = time.monotonic()
        if mode == "rune":
            distance = math.hypot(point.x() - self.game_target.x(), point.y() - self.game_target.y())
            if distance <= self.game_hit_radius:
                self.game_combo += 1
                self.game_aux = max(self.game_aux, self.game_combo)
                self.game_score += 1 + min(2, self.game_combo // 5)
                self.spawn_particles("star", 5)
                self.place_rune_target()
            elif any(math.hypot(point.x() - p.x(), point.y() - p.y()) <= 26 for p in self.game_decoys):
                self.game_score = max(0, self.game_score - 2)
                self.game_combo = 0
            else:
                self.game_combo = 0
        elif mode == "gungnir":
            marker = self.game_marker_position(now)
            distance = abs(marker - self.game_zone_center)
            if distance <= 0.026:
                points = 3
                self.game_aux += 1
                self.spawn_particles("star", 12)
            elif distance <= self.game_zone_half:
                points = 2
                self.spawn_particles("magic", 7)
            elif distance <= self.game_zone_half * 1.75:
                points = 1
            else:
                points = 0
            self.game_score += points
            self.game_results.append(points)
            self.game_round += 1
            if self.game_round >= 6:
                self.finish_inline_game()
                return
            self.game_zone_center = random.uniform(0.22, 0.78)
            self.game_round_started = now
            choices = [name for name in ACTION_VARIANTS["battle"] if name != self.sprite_name]
            self.change_sprite(random.choice(choices or ACTION_VARIANTS["battle"]))
        elif mode == "phase" and self.game_state == "input":
            clicked = -1
            for index, center in enumerate(self.phase_centers()):
                if math.hypot(point.x() - center.x(), point.y() - center.y()) <= 34:
                    clicked = index
                    break
            if clicked < 0:
                return
            self.game_flash_index = clicked
            self.game_flash_until = now + 0.22
            expected = self.game_sequence[self.game_input_index]
            if clicked != expected:
                self.finish_inline_game()
                return
            self.game_input_index += 1
            self.game_score += 1
            self.spawn_particles("magic", 5)
            if self.game_input_index >= len(self.game_sequence):
                self.game_aux = 1
                self.finish_inline_game()
                return
        self.update()

    def finish_inline_game(self) -> None:
        if not self.game_mode:
            return
        mode = self.game_mode
        score = self.game_score
        auxiliary = self.game_aux
        self.game_mode = None
        self.game_sequence = []
        self.game_decoys = []
        self.inline_game_finished.emit(mode, score, auxiliary)
        self.update()

    def draw_inline_game(self, painter: QPainter, now: float) -> None:
        mode = self.game_mode
        if not mode:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        header = QRectF(34, 14, self.width() - 68, 70)
        painter.setPen(QPen(QColor(224, 190, 82, 230), 1.5))
        painter.setBrush(QColor(6, 19, 24, 226))
        painter.drawRoundedRect(header, 14, 14)
        title_font = QFont("Microsoft YaHei UI", 11)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor(255, 232, 141))

        if mode == "rune":
            remaining = max(0, math.ceil(self.game_deadline - now))
            painter.drawText(QRect(45, 20, self.width() - 90, 25), Qt.AlignmentFlag.AlignCenter, "北欧符文追迹")
            painter.setPen(QColor(220, 244, 235))
            painter.drawText(QRect(45, 47, self.width() - 90, 24), Qt.AlignmentFlag.AlignCenter,
                             f"捕获金色符文 · {remaining}s   得分 {self.game_score}   连击 {self.game_combo}")
            for decoy in self.game_decoys:
                painter.setPen(QPen(QColor(255, 92, 98, 220), 2))
                painter.setBrush(QColor(89, 11, 29, 190))
                painter.drawEllipse(decoy, 22, 22)
                painter.drawLine(decoy + QPointF(-8, -8), decoy + QPointF(8, 8))
                painter.drawLine(decoy + QPointF(8, -8), decoy + QPointF(-8, 8))
            target = self.game_target
            pulse = 1.0 + math.sin(self.phase * 5.5) * 0.08
            radius = self.game_hit_radius * pulse
            glow = QRadialGradient(target, radius * 1.8)
            glow.setColorAt(0.0, QColor(255, 251, 170, 250))
            glow.setColorAt(0.45, QColor(255, 193, 44, 225))
            glow.setColorAt(1.0, QColor(255, 166, 20, 0))
            painter.setPen(QPen(QColor(255, 244, 166), 2.2))
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(target, radius, radius)
            painter.drawPolygon(QPolygonF([
                target + QPointF(0, -13), target + QPointF(11, 0),
                target + QPointF(0, 13), target + QPointF(-11, 0),
            ]))
        elif mode == "gungnir":
            painter.drawText(QRect(45, 20, self.width() - 90, 25), Qt.AlignmentFlag.AlignCenter, "主神之枪 · 共鸣校准")
            painter.setPen(QColor(220, 244, 235))
            painter.drawText(QRect(45, 47, self.width() - 90, 24), Qt.AlignmentFlag.AlignCenter,
                             f"在金色区域点击 · 第 {self.game_round + 1}/6 击   得分 {self.game_score}")
            gauge = QRectF(50, 96, self.width() - 100, 24)
            painter.setPen(QPen(QColor(106, 148, 139), 1.5))
            painter.setBrush(QColor(4, 15, 20, 225))
            painter.drawRoundedRect(gauge, 8, 8)
            zone_x = gauge.left() + (self.game_zone_center - self.game_zone_half) * gauge.width()
            zone_w = self.game_zone_half * 2 * gauge.width()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 207, 67, 210))
            painter.drawRoundedRect(QRectF(zone_x, gauge.top() + 2, zone_w, gauge.height() - 4), 6, 6)
            perfect_x = gauge.left() + (self.game_zone_center - 0.026) * gauge.width()
            painter.setBrush(QColor(255, 250, 196, 245))
            painter.drawRect(QRectF(perfect_x, gauge.top() + 2, 0.052 * gauge.width(), gauge.height() - 4))
            marker_x = gauge.left() + self.game_marker_position(now) * gauge.width()
            painter.setPen(QPen(QColor(255, 255, 255), 3))
            painter.drawLine(QPointF(marker_x, gauge.top() - 7), QPointF(marker_x, gauge.bottom() + 7))
            for index in range(6):
                color = QColor(70, 88, 89, 210)
                if index < len(self.game_results):
                    color = (QColor(255, 238, 142) if self.game_results[index] == 3 else
                             QColor(90, 214, 147) if self.game_results[index] == 2 else
                             QColor(215, 105, 91) if self.game_results[index] == 0 else QColor(115, 168, 202))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawEllipse(QPointF(170 + index * 24, 136), 6, 6)
        else:
            title = "相位记忆 · 复写术式"
            if self.game_state == "show":
                instruction = "记住依次亮起的相位，不要急着点击"
            else:
                instruction = f"按原顺序点击 · {self.game_input_index}/{len(self.game_sequence)}"
            painter.drawText(QRect(45, 20, self.width() - 90, 25), Qt.AlignmentFlag.AlignCenter, title)
            painter.setPen(QColor(220, 244, 235))
            painter.drawText(QRect(45, 47, self.width() - 90, 24), Qt.AlignmentFlag.AlignCenter, instruction)
            colors = (QColor(255, 202, 64), QColor(84, 210, 167), QColor(104, 167, 255), QColor(228, 103, 176))
            for index, center in enumerate(self.phase_centers()):
                active = index == self.game_flash_index
                color = colors[index]
                painter.setPen(QPen(QColor(255, 247, 192) if active else color, 3 if active else 1.5))
                painter.setBrush(QColor(color.red(), color.green(), color.blue(), 235 if active else 145))
                radius = 31 if active else 25
                painter.drawEllipse(center, radius, radius)
                painter.drawPolygon(QPolygonF([
                    center + QPointF(0, -13), center + QPointF(11, 7),
                    center + QPointF(-11, 7),
                ]))
                painter.drawEllipse(center, 8, 8)
        painter.restore()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.spear_adjust_mode:
                if self.spear_hit_test(event.position()):
                    self.spear_drag_active = True
                    self.spear_drag_origin = QPointF(event.position())
                    self.spear_offset_origin = self.spear_offset()
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                    self.grabMouse()
                event.accept()
                return
            if self.game_mode:
                self.handle_inline_game_click(event.position())
                event.accept()
                return
            self.drag_origin = event.globalPosition().toPoint()
            self.window_origin = self.pos()
            self.drag_distance = 0
            self.drag_visual_active = False
            self.grabMouse()
            self.drag_started.emit()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.context_requested.emit(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.spear_adjust_mode:
            if self.spear_drag_active:
                if not (event.buttons() & Qt.MouseButton.LeftButton):
                    self.abort_spear_drag()
                    self.spear_transform_committed.emit()
                    event.accept()
                    return
                scale = max(0.01, float(self.state["scale"]))
                delta = event.position() - self.spear_drag_origin
                self.set_spear_transform(
                    self.spear_offset_origin[0] + delta.x() / scale,
                    self.spear_offset_origin[1] + delta.y() / scale,
                )
            else:
                self.setCursor(
                    Qt.CursorShape.OpenHandCursor if self.spear_hit_test(event.position())
                    else Qt.CursorShape.ArrowCursor
                )
            event.accept()
            return
        if self.drag_origin is not None and self.window_origin is not None:
            # 透明顶层窗口偶尔可能漏收释放事件；发现左键已经抬起时立即解除陈旧拖动态。
            if not (event.buttons() & Qt.MouseButton.LeftButton):
                moved = self.drag_distance >= 8
                self.abort_body_drag()
                if moved:
                    self.moved_by_user.emit(self.pos())
                event.accept()
                return
            delta = event.globalPosition().toPoint() - self.drag_origin
            self.drag_distance = max(self.drag_distance, abs(delta.x()) + abs(delta.y()))
            if self.drag_distance >= 8 and not self.drag_visual_active:
                self.drag_visual_active = True
                self.mirror_sprite = False
                self.set_action("drag", 0.0, "喂，别像那只笨猫一样叼着我！")
            self.move(self.window_origin + delta)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.spear_adjust_mode:
            if self.spear_drag_active:
                self.abort_spear_drag()
                self.spear_transform_committed.emit()
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton and self.drag_origin is not None:
            moved = self.drag_distance >= 8
            final_position = self.pos()
            # 先清状态再发同步信号，避免归位/贴边回调看见一个已经结束的拖动。
            self.abort_body_drag()
            if not moved:
                self.clicked.emit()
            else:
                self.moved_by_user.emit(final_position)
            event.accept()

    def abort_body_drag(self) -> None:
        """无条件结束鼠标拖动，供异常释放、归位、隐藏和退出共同使用。"""
        self.drag_visual_active = False
        self.drag_origin = None
        self.window_origin = None
        self.drag_distance = 0
        if QWidget.mouseGrabber() is self:
            self.releaseMouse()

    def abort_spear_drag(self) -> None:
        self.spear_drag_active = False
        self.setCursor(Qt.CursorShape.OpenHandCursor if self.spear_adjust_mode else Qt.CursorShape.ArrowCursor)
        if QWidget.mouseGrabber() is self:
            self.releaseMouse()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.game_mode or self.spear_adjust_mode:
                event.accept()
                return
            self.double_clicked.emit()
            event.accept()

    def wheelEvent(self, event) -> None:
        delta = 0.06 if event.angleDelta().y() > 0 else -0.06
        value = round(clamp(float(self.state["scale"]) + delta, 0.72, 1.18), 2)
        self.scale_changed.emit(value)
        event.accept()


class RestDialog(QDialog):
    """预设与自定义时长共存的轻量休息选择窗。"""

    def __init__(self, current_minutes: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("欧提努斯 · 休息时间")
        self.setWindowIcon(QIcon(str(resource_path("assets/othinus_icon_v4_fullbody.ico"))))
        self.setFixedSize(350, 210)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QDialog { background:#0b1719; color:#eaffed; font-family:'Microsoft YaHei UI'; }
            QLabel { color:#dff7e8; }
            QComboBox, QSpinBox { background:#13292b; color:#fff2b0; border:1px solid #477966;
                border-radius:7px; padding:6px; min-height:24px; }
            QPushButton { background:#1b5945; color:white; border:1px solid #72bf8d;
                border-radius:8px; padding:7px 18px; }
            QPushButton:hover { background:#28765a; }
        """)
        layout = QVBoxLayout(self)
        title = QLabel("要让她休息多久？")
        title.setStyleSheet("font-size:17px;font-weight:700;color:#ffe28a;")
        layout.addWidget(title)
        form = QFormLayout()
        self.preset = QComboBox()
        self.preset.addItem("短暂小憩 · 1 分钟", 1)
        self.preset.addItem("安稳休息 · 5 分钟", 5)
        self.preset.addItem("长睡恢复 · 15 分钟", 15)
        self.preset.addItem("自定义时长", 0)
        self.custom = QSpinBox()
        self.custom.setRange(1, 180)
        self.custom.setSuffix(" 分钟")
        self.custom.setValue(max(1, min(180, current_minutes)))
        preset_values = (1, 5, 15)
        self.preset.setCurrentIndex(preset_values.index(current_minutes) if current_minutes in preset_values else 3)
        self.preset.currentIndexChanged.connect(self.update_custom_state)
        form.addRow("选择", self.preset)
        form.addRow("自定义", self.custom)
        layout.addLayout(form)
        hint = QLabel("休息期间会持续恢复精力；单击或选择其它互动可提前叫醒她。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#7fa99a;font-size:10px;")
        layout.addWidget(hint)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("开始休息")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.update_custom_state()

    def update_custom_state(self) -> None:
        self.custom.setEnabled(int(self.preset.currentData()) == 0)

    def selected_minutes(self) -> int:
        preset = int(self.preset.currentData())
        return self.custom.value() if preset == 0 else preset


class WorldEndOverlay(QWidget):
    """跨屏、无输入阻塞的世界终结与重启演出。"""

    restarting = Signal()
    finished = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("世界终结演出")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.figure = QPixmap(str(resource_path("assets/destroy_world_full.png")))
        self.declaration_pixmap = QPixmap(str(resource_path("assets/destroy_declaration.png")))
        self.started_at = 0.0
        self.duration = 8.4
        self.restart_emitted = False
        rng = random.Random(80308)
        self.cracks: list[list[tuple[float, float]]] = []
        for index in range(24):
            angle = math.tau * index / 24 + rng.uniform(-0.08, 0.08)
            points = [(0.5, 0.48)]
            for step in range(1, 6):
                radius = step * 0.13
                wobble = rng.uniform(-0.035, 0.035)
                points.append((
                    0.5 + math.cos(angle) * radius + wobble,
                    0.48 + math.sin(angle) * radius * 0.72 + wobble,
                ))
            self.cracks.append(points)
        self.shards = [
            (rng.random(), rng.random(), rng.uniform(8, 34), rng.uniform(18, 75), rng.uniform(-1.0, 1.0))
            for _ in range(95)
        ]
        self.stars = [
            (rng.random(), rng.random(), rng.uniform(0.8, 3.4), rng.uniform(0.3, 1.0))
            for _ in range(180)
        ]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

    def start_effect(self) -> None:
        virtual = QRect()
        for screen in QApplication.screens():
            virtual = virtual.united(screen.geometry())
        self.setGeometry(virtual)
        self.started_at = time.monotonic()
        self.restart_emitted = False
        self.show()
        self.raise_()
        self.timer.start(33)

    def tick(self) -> None:
        elapsed = time.monotonic() - self.started_at
        if elapsed >= 4.8 and not self.restart_emitted:
            self.restart_emitted = True
            self.restarting.emit()
        if elapsed >= self.duration:
            self.timer.stop()
            self.hide()
            self.finished.emit()
            return
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        elapsed = max(0.0, time.monotonic() - self.started_at)
        width = self.width()
        height = self.height()
        canvas = QRectF(self.rect())
        center = QPointF(width * 0.5, height * 0.48)

        if elapsed < 2.35:
            charge = min(1.0, elapsed / 1.25)
            gradient = QRadialGradient(center, max(width, height) * 0.72)
            gradient.setColorAt(0.0, QColor(255, 220, 92, round(120 * charge)))
            gradient.setColorAt(0.34, QColor(120, 18, 28, round(190 * charge)))
            gradient.setColorAt(1.0, QColor(0, 0, 0, round(238 * charge)))
            painter.fillRect(canvas, QBrush(gradient))
            if not self.figure.isNull():
                scale = min(width * 0.56 / self.figure.width(), height * 0.91 / self.figure.height())
                figure_w = round(self.figure.width() * scale)
                figure_h = round(self.figure.height() * scale)
                target = QRect(round((width - figure_w) / 2), height - figure_h, figure_w, figure_h)
                painter.setOpacity(min(1.0, charge * 1.4))
                painter.drawPixmap(target, self.figure)
                painter.setOpacity(1.0)

            # 主神之枪发动前的多层魔法阵与放射光束。
            painter.save()
            painter.translate(center)
            painter.rotate(elapsed * 13.0)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for index in range(5):
                radius = min(width, height) * (0.16 + index * 0.065) * (0.55 + charge * 0.45)
                alpha = round((180 - index * 24) * charge)
                painter.setPen(QPen(QColor(255, 223, 104, alpha), 1.2 + (index % 2)))
                painter.drawEllipse(QPointF(0, 0), radius, radius)
                for spoke in range(0, 360, 45):
                    angle = math.radians(spoke + index * 9)
                    inner = radius * 0.86
                    painter.drawLine(
                        QPointF(math.cos(angle) * inner, math.sin(angle) * inner),
                        QPointF(math.cos(angle) * radius, math.sin(angle) * radius),
                    )
            painter.restore()

            # 宣誓采用电影字幕式渐入，不再用结局标签直接跳脸。
            text_alpha = max(0.0, min(1.0, elapsed / 0.45, (2.35 - elapsed) / 0.45))
            if text_alpha > 0 and not self.declaration_pixmap.isNull():
                max_text_width = width * 0.90
                max_text_height = height * 0.17
                text_scale = min(
                    max_text_width / self.declaration_pixmap.width(),
                    max_text_height / self.declaration_pixmap.height(),
                )
                text_width = round(self.declaration_pixmap.width() * text_scale)
                text_height = round(self.declaration_pixmap.height() * text_scale)
                text_target = QRect(
                    round((width - text_width) / 2),
                    round(height * 0.77),
                    text_width,
                    text_height,
                )
                painter.setOpacity(text_alpha)
                painter.drawPixmap(text_target, self.declaration_pixmap)
                painter.setOpacity(1.0)

        crack_strength = max(0.0, min(1.0, (elapsed - 0.7) / 1.1))
        if crack_strength > 0 and elapsed < 4.9:
            painter.setPen(QPen(QColor(255, 220, 92, round(230 * crack_strength)), 2.2))
            for points in self.cracks:
                painter.drawPolyline(QPolygonF([QPointF(x * width, y * height) for x, y in points]))

        if 1.55 <= elapsed <= 2.25:
            flash = math.sin((elapsed - 1.55) / 0.70 * math.pi)
            painter.fillRect(canvas, QColor(255, 249, 218, round(245 * max(0.0, flash))))

        if 2.0 < elapsed < 5.2:
            darkness = min(1.0, (elapsed - 2.0) / 0.65)
            painter.fillRect(canvas, QColor(0, 0, 0, round(252 * darkness)))
            fall = elapsed - 2.0
            collapse = min(1.0, fall / 1.8)
            # 世界相位向中心收缩：星点、光线和碎片逐渐被黑暗吞没。
            painter.setPen(Qt.PenStyle.NoPen)
            for x, y, size, pulse in self.stars:
                px = center.x() + (x * width - center.x()) * (1.0 - collapse * 0.88)
                py = center.y() + (y * height - center.y()) * (1.0 - collapse * 0.88)
                alpha = round(210 * darkness * pulse * max(0.0, 1.0 - fall / 3.4))
                painter.setBrush(QColor(255, 223, 118, alpha))
                painter.drawEllipse(QPointF(px, py), size, size)
            painter.setPen(Qt.PenStyle.NoPen)
            for x, y, size, speed, drift in self.shards:
                px = (x * width + drift * fall * 45) % max(1, width)
                py = (y * height + speed * fall) % max(1, height)
                painter.setBrush(QColor(126, 19, 29, max(0, round(190 - fall * 34))))
                painter.drawPolygon(QPolygonF([
                    QPointF(px, py), QPointF(px + size, py + size * 0.25),
                    QPointF(px + size * 0.35, py + size),
                ]))
            void = QRadialGradient(center, max(width, height) * 0.38)
            void.setColorAt(0.0, QColor(0, 0, 0, 255))
            void.setColorAt(0.18 + collapse * 0.25, QColor(0, 0, 0, 248))
            void.setColorAt(0.62, QColor(88, 4, 17, round(175 * (1.0 - collapse))))
            void.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.fillRect(canvas, QBrush(void))

        if elapsed >= 4.65:
            restart = min(1.0, (elapsed - 4.65) / 2.2)
            fade = max(0.0, min(1.0, (self.duration - elapsed) / 1.0))
            sky = QLinearGradient(0, 0, 0, height)
            sky.setColorAt(0.0, QColor(4, 18, 36, round(250 * fade)))
            sky.setColorAt(0.58, QColor(15, 83, 89, round(235 * fade)))
            sky.setColorAt(1.0, QColor(247, 220, 126, round(210 * restart * fade)))
            painter.fillRect(canvas, QBrush(sky))
            # 光柱与重新出现的星点表达“重构”，不使用解释性大字。
            beam = QLinearGradient(width * 0.5 - width * 0.13, 0, width * 0.5 + width * 0.13, 0)
            beam.setColorAt(0.0, QColor(255, 246, 190, 0))
            beam.setColorAt(0.5, QColor(255, 246, 190, round(105 * restart * fade)))
            beam.setColorAt(1.0, QColor(255, 246, 190, 0))
            painter.fillRect(QRectF(width * 0.35, 0, width * 0.30, height), QBrush(beam))
            painter.setPen(Qt.PenStyle.NoPen)
            for x, y, size, pulse in self.stars:
                reveal = max(0.0, min(1.0, restart * 1.5 - y * 0.5))
                painter.setBrush(QColor(255, 239, 172, round(205 * reveal * pulse * fade)))
                painter.drawEllipse(QPointF(x * width, y * height), size, size)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for index in range(7):
                radius = (restart * max(width, height) * 0.58 + index * 82) % (max(width, height) * 0.72)
                painter.setPen(QPen(QColor(255, 229, 133, round((150 - index * 14) * fade)), 2))
                painter.drawEllipse(center, radius, radius)


class StatusPanel(QWidget):
    request_action = Signal(str)

    def __init__(self, controller) -> None:
        super().__init__()
        self.controller = controller
        self.setWindowTitle("欧提努斯 · 成长档案")
        self.setWindowIcon(QIcon(str(resource_path("assets/othinus_icon_v4_fullbody.ico"))))
        self.setFixedSize(450, 690)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QWidget { background: #0b1719; color: #eaffed; font-family: 'Microsoft YaHei UI'; }
            QFrame#card { background: #112629; border: 1px solid #315c4c; border-radius: 14px; }
            QLabel#name { color: #ffe28a; font-size: 22px; font-weight: 700; }
            QLabel#sub { color: #8ccfaf; font-size: 12px; }
            QPushButton { background: #173f36; border: 1px solid #4da879; border-radius: 10px; padding: 8px; font-weight: 600; }
            QPushButton:hover { background: #24624e; border-color: #f2d66f; }
            QProgressBar { background: #081113; border: 1px solid #315c4c; border-radius: 7px; text-align: center; height: 16px; }
            QProgressBar::chunk { background: #4bd88b; border-radius: 6px; }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(8)

        header = QFrame(objectName="card")
        header_layout = QHBoxLayout(header)
        portrait = QLabel()
        portrait.setPixmap(QPixmap(str(resource_path("assets/othinus_icon_v4_fullbody.png"))).scaled(82, 82, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        portrait.setFixedSize(88, 88)
        names = QVBoxLayout()
        self.name_label = QLabel(objectName="name")
        self.title_label = QLabel(objectName="sub")
        self.level_label = QLabel()
        names.addWidget(self.name_label)
        names.addWidget(self.title_label)
        names.addWidget(self.level_label)
        header_layout.addWidget(portrait)
        header_layout.addLayout(names, 1)
        outer.addWidget(header)

        self.xp_label = QLabel()
        self.xp_bar = self.make_bar("#dfbd43")
        outer.addWidget(self.xp_label)
        outer.addWidget(self.xp_bar)

        stat_card = QFrame(objectName="card")
        stats = QGridLayout(stat_card)
        self.bars = {}
        stat_info = [("fullness", "饱食度", "#e5b65e"), ("energy", "精力", "#67c9ff"), ("mood", "心情", "#ff7ead"), ("affection", "亲密度", "#8cf083")]
        for row, (key, label, color) in enumerate(stat_info):
            stats.addWidget(QLabel(label), row, 0)
            bar = self.make_bar(color)
            stats.addWidget(bar, row, 1)
            self.bars[key] = bar
        outer.addWidget(stat_card)

        growth_card = QFrame(objectName="card")
        growth = QVBoxLayout(growth_card)
        growth.setContentsMargins(12, 9, 12, 9)
        growth.setSpacing(4)
        self.bond_label = QLabel()
        self.mastery_label = QLabel()
        self.mastery_label.setWordWrap(True)
        self.record_label = QLabel()
        self.record_label.setWordWrap(True)
        growth.addWidget(self.bond_label)
        growth.addWidget(self.mastery_label)
        growth.addWidget(self.record_label)
        outer.addWidget(growth_card)

        self.coin_label = QLabel()
        self.achievement_label = QLabel()
        self.achievement_label.setWordWrap(True)
        outer.addWidget(self.coin_label)
        outer.addWidget(self.achievement_label)

        buttons = QGridLayout()
        actions = [
            ("投喂饼干", "feed"), ("一起玩", "play"), ("摸摸头", "pat"),
            ("释放魔法", "magic"), ("召唤神枪", "spear"), ("战斗演练", "battle"),
            ("休息", "sleep"), ("随机表情", "mood"), ("随机桌面游戏", "game"),
            ("相位馈赠", "phase_gift"),
        ]
        for index, (label, action) in enumerate(actions):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, value=action: self.request_action.emit(value))
            buttons.addWidget(button, index // 3, index % 3)
        outer.addLayout(buttons)

        hint = QLabel("提示：拖动她移动；单击摸头；双击施法；滚轮缩放；右键打开菜单。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#759c91;font-size:10px;")
        outer.addWidget(hint)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)
        self.refresh()

    def make_bar(self, color: str) -> QProgressBar:
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setStyleSheet(f"QProgressBar::chunk {{ background: {color}; border-radius: 6px; }}")
        return bar

    def refresh(self) -> None:
        state = self.controller.state
        level = int(state["level"])
        needed = state.xp_needed(level)
        self.name_label.setText(state["name"])
        self.title_label.setText(state.title)
        self.level_label.setText(f"等级 {level}  ·  下一级还需 {max(0, needed-int(state['xp']))} XP")
        self.xp_label.setText(f"经验值  {int(state['xp'])} / {needed}")
        self.xp_bar.setValue(round(int(state["xp"]) / needed * 100))
        self.bars["fullness"].setValue(round(float(state["fullness"])))
        self.bars["energy"].setValue(round(float(state["energy"])))
        self.bars["mood"].setValue(round(float(state["mood"])))
        self.bars["affection"].setValue(state.bond_progress)
        self.bond_label.setText(
            f"羁绊阶段：{state.bond_title}  ·  亲密 {int(state['affection'])}  ·  连续相伴 {int(state['daily_streak'])} 天"
        )
        self.mastery_label.setText("熟练度：" + "　".join(state.mastery_label(key) for key in ("rune", "gungnir", "phase")))
        records = state["game_records"]
        self.record_label.setText(
            f"游戏纪录：符文 {records['rune_best']}　神枪 {records['gungnir_best']}/18　"
            f"相位 {records['phase_best']}　完美校准 {records['perfects']} 次"
        )
        interactions = sum(value for key, value in state["counters"].items() if not key.startswith("game_"))
        self.coin_label.setText(
            f"饼干币：{int(state['coins'])}    相位碎片：{int(state['phase_fragments'])}    累计互动：{interactions}"
        )
        achievements = state["achievements"]
        unlocks = state["unlocks"]
        self.achievement_label.setText(
            "成就：" + ("、".join(achievements[-3:]) if achievements else "尚未解锁——去和她互动吧")
            + "\n成长解锁：" + ("、".join(unlocks[-3:]) if unlocks else "继续提升羁绊与熟练度")
        )

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()


class PetController:
    def __init__(self, app: QApplication, smoke_test: bool = False) -> None:
        self.app = app
        self.smoke_test = smoke_test
        self.state = SaveData()
        self.pet = PetWindow(self.state)
        self.panel = StatusPanel(self)
        self.world_effect = WorldEndOverlay()
        self.rest_until = 0.0
        self.rest_total_seconds = 0.0
        self.last_interaction = 0.0
        self.last_notification = 0.0
        self.wander_target: QPoint | None = None
        self.wander_position: tuple[float, float] | None = None
        self.active_edge: str | None = None
        self.next_wander_at = time.monotonic() + random.uniform(55.0, 100.0)

        self.pet.clicked.connect(self.pat)
        self.pet.double_clicked.connect(self.magic)
        self.pet.drag_started.connect(self.begin_user_drag)
        self.pet.context_requested.connect(self.show_menu)
        self.pet.scale_changed.connect(self.change_scale)
        self.pet.moved_by_user.connect(self.remember_position)
        self.pet.sprite_changed.connect(self.keep_edge_anchor)
        self.pet.inline_game_finished.connect(self.game_reward)
        self.pet.spear_transform_committed.connect(self.save_spear_transform)
        self.panel.request_action.connect(self.handle_action)
        self.world_effect.restarting.connect(self.announce_world_restart)
        self.world_effect.finished.connect(self.finish_world_restart)

        self.tray = QSystemTrayIcon(QIcon(str(resource_path("assets/othinus_icon_v4_fullbody.ico"))), app)
        self.menu = self.build_menu()
        self.tray.setContextMenu(self.menu)
        self.tray.setToolTip(APP_NAME)
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()

        self.place_pet()
        self.pet.show()
        self.pet.raise_()
        self.daily_reward()

        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self.heartbeat)
        self.heartbeat_timer.start(1000)
        self.motion_timer = QTimer()
        self.motion_timer.timeout.connect(self.advance_wander)
        self.motion_timer.start(33)
        self.auto_timer = QTimer()
        self.auto_timer.timeout.connect(self.autonomous_action)
        self.auto_timer.start(16000)
        self.save_timer = QTimer()
        self.save_timer.timeout.connect(self.save)
        self.save_timer.start(30000)

        QTimer.singleShot(1100, lambda: self.pet.set_action("wave", 4.2, "喂，理解者。我会待在桌面右下角。"))
        if not smoke_test:
            QTimer.singleShot(1600, lambda: self.tray.showMessage(APP_NAME, "单击我可显示/隐藏桌宠，右键还有更多互动。", QSystemTrayIcon.MessageIcon.Information, 3500))

    def build_menu(self) -> QMenu:
        menu = QMenu()
        menu.setStyleSheet("QMenu{background:#102226;color:#edfff1;border:1px solid #4c8c6a;padding:6px;} QMenu::item{padding:7px 28px;} QMenu::item:selected{background:#245a45;}")
        self.visible_action = QAction("隐藏桌宠", menu)
        self.visible_action.triggered.connect(self.toggle_pet)
        menu.addAction(self.visible_action)
        status = QAction("成长档案", menu)
        status.triggered.connect(self.show_panel)
        menu.addAction(status)
        menu.addSeparator()
        actions = [
            ("摸摸头", self.pat), ("投喂饼干", self.feed), ("一起玩", self.play),
            ("释放魔法", self.magic), ("挥挥手", self.wave), ("休息一下…", self.choose_rest),
            ("吓她一跳", self.surprise), ("随机动作表情", self.random_mood),
            ("召唤主神之枪", self.summon_spear), ("主神之枪战斗", self.battle),
            ("听取今日神谕", self.daily_oracle), ("相位馈赠", self.use_phase_gift),
        ]
        for text, slot in actions:
            action = QAction(text, menu)
            action.triggered.connect(slot)
            menu.addAction(action)
        game_menu = menu.addMenu("桌面小游戏")
        game_menu.setStyleSheet(menu.styleSheet())
        for text, mode in (
            ("北欧符文追迹", "rune"),
            ("主神之枪校准", "gungnir"),
            ("相位记忆", "phase"),
        ):
            game_action = QAction(text, game_menu)
            game_action.triggered.connect(lambda _checked=False, value=mode: self.start_inline_game(value))
            game_menu.addAction(game_action)
        cancel_game = QAction("结束当前小游戏", game_menu)
        cancel_game.triggered.connect(self.pet.cancel_inline_game)
        game_menu.addSeparator()
        game_menu.addAction(cancel_game)
        menu.addSeparator()
        destroy_action = QAction("毁灭世界（演出）", menu)
        destroy_action.triggered.connect(self.destroy_world)
        menu.addAction(destroy_action)
        menu.addSeparator()
        self.spear_float_action = QAction("主神之枪常驻漂浮", menu, checkable=True)
        self.spear_float_action.setChecked(bool(self.state["spear_float"]))
        self.spear_float_action.toggled.connect(self.toggle_spear_float)
        menu.addAction(self.spear_float_action)
        spear_settings_menu = menu.addMenu("主神之枪调整")
        spear_settings_menu.setStyleSheet(menu.styleSheet())
        self.spear_adjust_action = QAction("调整主神之枪位置", spear_settings_menu, checkable=True)
        self.spear_adjust_action.toggled.connect(self.toggle_spear_adjust)
        spear_settings_menu.addAction(self.spear_adjust_action)
        spear_angle_action = QAction("输入主神之枪角度…", spear_settings_menu)
        spear_angle_action.triggered.connect(self.choose_spear_angle)
        spear_settings_menu.addAction(spear_angle_action)
        spear_size_action = QAction("输入主神之枪尺寸…", spear_settings_menu)
        spear_size_action.triggered.connect(self.choose_spear_size)
        spear_settings_menu.addAction(spear_size_action)
        spear_settings_menu.addSeparator()
        spear_reset_action = QAction("恢复默认位置、角度和尺寸", spear_settings_menu)
        spear_reset_action.triggered.connect(self.reset_spear_transform)
        spear_settings_menu.addAction(spear_reset_action)
        menu.addSeparator()
        self.wander_action = QAction("自动散步", menu, checkable=True)
        self.wander_action.setChecked(bool(self.state["auto_wander"]))
        self.wander_action.toggled.connect(self.toggle_wander)
        menu.addAction(self.wander_action)
        self.sound_action = QAction("互动提示音", menu, checkable=True)
        self.sound_action.setChecked(bool(self.state["sound"]))
        self.sound_action.toggled.connect(self.toggle_sound)
        menu.addAction(self.sound_action)
        reset = QAction("回到右下角", menu)
        reset.triggered.connect(self.reset_position)
        menu.addAction(reset)
        menu.addSeparator()
        about = QAction(f"关于 · 粉丝自制桌宠 v{APP_VERSION}", menu)
        about.setEnabled(False)
        menu.addAction(about)
        author = QAction("制作：天底 / 安娜修普林凯勒", menu)
        author.setEnabled(False)
        menu.addAction(author)
        quit_action = QAction("退出桌宠", menu)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)
        return menu

    def beep(self) -> None:
        if self.state["sound"] and not self.smoke_test:
            QApplication.beep()

    def place_pet(self) -> None:
        saved = self.state["position"]
        if isinstance(saved, list) and len(saved) == 2:
            self.pet.move(int(saved[0]), int(saved[1]))
            self.keep_on_screen()
        else:
            self.reset_position()

    def reset_position(self) -> None:
        # “回到右下角”同时是移动状态的硬复位，不能让旧散步目标在下一帧重新接管位置。
        self.pet.abort_body_drag()
        self.pet.abort_spear_drag()
        self.cancel_wander()
        area = QApplication.primaryScreen().availableGeometry()
        visible = self.pet.sprite_content_rect("idle_neutral", mirrored=False)
        # 默认位置与右、下边缘保留小间距，不误触发边缘动作。
        self.active_edge = None
        self.pet.mirror_sprite = False
        self.pet.set_action("idle", 0.0)
        self.pet.move(
            area.right() - visible.right() - 12,
            area.bottom() - visible.bottom() - 10,
        )
        self.state["position"] = [self.pet.x(), self.pet.y()]
        self.state.save()

    def keep_on_screen(self) -> None:
        screen = QApplication.screenAt(self.pet.frameGeometry().center()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        visible = self.pet.global_sprite_content_rect()
        left_margin, top_margin, right_margin, bottom_margin = ACTION_MOTION_MARGINS.get(
            self.pet.action, DEFAULT_SCREEN_MARGIN
        )
        shift_x = 0
        shift_y = 0
        if visible.left() < area.left() + left_margin:
            shift_x = area.left() + left_margin - visible.left()
        elif visible.right() > area.right() - right_margin:
            shift_x = area.right() - right_margin - visible.right()
        if visible.top() < area.top() + top_margin:
            shift_y = area.top() + top_margin - visible.top()
        elif visible.bottom() > area.bottom() - bottom_margin:
            shift_y = area.bottom() - bottom_margin - visible.bottom()
        if shift_x or shift_y:
            self.pet.move(self.pet.x() + shift_x, self.pet.y() + shift_y)

    def remember_position(self, point: QPoint) -> None:
        self.cancel_wander(return_to_idle=False)
        self.active_edge = None
        self.keep_on_screen()
        self.state["position"] = [self.pet.x(), self.pet.y()]
        self.state.save()
        self.apply_edge_action()

    def begin_user_drag(self) -> None:
        """鼠标按下即取得移动所有权，避免自动散步与人工拖动争抢窗口位置。"""
        self.cancel_wander()
        self.active_edge = None
        self.pet.mirror_sprite = False

    def toggle_pet(self) -> None:
        if self.pet.isVisible():
            self.pet.abort_body_drag()
            self.pet.abort_spear_drag()
            self.cancel_wander()
            self.pet.hide()
            self.visible_action.setText("显示桌宠")
        else:
            self.pet.show()
            self.pet.raise_()
            self.visible_action.setText("隐藏桌宠")

    def tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.toggle_pet()

    def show_menu(self, point: QPoint) -> None:
        self.menu.popup(point)

    def show_panel(self) -> None:
        self.panel.refresh()
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()

    def handle_action(self, name: str) -> None:
        {
            "feed": self.feed, "play": self.play, "pat": self.pat,
            "magic": self.magic, "spear": self.summon_spear, "battle": self.battle,
            "sleep": self.choose_rest, "wave": self.wave, "mood": self.random_mood,
            "game": self.start_game, "phase_gift": self.use_phase_gift,
        }[name]()

    def dialogue(self, kind: str) -> str:
        lines = {
            "pat": ["哼，勉强允许你摸一下。", "理解者的手……还算温暖。", "再摸的话，要支付一枚饼干。", "别把帽子弄歪了。"],
            "feed": ["这块饼干还算有品位。", "魔神也需要补充糖分。", "我只是替你检查味道。", "再来一块也不是不行。"],
            "play": ["抓得到我吗，理解者？", "这种小游戏，我可不会输。", "偶尔陪你胡闹也不错。", "看好了，这是魔神的步法。"],
            "magic": ["北欧符文，回应我。", "别眨眼，奇迹只出现一次。", "这点魔法只算热身。", "世界啊，稍微安静一下。"],
            "wave": ["喂，我在这里。", "今天也别把我忘了。", "理解者，工作顺利吗？"],
            "sleep": ["今天的世界先交给你。", "只是闭眼思考，不是困。", "帽子借我当枕头……"],
            "surprise": ["什、什么？突然做什么！", "差点让你得逞了。", "魔神也是会被吓到的！"],
            "spear": ["主神之枪，回应我的召唤。", "别碰，它可不是装饰品。", "让它陪我看守你的桌面。"],
            "battle": ["理解者，看清魔神的战斗方式。", "这一击只作演练。", "主神之枪——锁定。"],
        }
        return random.choice(lines[kind])

    def cooldown(self, seconds: float = 0.9) -> bool:
        if self.pet.game_mode or self.pet.spear_adjust_mode:
            return False
        now = time.monotonic()
        if now - self.last_interaction < seconds:
            return False
        self.last_interaction = now
        self.cancel_wander(return_to_idle=False)
        return True

    def modify(self, *, fullness=0.0, energy=0.0, mood=0.0, affection=0.0, xp=0, coins=0) -> None:
        old_bond_rank = self.state.bond_rank
        self.state["fullness"] = clamp(float(self.state["fullness"]) + fullness)
        self.state["energy"] = clamp(float(self.state["energy"]) + energy)
        self.state["mood"] = clamp(float(self.state["mood"]) + mood)
        self.state["affection"] = max(0, int(self.state["affection"]) + affection)
        self.state["coins"] = max(0, int(self.state["coins"]) + coins)
        if xp:
            self.gain_xp(xp)
        self.check_achievements()
        self.update_unlocks()
        if self.state.bond_rank > old_bond_rank:
            self.pet.spawn_particles("heart", 18)
        self.update_tray_tip()

    def gain_xp(self, amount: int) -> None:
        self.state["xp"] = int(self.state["xp"]) + amount
        levels_gained = 0
        coin_reward = 0
        fragment_reward = 0
        while self.state["xp"] >= self.state.xp_needed(int(self.state["level"])):
            needed = self.state.xp_needed(int(self.state["level"]))
            self.state["xp"] -= needed
            self.state["level"] = int(self.state["level"]) + 1
            new_level = int(self.state["level"])
            reward = 3 + (2 if new_level % 5 == 0 else 0)
            fragments = 1 + (1 if new_level % 5 == 0 else 0)
            self.state["coins"] = int(self.state["coins"]) + reward
            self.state["phase_fragments"] = int(self.state["phase_fragments"]) + fragments
            levels_gained += 1
            coin_reward += reward
            fragment_reward += fragments
        if levels_gained:
            self.pet.set_action(
                "jump", 3.0,
                f"升到 Lv.{self.state['level']} · {self.state.title}！获得 {coin_reward} 饼干币和 {fragment_reward} 相位碎片。",
            )
            self.pet.spawn_particles("star", 30)
            if not self.smoke_test:
                self.tray.showMessage(
                    "等级提升",
                    f"欧提努斯升到 Lv.{self.state['level']}，获得 {coin_reward} 饼干币与 {fragment_reward} 相位碎片。",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000,
                )

    def count(self, key: str) -> None:
        self.state["counters"][key] = int(self.state["counters"].get(key, 0)) + 1

    def pat(self) -> None:
        if not self.cooldown():
            return
        self.count("pat")
        self.modify(mood=3.5, affection=1, xp=2)
        self.pet.set_action("pat", 2.7, self.dialogue("pat"))
        self.pet.spawn_particles("heart", 9)
        self.beep()

    def feed(self) -> None:
        if not self.cooldown():
            return
        if int(self.state["coins"]) <= 0:
            self.pet.set_action("angry", 2.8, "饼干库存空了。去抓几个符文换饼干币吧！")
            return
        self.count("feed")
        self.modify(fullness=19, mood=5, affection=1, xp=5, coins=-1)
        self.pet.set_action("eat", 3.2, self.dialogue("feed"))
        self.beep()

    def play(self) -> None:
        if not self.cooldown():
            return
        if float(self.state["energy"]) < 12:
            self.start_rest(3.0, automatic=True, text="现在玩不动了……先让我睡一会儿。")
            return
        self.count("play")
        self.modify(fullness=-2, energy=-9, mood=15, affection=1, xp=8)
        self.pet.set_action(random.choice(("jump", "laugh")), 3.0, self.dialogue("play"))
        self.beep()

    def magic(self) -> None:
        if not self.cooldown():
            return
        if float(self.state["energy"]) < 10:
            self.start_rest(3.0, automatic=True, text="魔力不足。先让我认真休息一会儿。")
            return
        self.count("magic")
        self.modify(fullness=-1, energy=-11, mood=7, affection=1, xp=9)
        self.pet.set_action("magic", 3.8, self.dialogue("magic"))
        self.beep()

    def summon_spear(self) -> None:
        if not self.cooldown():
            return
        if float(self.state["energy"]) < 6:
            self.pet.set_action("tired", 2.8, "现在的魔力不足以召唤主神之枪。")
            return
        self.modify(energy=-5, mood=5, affection=1, xp=7)
        self.pet.set_action("spear_idle", 4.2, self.dialogue("spear"))
        self.pet.spawn_particles("magic", 22)
        self.beep()

    def battle(self) -> None:
        if not self.cooldown():
            return
        if float(self.state["energy"]) < 14:
            self.start_rest(4.0, automatic=True, text="今天的战斗演练到此为止……魔神也需要恢复。")
            return
        self.count("battle")
        self.modify(fullness=-2, energy=-14, mood=11, affection=1, xp=13)
        self.pet.set_action("battle", 4.2, self.dialogue("battle"))
        self.pet.spawn_particles("magic", 32)
        QTimer.singleShot(5700, self.finish_battle)
        self.beep()

    def finish_battle(self) -> None:
        if self.pet.action == "battle":
            self.pet.set_action("victory", 2.8, "哼，胜负从一开始就决定了。")
            self.pet.spawn_particles("star", 20)

    def destroy_world(self) -> None:
        """新约8结尾意象的非破坏性全屏演出；不会操作用户文件或系统。"""
        if self.world_effect.isVisible() or not self.cooldown(1.5):
            return
        if float(self.state["energy"]) < 24:
            self.start_rest(5.0, automatic=True, text="毁灭世界需要完整的魔神之力。先恢复魔力。")
            return
        self.count("destroy")
        self.modify(fullness=-3, energy=-22, mood=9, affection=1, xp=20)
        self.active_edge = None
        self.pet.set_action(
            "destroy",
            10.0,
            "琐碎的争斗就到此为止吧——",
        )
        self.keep_on_screen()
        self.pet.spawn_particles("magic", 55)
        QTimer.singleShot(950, self.world_effect.start_effect)
        self.beep()

    def announce_world_restart(self) -> None:
        # 重构过程只由全屏光效表达，避免再用解释性文字打断画面。
        self.pet.spawn_particles("star", 18)

    def finish_world_restart(self) -> None:
        self.pet.set_action("idle", 4.5, "……只是玩笑，理解者。你的世界还好好地在这里。")
        self.pet.spawn_particles("star", 30)
        self.state.save()

    def daily_oracle(self) -> None:
        """同一天给出稳定的轻量神谕，作为不消耗资源的小互动。"""
        if not self.cooldown(0.5):
            return
        seed = date.today().toordinal() * 131 + int(self.state["level"]) * 17
        oracle = random.Random(seed).choice((
            "今日神谕：先解决最小的麻烦，世界会自己让出道路。",
            "今日神谕：适合整理桌面，也适合奖励自己一块饼干。",
            "今日神谕：别被进度条欺骗，真正重要的是你已经开始了。",
            "今日神谕：遇到难题就休息五分钟，魔神批准了。",
            "今日神谕：今天的幸运物，是放在手边的那杯饮料。",
            "今日神谕：保持一点任性。完全正确的人生会很无聊。",
        ))
        self.count("oracle")
        self.modify(mood=2, affection=1, xp=1)
        self.pet.set_action(random.choice(("magic", "confused", "idle")), 5.0, oracle)

    def random_mood(self) -> None:
        if not self.cooldown():
            return
        action, text = random.choice([
            ("confused", "你刚才是不是在发呆？"),
            ("shy", "别、别一直盯着我看。"),
            ("yawn", "只是稍微有一点困。"),
            ("bored", "理解者，找点有趣的事吧。"),
            ("gift", "这个给你。别误会，只是奖励。"),
            ("laugh", "呵，今天的你还挺有趣。"),
        ])
        self.modify(mood=2, affection=1, xp=2)
        self.pet.set_action(action, 3.2, text)

    def wave(self) -> None:
        if not self.cooldown():
            return
        self.modify(mood=2, xp=1)
        self.pet.set_action("wave", 2.5, self.dialogue("wave"))

    def choose_rest(self) -> None:
        if not self.cooldown(0.2):
            return
        dialog = RestDialog(int(self.state["rest_minutes"]))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        minutes = dialog.selected_minutes()
        self.state["rest_minutes"] = minutes
        self.start_rest(float(minutes), automatic=False)

    def start_rest(self, minutes: float, automatic: bool = False, text: str = "") -> None:
        seconds = max(3.0, float(minutes) * 60.0)
        self.rest_total_seconds = seconds
        self.rest_until = time.monotonic() + seconds
        if not text:
            text = random.choice([
                self.dialogue("sleep"),
                "当麻玩偶只是临时抱枕……不许笑。",
                "理解者就在这里，所以能睡得安稳一点。",
                f"那就休息 {max(1, round(minutes))} 分钟。时间到了记得叫我。",
            ])
        self.pet.set_action("sleep", seconds, text)
        if not automatic:
            self.modify(mood=3, affection=1, xp=2)
        self.state.save()

    def sleep(self) -> None:
        """供自动行为和兼容旧调用使用；主动菜单使用 choose_rest。"""
        self.start_rest(1.0, automatic=True)

    def surprise(self) -> None:
        if not self.cooldown():
            return
        self.modify(energy=-2, mood=-1, xp=2)
        self.pet.set_action("surprise", 2.8, self.dialogue("surprise"))
        QTimer.singleShot(3300, self.finish_surprise)
        self.beep()

    def finish_surprise(self) -> None:
        if self.pet.action == "surprise":
            self.pet.set_action("angry", 4.2, "下次轮到我吓你。")

    def change_scale(self, value: float) -> None:
        self.state["scale"] = value
        # 神枪使用角色局部逻辑坐标；缩放后只重新约束边界，不改变保存的相对布局。
        spear_x, spear_y = self.pet.spear_offset()
        self.pet.set_spear_transform(spear_x, spear_y)
        self.pet.say(f"体型缩放：{round(value * 100)}%", 1.6)
        self.state.save()
        if self.active_edge:
            self.snap_pet_to_edge(self.active_edge)

    def start_game(self) -> None:
        """成长档案中的快捷按钮会轮换三种桌面内游戏。"""
        choices = ["rune", "gungnir", "phase"]
        total = int(self.state["game_records"].get("total", 0))
        self.start_inline_game(choices[total % len(choices)])

    def start_inline_game(self, mode: str) -> None:
        if self.pet.game_mode or self.world_effect.isVisible():
            return
        if not self.cooldown(0.45):
            return
        if float(self.state["energy"]) < 8:
            self.start_rest(3.0, automatic=True, text="这种演练也要消耗魔力。先休息一下。")
            return
        mastery = self.state.mastery_level(mode)
        if self.pet.start_inline_game(mode, mastery):
            self.active_edge = None
            self.modify(fullness=-1, energy=-3, mood=2)
            self.keep_on_screen()
            self.beep()

    def game_reward(self, mode: str, score: int, auxiliary: int) -> None:
        names = {"rune": "符文追迹", "gungnir": "神枪校准", "phase": "相位记忆"}
        record_keys = {"rune": "rune_best", "gungnir": "gungnir_best", "phase": "phase_best"}
        records = self.state["game_records"]
        key = record_keys[mode]
        records[key] = max(int(records.get(key, 0)), score)
        records["total"] = int(records.get("total", 0)) + 1
        if mode == "rune":
            records["best_combo"] = max(int(records.get("best_combo", 0)), auxiliary)
        elif mode == "gungnir":
            records["perfects"] = int(records.get("perfects", 0)) + auxiliary

        self.count("game")
        self.count(f"game_{mode}")
        mastery_gain = max(5, score * 2 + auxiliary * 2)
        self.state["mastery"][mode] = int(self.state["mastery"].get(mode, 0)) + mastery_gain
        reward_multiplier = 1.0 + self.state.bond_rank * 0.06 + min(0.18, max(0, int(self.state["level"]) - 1) * 0.01)
        xp = round((7 + score * 2.4 + auxiliary) * reward_multiplier)
        coins = max(1, round((score / 4 + auxiliary / 3) * reward_multiplier))
        fragments = max(1, score // 6 + (1 if mode == "phase" and auxiliary else 0))
        self.state["phase_fragments"] = int(self.state["phase_fragments"]) + fragments
        self.modify(mood=min(18, 5 + score), affection=1 + (1 if score >= 8 else 0), xp=xp, coins=coins)

        success = score >= (8 if mode == "rune" else 10 if mode == "gungnir" else len(self.pet.game_sequence))
        # phase 序列在信号发出前已清空，使用辅助完成标记判断。
        if mode == "phase":
            success = bool(auxiliary)
        action = "victory" if mode == "gungnir" and success else "jump" if success else "confused"
        self.pet.set_action(
            action,
            5.0,
            f"{names[mode]}：{score} 分。熟练度 +{mastery_gain}，获得 {coins} 饼干币与 {fragments} 相位碎片。",
        )
        self.state.save()

    def use_phase_gift(self) -> None:
        if not self.cooldown(0.5):
            return
        fragments = int(self.state["phase_fragments"])
        if fragments < 5:
            self.pet.set_action("confused", 4.0, f"相位馈赠需要 5 枚碎片，现在只有 {fragments} 枚。")
            return
        self.state["phase_fragments"] = fragments - 5
        self.modify(fullness=12, energy=26, mood=18, affection=2, xp=8)
        self.pet.set_action("gift", 5.0, "把五枚相位碎片重构成祝福。今天就稍微偏爱你一点。")
        self.pet.spawn_particles("magic", 28)
        self.state.save()

    def daily_reward(self) -> None:
        today = date.today().isoformat()
        if self.state["last_daily"] != today:
            yesterday = date.fromordinal(date.today().toordinal() - 1).isoformat()
            streak = int(self.state["daily_streak"]) + 1 if self.state["last_daily"] == yesterday else 1
            self.state["daily_streak"] = streak
            self.state["best_daily_streak"] = max(int(self.state["best_daily_streak"]), streak)
            self.state["last_daily"] = today
            coins = 2 + min(3, streak // 3)
            fragments = 1 if streak % 3 == 0 else 0
            self.state["phase_fragments"] = int(self.state["phase_fragments"]) + fragments
            self.modify(mood=5, affection=1 if streak >= 3 else 0, xp=12 + min(10, streak), coins=coins)
            extra = f"、{fragments} 枚相位碎片" if fragments else ""
            QTimer.singleShot(
                3500,
                lambda: self.pet.set_action(
                    "eat", 4.2,
                    f"连续相伴第 {streak} 天：获得 {coins} 枚饼干币{extra}。明天也要来。",
                ),
            )

    def check_achievements(self) -> None:
        counters = self.state["counters"]
        candidates = []
        if counters.get("pat", 0) >= 1:
            candidates.append("第一次摸头")
        if counters.get("feed", 0) >= 5:
            candidates.append("饼干鉴赏家")
        if counters.get("magic", 0) >= 10:
            candidates.append("符文共鸣")
        if counters.get("battle", 0) >= 5:
            candidates.append("主神之枪的见证者")
        if counters.get("game", 0) >= 3:
            candidates.append("魔神的游乐场")
        records = self.state["game_records"]
        if int(records.get("rune_best", 0)) >= 12:
            candidates.append("符文猎手")
        if int(records.get("gungnir_best", 0)) >= 15:
            candidates.append("神枪同调者")
        if int(records.get("phase_best", 0)) >= 5:
            candidates.append("相位书记官")
        if int(self.state["daily_streak"]) >= 7:
            candidates.append("七日理解者")
        if self.state.bond_rank >= 3:
            candidates.append("可靠的理解者")
        if min(self.state.mastery_level(key) for key in ("rune", "gungnir", "phase")) >= 3:
            candidates.append("三术式精通")
        if counters.get("destroy", 0) >= 1:
            candidates.append("世界重启见证者")
        if counters.get("oracle", 0) >= 7:
            candidates.append("神谕记录者")
        if int(self.state["level"]) >= 5:
            candidates.append("真正的理解者")
        for name in candidates:
            if name not in self.state["achievements"]:
                self.state["achievements"].append(name)
                self.state["coins"] = int(self.state["coins"]) + 2
                self.state["phase_fragments"] = int(self.state["phase_fragments"]) + 1
                self.pet.say(f"成就解锁：{name}（+2 饼干币、+1 相位碎片）", 3.5)

    def update_unlocks(self) -> None:
        candidates = []
        if int(self.state["level"]) >= 3:
            candidates.append("成长加成：游戏经验提升")
        if self.state.bond_rank >= 2:
            candidates.append("羁绊加成：游戏奖励提升")
        for key, label in (("rune", "稳定符文轨迹"), ("gungnir", "宽幅共鸣区"), ("phase", "延长相位显现")):
            if self.state.mastery_level(key) >= 3:
                candidates.append(label)
        if int(self.state["daily_streak"]) >= 3:
            candidates.append("连续相伴奖励")
        for name in candidates:
            if name not in self.state["unlocks"]:
                self.state["unlocks"].append(name)

    def heartbeat(self) -> None:
        if self.pet.action == "sleep":
            energy = float(self.state["energy"])
            recovery = 0.30 if energy < 20 else 0.20
            self.state["energy"] = clamp(energy + recovery)
        else:
            self.rest_until = 0.0
            self.rest_total_seconds = 0.0
            self.state["energy"] = clamp(float(self.state["energy"]) - 0.009)
        self.state["fullness"] = clamp(float(self.state["fullness"]) - 0.018)
        if float(self.state["fullness"]) < 22:
            self.state["mood"] = clamp(float(self.state["mood"]) - 0.025)
        self.maybe_start_wander()
        self.update_tray_tip()

    def autonomous_action(self) -> None:
        if self.pet.spear_adjust_mode or self.pet.action != "idle" or not self.pet.isVisible():
            return
        fullness = float(self.state["fullness"])
        energy = float(self.state["energy"])
        mood = float(self.state["mood"])
        if energy < 8:
            self.start_rest(random.uniform(5.0, 7.0), automatic=True, text="魔力见底了……这次要多睡一会儿。")
        elif fullness < 15:
            self.pet.set_action("cry", 4.0, "理解者……饼干库存是不是被你忘了？")
            self.notify_need("欧提努斯饿了", "投喂一块饼干，或者玩符文小游戏赚取饼干币。")
        elif energy < 18:
            self.start_rest(random.uniform(3.0, 5.0), automatic=True, text="精力太低了。我会认真休息一阵。")
        elif energy < 30 and random.random() < 0.62:
            self.start_rest(random.uniform(1.0, 2.5), automatic=True, text="趁现在补充一点魔力……")
        elif mood < 20:
            self.pet.set_action("cry", 4.0, "是不是该陪我玩一会儿了？")
        else:
            action = random.choices(
                ["idle", "wave", "jump", "magic", "surprise", "confused", "yawn", "bored", "spear_idle"],
                weights=[24, 15, 12, 10, 8, 8, 8, 8, 7],
                k=1,
            )[0]
            if action == "idle":
                self.pet.set_action("idle", 0.0)
                if random.random() < 0.4:
                    self.pet.say(random.choice(["今天的桌面还算和平。", "忙完记得休息。", "我在看着你呢。"]), 2.7)
            elif action in ("magic", "spear_idle") and energy < 25:
                self.pet.set_action("wave", 2.2)
            else:
                self.pet.set_action(action, random.uniform(4.2, 5.8))

    def notify_need(self, title: str, text: str) -> None:
        now = time.monotonic()
        if not self.smoke_test and now - self.last_notification > 900:
            self.last_notification = now
            self.tray.showMessage(title, text, QSystemTrayIcon.MessageIcon.Warning, 4500)

    def maybe_start_wander(self) -> None:
        """低频触发一次短途二维散步，避免角色长时间保持立正姿势平移。"""
        now = time.monotonic()
        if (
            not self.state["auto_wander"]
            or not self.pet.isVisible()
            or self.pet.spear_adjust_mode
            or self.pet.drag_origin is not None
            or self.wander_target is not None
            or now < self.next_wander_at
        ):
            return
        if self.pet.action != "idle":
            self.next_wander_at = now + 15.0
            return

        screen = QApplication.screenAt(self.pet.frameGeometry().center()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        current = self.pet.pos()
        edge_trip = random.random() < 0.28
        if edge_trip:
            edge = random.choice(("left", "right", "top", "bottom"))
            walk_mirror = edge == "left"
            target = self.edge_target_position(edge, area, "walk_step", walk_mirror)
        else:
            visible = self.pet.sprite_content_rect("walk_step", mirrored=False)
            min_x = area.left() - visible.left()
            max_x = max(min_x, area.right() - visible.right())
            min_y = area.top() - visible.top()
            max_y = max(min_y, area.bottom() - visible.bottom())
            target = QPoint(
                max(min_x, min(max_x, current.x() + random.randint(-260, 260))),
                max(min_y, min(max_y, current.y() + random.randint(-140, 140))),
            )
            if (target - current).manhattanLength() < 60:
                target = QPoint(max(min_x, min(max_x, current.x() + random.choice((-120, 120)))), target.y())

        self.active_edge = None
        self.wander_target = target
        self.wander_position = (float(current.x()), float(current.y()))
        self.pet.mirror_sprite = target.x() < current.x()
        self.pet.set_action("walk", 0.0)

    def advance_wander(self) -> None:
        if self.wander_target is None or self.wander_position is None:
            return
        if not self.state["auto_wander"] or not self.pet.isVisible():
            self.cancel_wander()
            return
        if self.pet.drag_origin is not None:
            self.cancel_wander(return_to_idle=False)
            return

        x, y = self.wander_position
        actual = self.pet.pos()
        if abs(actual.x() - round(x)) + abs(actual.y() - round(y)) > 8:
            # 菜单归位、系统窗口移动或异常拖动改变了真实位置：旧轨迹立即失效。
            self.cancel_wander()
            self.keep_on_screen()
            return
        dx = self.wander_target.x() - x
        dy = self.wander_target.y() - y
        distance = math.hypot(dx, dy)
        step = 2.65  # 约 80px/s；移动短促，避免几分钟的“立正滑行”。
        if distance <= step:
            self.pet.move(self.wander_target)
            self.wander_target = None
            self.wander_position = None
            self.state["position"] = [self.pet.x(), self.pet.y()]
            self.state.save()
            self.next_wander_at = time.monotonic() + random.uniform(90.0, 180.0)
            self.apply_edge_action()
            return

        x += dx / distance * step
        y += dy / distance * step
        self.wander_position = (x, y)
        self.pet.move(round(x), round(y))

    def edge_kind(self) -> str | None:
        screen = QApplication.screenAt(self.pet.frameGeometry().center()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        visible = self.pet.global_sprite_content_rect()
        distances = {
            "left": abs(visible.left() - area.left()),
            "right": abs(area.right() - visible.right()),
            "top": abs(visible.top() - area.top()),
            "bottom": abs(area.bottom() - visible.bottom()),
        }
        edge = min(distances, key=distances.get)
        return edge if distances[edge] <= EDGE_TRIGGER_DISTANCE else None

    def edge_target_position(
        self,
        edge: str,
        area: QRect,
        sprite_name: str,
        mirrored: bool,
    ) -> QPoint:
        """给定动作的真实 alpha 边界，计算刚好贴屏且另一轴完整可见的位置。"""
        local = self.pet.sprite_content_rect(sprite_name, mirrored)
        min_x = area.left() - local.left()
        max_x = max(min_x, area.right() - local.right())
        min_y = area.top() - local.top()
        max_y = max(min_y, area.bottom() - local.bottom())
        if edge == "left":
            return QPoint(min_x, random.randint(min_y, max_y))
        if edge == "right":
            return QPoint(max_x, random.randint(min_y, max_y))
        if edge == "top":
            return QPoint(random.randint(min_x, max_x), min_y)
        return QPoint(random.randint(min_x, max_x), max_y)

    def snap_pet_to_edge(self, edge: str) -> None:
        """边缘姿势零间隙贴屏；动态姿势留安全内缩，避免动画越出屏幕。"""
        screen = QApplication.screenAt(self.pet.frameGeometry().center()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        local = self.pet.sprite_content_rect()
        x = self.pet.x()
        y = self.pet.y()
        inset = ACTION_EDGE_INSETS.get(self.pet.action, 0)
        if edge == "left":
            x = area.left() - local.left() + inset
        elif edge == "right":
            x = area.right() - local.right() - inset
        elif edge == "top":
            y = area.top() - local.top() + inset
        elif edge == "bottom":
            y = area.bottom() - local.bottom() - inset

        # 沿边移动时仍确保帽子、披风和脚的另一轴完整可见。
        x = max(area.left() - local.left(), min(x, area.right() - local.right()))
        y = max(area.top() - local.top(), min(y, area.bottom() - local.bottom()))
        self.pet.move(x, y)
        self.state["position"] = [x, y]

    def keep_edge_anchor(self, _sprite_name: str) -> None:
        """切换贴图后重新校正真实轮廓：贴边则重锚定，否则保证整张动作留在屏内。"""
        if self.pet.drag_origin is not None or self.wander_target is not None:
            return

        def settle_sprite() -> None:
            if self.active_edge:
                self.snap_pet_to_edge(self.active_edge)
            else:
                self.keep_on_screen()

        QTimer.singleShot(0, settle_sprite)

    def apply_edge_action(self) -> None:
        edge = self.edge_kind()
        if edge in ("left", "right"):
            self.active_edge = edge
            # 左边缘使用原图、右边缘镜像，使扶墙与探头方向朝向对应屏幕边界。
            self.pet.mirror_sprite = edge == "right"
            self.pet.set_action("edge", 5.5, random.choice(("这里就是世界的边缘？", "屏幕外面有什么？", "让我探头看看。")))
        elif edge == "top":
            self.active_edge = edge
            self.pet.mirror_sprite = False
            self.pet.set_action("drag", 5.2, "别把我挂在屏幕顶上。")
        elif edge == "bottom":
            self.active_edge = edge
            self.pet.mirror_sprite = False
            self.pet.set_action("bored", 5.5, "这里倒是适合稍微休息。")
        else:
            self.active_edge = None
            self.pet.mirror_sprite = False
            self.pet.set_action("idle", 0.0)
            return
        self.snap_pet_to_edge(edge)
        self.state.save()

    def cancel_wander(self, return_to_idle: bool = True) -> None:
        was_walking = self.pet.action == "walk"
        self.wander_target = None
        self.wander_position = None
        self.next_wander_at = time.monotonic() + random.uniform(90.0, 180.0)
        if was_walking:
            self.pet.mirror_sprite = False
        if return_to_idle and was_walking:
            self.pet.set_action("idle", 0.0)

    def toggle_wander(self, checked: bool) -> None:
        self.state["auto_wander"] = checked
        self.cancel_wander()
        self.state.save()

    def toggle_spear_float(self, checked: bool) -> None:
        if not checked and self.pet.spear_adjust_mode:
            self.spear_adjust_action.setChecked(False)
        self.state["spear_float"] = checked
        if checked:
            self.pet.set_action("spear_idle", 3.4, "主神之枪会暂时守在我身边。")
        else:
            self.pet.set_action("idle", 1.8, "收起来了，需要时再召唤。")
        self.state.save()

    def toggle_spear_adjust(self, checked: bool) -> None:
        """进入桌宠画布内的神枪局部坐标调整模式。"""
        self.cancel_wander()
        self.active_edge = None
        if checked:
            if self.pet.game_mode:
                self.pet.cancel_inline_game()
            self.state["spear_float"] = True
            self.spear_float_action.blockSignals(True)
            self.spear_float_action.setChecked(True)
            self.spear_float_action.blockSignals(False)
            self.pet.spear_adjust_mode = True
            self.pet.spear_drag_active = False
            self.pet.mirror_sprite = False
            self.pet.set_action("idle", 0.0)
            spear_x, spear_y = self.pet.spear_offset()
            self.pet.set_spear_transform(spear_x, spear_y)
            self.pet.setCursor(Qt.CursorShape.OpenHandCursor)
            self.spear_adjust_action.setText("完成主神之枪调整")
            self.pet.say("直接拖动神枪；角度可从右键菜单输入。", 4.0)
        else:
            self.pet.spear_adjust_mode = False
            self.pet.abort_spear_drag()
            self.spear_adjust_action.setText("调整主神之枪位置")
            self.pet.say("位置已固定。它会保持相对位置随我移动。", 3.2)
        self.pet.update()
        self.save_spear_transform()

    def choose_spear_angle(self) -> None:
        angle, accepted = QInputDialog.getDouble(
            self.pet,
            "调整主神之枪角度",
            "角度（-180° 到 180°）：",
            self.pet.spear_angle(),
            -180.0,
            180.0,
            1,
        )
        if not accepted:
            return
        spear_x, spear_y = self.pet.spear_offset()
        self.pet.set_spear_transform(spear_x, spear_y, angle)
        self.ensure_spear_floating()
        self.save_spear_transform()
        self.pet.say(f"主神之枪角度：{self.pet.spear_angle():+.1f}°", 2.4)

    def choose_spear_size(self) -> None:
        percent, accepted = QInputDialog.getInt(
            self.pet,
            "调整主神之枪尺寸",
            "浮动神枪尺寸（相对原尺寸）：",
            round(self.pet.spear_scale() * 100),
            round(SPEAR_SCALE_RANGE[0] * 100),
            round(SPEAR_SCALE_RANGE[1] * 100),
            5,
        )
        if not accepted:
            return
        spear_x, spear_y = self.pet.spear_offset()
        self.pet.set_spear_transform(spear_x, spear_y, spear_scale=percent / 100.0)
        self.ensure_spear_floating()
        self.save_spear_transform()
        self.pet.say(f"主神之枪尺寸：{percent}%", 2.4)

    def ensure_spear_floating(self) -> None:
        self.state["spear_float"] = True
        self.spear_float_action.blockSignals(True)
        self.spear_float_action.setChecked(True)
        self.spear_float_action.blockSignals(False)
        self.pet.update()

    def reset_spear_transform(self) -> None:
        self.pet.set_spear_transform(
            SPEAR_DEFAULT_OFFSET[0],
            SPEAR_DEFAULT_OFFSET[1],
            SPEAR_DEFAULT_ANGLE,
            SPEAR_DEFAULT_SCALE,
        )
        self.ensure_spear_floating()
        self.save_spear_transform()
        self.pet.say("主神之枪已回到默认位置。", 2.7)

    def save_spear_transform(self) -> None:
        """位置已由 PetWindow 写入状态；这里只负责可靠落盘。"""
        self.state.save()

    def toggle_sound(self, checked: bool) -> None:
        self.state["sound"] = checked
        self.state.save()

    def update_tray_tip(self) -> None:
        rest = ""
        if self.pet.action == "sleep" and self.rest_until > time.monotonic():
            remaining = max(1, math.ceil((self.rest_until - time.monotonic()) / 60))
            rest = f"\n休息剩余约 {remaining} 分钟"
        self.tray.setToolTip(
            f"{APP_NAME} · Lv.{self.state['level']}\n"
            f"饱食 {round(self.state['fullness'])}  精力 {round(self.state['energy'])}  心情 {round(self.state['mood'])}{rest}"
        )

    def save(self) -> None:
        self.state["position"] = [self.pet.x(), self.pet.y()]
        self.state.save()

    def quit(self) -> None:
        self.pet.abort_body_drag()
        self.pet.abort_spear_drag()
        self.cancel_wander(return_to_idle=False)
        self.save()
        self.world_effect.timer.stop()
        self.world_effect.hide()
        self.tray.hide()
        self.app.quit()


def main() -> int:
    smoke_test = "--smoke-test" in sys.argv
    if smoke_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(QIcon(str(resource_path("assets/othinus_icon_v4_fullbody.ico"))))
    app.setQuitOnLastWindowClosed(False)

    lock_name = "OthinusDesktopPet-smoke.lock" if smoke_test else "OthinusDesktopPet-single-instance.lock"
    lock = QLockFile(os.path.join(QDir.tempPath(), lock_name))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        return 0

    controller = PetController(app, smoke_test=smoke_test)
    app.aboutToQuit.connect(controller.save)
    if smoke_test:
        # 离屏验证神枪变换、三种内嵌游戏、睡姿与全屏演出后干净退出；不碰正式存档。
        if controller.world_effect.figure.isNull() or controller.world_effect.declaration_pixmap.isNull():
            raise RuntimeError("destroy-world overlay asset is missing")
        QTimer.singleShot(40, controller.reset_spear_transform)
        QTimer.singleShot(80, lambda: controller.spear_adjust_action.setChecked(True))
        QTimer.singleShot(120, lambda: controller.pet.set_spear_transform(35.0, -158.0, -24.0))
        QTimer.singleShot(160, lambda: controller.spear_adjust_action.setChecked(False))
        QTimer.singleShot(180, lambda: controller.pet.start_inline_game("rune", 1))
        QTimer.singleShot(650, controller.pet.cancel_inline_game)
        QTimer.singleShot(900, lambda: controller.pet.start_inline_game("gungnir", 1))
        QTimer.singleShot(1350, controller.pet.cancel_inline_game)
        QTimer.singleShot(1600, lambda: controller.pet.start_inline_game("phase", 1))
        QTimer.singleShot(2050, controller.pet.cancel_inline_game)
        QTimer.singleShot(2300, controller.magic)
        QTimer.singleShot(3300, controller.battle)
        QTimer.singleShot(4100, controller.sleep)
        QTimer.singleShot(5000, controller.destroy_world)
        QTimer.singleShot(6500, controller.quit)
    result = app.exec()
    lock.unlock()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
