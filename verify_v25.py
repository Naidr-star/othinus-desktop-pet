#!/usr/bin/env python3
"""欧提努斯桌宠 v2.6.2 的离屏发布验证。"""

from __future__ import annotations

import json
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if "--smoke-test" not in sys.argv:
    sys.argv.append("--smoke-test")

import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

import othinus_pet as pet_app


def alpha_margins(image: QImage) -> tuple[int, int, int, int]:
    """返回非透明内容距左、上、右、下边界的像素数。"""
    raw = np.frombuffer(image.constBits(), dtype=np.uint8, count=image.sizeInBytes())
    rows = raw.reshape(image.height(), image.bytesPerLine())
    alpha = rows[:, 3:image.width() * 4:4]
    ys, xs = np.where(alpha > 0)
    if not len(xs):
        raise AssertionError("render produced an empty image")
    return (
        int(xs.min()),
        int(ys.min()),
        int(image.width() - 1 - xs.max()),
        int(image.height() - 1 - ys.max()),
    )


def render_widget(widget) -> QImage:
    image = QImage(widget.width(), widget.height(), QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
    widget.render(image)
    return image


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    state = pet_app.SaveData()
    state["scale"] = 1.18
    state["spear_float"] = False
    pet = pet_app.PetWindow(state)
    pet.anim_timer.stop()
    pet.bubble_until = 0.0

    minimum_margin = 10_000
    tightest = None
    render_count = 0
    for action, variants in pet_app.ACTION_VARIANTS.items():
        for sprite_name in variants:
            for progress in (0.0, 0.25, 0.5, 0.75, 1.0):
                pet.action = action
                pet.sprite_name = sprite_name
                pet.previous_sprite_name = None
                pet.action_duration = 10.0
                pet.action_started = time.monotonic() - progress * pet.action_duration
                pet.phase = progress * 6.4
                pet.mirror_sprite = False
                pet.particles.clear()
                margins = alpha_margins(render_widget(pet))
                render_count += 1
                candidate = min(margins)
                if candidate < minimum_margin:
                    minimum_margin = candidate
                    tightest = (action, sprite_name, progress, margins)
                if candidate <= 0:
                    raise AssertionError(f"sprite clipping: {action}/{sprite_name}/{progress}: {margins}")

    dialog = pet_app.RestDialog(7)
    assert int(dialog.preset.currentData()) == 0 and dialog.custom.isEnabled()
    dialog.custom.setValue(42)
    assert dialog.selected_minutes() == 42
    dialog.preset.setCurrentIndex(2)
    assert dialog.selected_minutes() == 15 and not dialog.custom.isEnabled()
    dialog.close()

    overlay = pet_app.WorldEndOverlay()
    overlay.resize(1280, 720)
    assert not overlay.figure.isNull()
    overlay_margins = {}
    overlay_frames = []
    for elapsed in (0.2, 1.1, 1.9, 3.2, 5.5, 7.8):
        overlay.started_at = time.monotonic() - elapsed
        frame = render_widget(overlay)
        overlay_margins[str(elapsed)] = alpha_margins(frame)
        overlay_frames.append(frame)

    if "--effect-preview" in sys.argv:
        preview = QImage(960, 810, QImage.Format.Format_RGBA8888)
        preview.fill(Qt.GlobalColor.black)
        painter = QPainter(preview)
        for index, frame in enumerate(overlay_frames):
            x = (index % 2) * 480
            y = (index // 2) * 270
            painter.drawImage(QRect(x, y, 480, 270), frame)
        painter.end()
        preview.save(os.path.join(os.environ.get("TEMP", "."), "othinus_v251_effect_preview.png"))
        overlay_frames[1].save(os.path.join(os.environ.get("TEMP", "."), "othinus_v251_declaration_preview.png"))

    controller = pet_app.PetController(app, smoke_test=True)
    for timer in (
        controller.pet.anim_timer,
        controller.panel.timer,
        controller.heartbeat_timer,
        controller.motion_timer,
        controller.auto_timer,
        controller.save_timer,
        controller.world_effect.timer,
    ):
        timer.stop()

    controller.start_rest(15.0, automatic=False, text="release test")
    remaining = controller.rest_until - time.monotonic()
    assert controller.pet.action == "sleep" and 899.0 < remaining <= 900.0

    controller.pet.action = "idle"
    controller.state["energy"] = 7.0
    controller.autonomous_action()
    assert controller.pet.action == "sleep"
    assert 300.0 <= controller.rest_total_seconds <= 420.0
    energy_before = float(controller.state["energy"])
    controller.heartbeat()
    assert float(controller.state["energy"]) > energy_before

    area = QApplication.primaryScreen().availableGeometry()
    controller.pet.action = "edge"
    controller.pet.sprite_name = "edge_peek"
    controller.pet.previous_sprite_name = None
    controller.pet.mirror_sprite = False
    controller.active_edge = "left"
    controller.snap_pet_to_edge("left")
    assert controller.pet.global_sprite_content_rect().left() == area.left()

    controller.pet.action = "jump"
    controller.pet.sprite_name = "jump_excited"
    controller.snap_pet_to_edge("left")
    dynamic_gap = controller.pet.global_sprite_content_rect().left() - area.left()
    assert dynamic_gap == pet_app.ACTION_EDGE_INSETS["jump"]

    controller.active_edge = None
    controller.state["scale"] = 1.18
    screen_fit_cases = 0
    for action, variants in pet_app.ACTION_VARIANTS.items():
        margins = pet_app.ACTION_MOTION_MARGINS.get(action, pet_app.DEFAULT_SCREEN_MARGIN)
        for sprite_name in variants:
            controller.pet.action = action
            controller.pet.sprite_name = sprite_name
            controller.pet.previous_sprite_name = None
            for position in (
                (area.left() - controller.pet.width(), area.top() - controller.pet.height()),
                (area.right() + controller.pet.width(), area.bottom() + controller.pet.height()),
            ):
                controller.pet.move(*position)
                controller.keep_on_screen()
                visible = controller.pet.global_sprite_content_rect()
                assert visible.left() >= area.left() + margins[0]
                assert visible.top() >= area.top() + margins[1]
                assert visible.right() <= area.right() - margins[2]
                assert visible.bottom() <= area.bottom() - margins[3]
                screen_fit_cases += 1

    # v2.6.2：神枪使用人物局部坐标，旋转/拖动/缩放后仍完整处于透明画布内。
    controller.reset_spear_transform()
    controller.pet.action = "idle"
    controller.pet.sprite_name = "idle_neutral"
    controller.pet.previous_sprite_name = None
    default_rect = controller.pet.spear_draw_rect(False)
    assert abs(default_rect.center().x() - controller.pet.width() / 2) < 125
    assert controller.pet.spear_angle() == pet_app.SPEAR_DEFAULT_ANGLE
    assert controller.pet.spear_scale() == pet_app.SPEAR_DEFAULT_SCALE
    spear_frame = render_widget(controller.pet)
    assert min(alpha_margins(spear_frame)) > 0

    controller.pet.set_spear_transform(999.0, -999.0, 90.0)
    rotated_bounds = controller.pet.spear_polygon(False).boundingRect()
    assert rotated_bounds.left() >= 7.9
    assert rotated_bounds.top() >= 7.9
    assert rotated_bounds.right() <= controller.pet.width() - 7.9
    assert rotated_bounds.bottom() <= controller.pet.height() - 7.9

    controller.pet.set_spear_transform(999.0, 999.0, 73.0, pet_app.SPEAR_SCALE_RANGE[1])
    maximum_bounds = controller.pet.spear_polygon(False).boundingRect()
    assert controller.pet.spear_scale() == pet_app.SPEAR_SCALE_RANGE[1]
    assert maximum_bounds.left() >= 7.9 and maximum_bounds.top() >= 7.9
    assert maximum_bounds.right() <= controller.pet.width() - 7.9
    assert maximum_bounds.bottom() <= controller.pet.height() - 7.9

    controller.pet.set_spear_transform(42.0, -150.0, -27.0)
    local_center = QPointF(controller.pet.spear_draw_rect(False).center())
    old_window_pos = QPointF(controller.pet.pos())
    controller.pet.move(controller.pet.x() + 37, controller.pet.y() + 23)
    new_global_center = QPointF(controller.pet.pos()) + controller.pet.spear_draw_rect(False).center()
    old_global_center = old_window_pos + local_center
    assert abs((new_global_center.x() - old_global_center.x()) - 37.0) < 0.01
    assert abs((new_global_center.y() - old_global_center.y()) - 23.0) < 0.01

    saved_offset = controller.pet.spear_offset()
    controller.change_scale(0.82)
    scaled_center = controller.pet.spear_draw_rect(False).center()
    assert abs((scaled_center.x() - controller.pet.width() / 2) / 0.82 - saved_offset[0]) < 0.2
    assert abs((scaled_center.y() - pet_app.PET_GROUND_Y) / 0.82 - saved_offset[1]) < 0.2
    controller.spear_adjust_action.setChecked(True)
    assert controller.pet.spear_adjust_mode and controller.spear_adjust_action.isChecked()
    controller.spear_adjust_action.setChecked(False)
    assert not controller.pet.spear_adjust_mode
    controller.reset_spear_transform()
    assert controller.pet.spear_offset() == pet_app.SPEAR_DEFAULT_OFFSET
    assert controller.pet.spear_scale() == pet_app.SPEAR_DEFAULT_SCALE
    spear_checks = 18

    # 自动散步、人工拖动和菜单归位不能同时持有窗口位置。
    controller.state["auto_wander"] = True
    controller.pet.set_action("walk", 0.0)
    walk_start = QPoint(controller.pet.pos())
    controller.wander_position = (float(walk_start.x()), float(walk_start.y()))
    controller.wander_target = walk_start + QPoint(320, 0)
    controller.reset_position()
    reset_pos = QPoint(controller.pet.pos())
    assert controller.wander_target is None and controller.wander_position is None
    controller.advance_wander()
    assert controller.pet.pos() == reset_pos

    controller.pet.set_action("walk", 0.0)
    controller.wander_position = (float(reset_pos.x()), float(reset_pos.y()))
    controller.wander_target = reset_pos + QPoint(250, 0)
    controller.pet.drag_origin = QPoint(100, 100)
    controller.pet.window_origin = QPoint(reset_pos)
    controller.begin_user_drag()
    assert controller.wander_target is None and controller.wander_position is None
    controller.pet.abort_body_drag()
    assert controller.pet.drag_origin is None and controller.pet.window_origin is None

    controller.pet.set_action("walk", 0.0)
    track_start = QPoint(controller.pet.pos())
    controller.wander_position = (float(track_start.x()), float(track_start.y()))
    controller.wander_target = track_start + QPoint(180, 0)
    controller.pet.move(track_start + QPoint(24, 0))
    controller.advance_wander()
    assert controller.wander_target is None and controller.wander_position is None
    movement_state_checks = 9

    if "--spear-preview" in sys.argv:
        preview = QImage(controller.pet.width() * 3, controller.pet.height(), QImage.Format.Format_RGBA8888)
        preview.fill(Qt.GlobalColor.transparent)
        painter = QPainter(preview)
        controller.pet.bubble_until = 0.0
        controller.pet.action = "idle"
        controller.reset_spear_transform()
        painter.drawImage(0, 0, render_widget(controller.pet))
        controller.pet.set_spear_transform(5.0, -154.0, -42.0)
        painter.drawImage(controller.pet.width(), 0, render_widget(controller.pet))
        controller.spear_adjust_action.setChecked(True)
        controller.pet.bubble_until = 0.0
        painter.drawImage(controller.pet.width() * 2, 0, render_widget(controller.pet))
        controller.spear_adjust_action.setChecked(False)
        painter.end()
        preview.save(os.path.join(os.environ.get("TEMP", "."), "othinus_v262_spear_preview.png"))
        controller.reset_spear_transform()

    game_renders = 0
    game_frames = []
    fragments_before = int(controller.state["phase_fragments"])
    controller.last_interaction = 0.0
    controller.state["energy"] = 100.0
    controller.start_inline_game("rune")
    assert controller.pet.game_mode == "rune"
    frame = render_widget(controller.pet)
    alpha_margins(frame)
    game_frames.append(frame)
    game_renders += 1
    controller.pet.handle_inline_game_click(QPointF(controller.pet.game_target))
    assert controller.pet.game_score >= 1
    controller.pet.finish_inline_game()
    assert int(controller.state["game_records"]["total"]) == 1

    controller.last_interaction = 0.0
    controller.start_inline_game("gungnir")
    assert controller.pet.game_mode == "gungnir"
    frame = render_widget(controller.pet)
    alpha_margins(frame)
    game_frames.append(frame)
    game_renders += 1
    for _ in range(6):
        now = time.monotonic()
        controller.pet.game_zone_center = controller.pet.game_marker_position(now)
        controller.pet.handle_inline_game_click(QPointF(230, 108))
    assert controller.pet.game_mode is None
    assert int(controller.state["game_records"]["gungnir_best"]) == 18

    controller.last_interaction = 0.0
    controller.start_inline_game("phase")
    assert controller.pet.game_mode == "phase"
    controller.pet.game_state = "input"
    frame = render_widget(controller.pet)
    alpha_margins(frame)
    game_frames.append(frame)
    game_renders += 1
    sequence = list(controller.pet.game_sequence)
    centers = controller.pet.phase_centers()
    for index in sequence:
        controller.pet.handle_inline_game_click(QPointF(centers[index]))
    assert controller.pet.game_mode is None
    assert int(controller.state["game_records"]["phase_best"]) == len(sequence)
    assert all(controller.state.mastery_level(key) >= 1 for key in ("rune", "gungnir", "phase"))
    assert int(controller.state["phase_fragments"]) > fragments_before

    controller.last_interaction = 0.0
    controller.state["phase_fragments"] = 5
    controller.state["energy"] = 40.0
    controller.use_phase_gift()
    assert int(controller.state["phase_fragments"]) == 0
    assert float(controller.state["energy"]) > 40.0
    controller.panel.refresh()
    controller.panel.layout().activate()
    panel_minimum = controller.panel.minimumSizeHint()
    assert panel_minimum.width() <= controller.panel.width()
    assert panel_minimum.height() <= controller.panel.height()
    render_widget(controller.panel)

    if "--game-preview" in sys.argv:
        preview = QImage(controller.pet.width() * 3, controller.pet.height(), QImage.Format.Format_RGBA8888)
        preview.fill(Qt.GlobalColor.transparent)
        painter = QPainter(preview)
        for index, frame in enumerate(game_frames):
            painter.drawImage(index * controller.pet.width(), 0, frame)
        painter.end()
        preview.save(os.path.join(os.environ.get("TEMP", "."), "othinus_v26_game_preview.png"))

    result = {
        "version": pet_app.APP_VERSION,
        "sprite_renders": render_count,
        "minimum_window_margin_px": minimum_margin,
        "tightest_case": tightest,
        "manual_rest_seconds": round(remaining, 2),
        "low_energy_auto_rest_seconds": round(controller.rest_total_seconds, 2),
        "dynamic_edge_gap_px": dynamic_gap,
        "screen_fit_cases": screen_fit_cases,
        "spear_transform_checks": spear_checks,
        "movement_state_checks": movement_state_checks,
        "inline_game_renders": game_renders,
        "game_records": controller.state["game_records"],
        "growth_panel_minimum": [panel_minimum.width(), panel_minimum.height()],
        "overlay_phases": len(overlay_margins),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    controller.tray.hide()
    controller.pet.close()
    controller.panel.close()
    controller.world_effect.close()
    overlay.close()
    pet.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
