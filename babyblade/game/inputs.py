"""Input mapping: keyboard, gamepad and pointer, turned into menu commands, actions and steering.

Keyboard: arrows/WASD navigate and steer, Enter/Space confirm in menus, Esc back, P pause;
          in battle 1 Charge, 2 Attack, 3 Guard, 4 Special, Space Dodge.
Gamepad:  D-pad/left stick navigate and steer, A confirm, B back, Start pause;
          in battle X=Charge, A=Attack, Y=Guard, B=Dodge, RB=Special.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import pygame

from babyblade.sim.actions import ORDER, Action

_pads: Dict[int, "pygame.joystick.JoystickType"] = {}
_axis_latch: Dict[Tuple[int, int], int] = {}

KEY_NAV = {
    pygame.K_UP: "up", pygame.K_w: "up", pygame.K_DOWN: "down", pygame.K_s: "down",
    pygame.K_LEFT: "left", pygame.K_a: "left", pygame.K_RIGHT: "right", pygame.K_d: "right",
    pygame.K_RETURN: "confirm", pygame.K_KP_ENTER: "confirm", pygame.K_SPACE: "confirm",
    pygame.K_ESCAPE: "back", pygame.K_BACKSPACE: "back",
}
KEY_ACTION = {pygame.K_1: Action.CHARGE, pygame.K_2: Action.ATTACK, pygame.K_3: Action.GUARD,
              pygame.K_4: Action.SPECIAL, pygame.K_SPACE: Action.DODGE,
              pygame.K_KP1: Action.CHARGE, pygame.K_KP2: Action.ATTACK, pygame.K_KP3: Action.GUARD,
              pygame.K_KP4: Action.SPECIAL, pygame.K_KP0: Action.DODGE}
PAD_ACTION = {2: Action.CHARGE, 0: Action.ATTACK, 3: Action.GUARD, 1: Action.DODGE, 5: Action.SPECIAL}


def init() -> None:
    try:
        pygame.joystick.init()
        for i in range(pygame.joystick.get_count()):
            j = pygame.joystick.Joystick(i)
            _pads[j.get_instance_id()] = j
    except Exception:
        pass


def handle_device(event: pygame.event.Event) -> None:
    try:
        if event.type == pygame.JOYDEVICEADDED:
            j = pygame.joystick.Joystick(event.device_index)
            _pads[j.get_instance_id()] = j
        elif event.type == pygame.JOYDEVICEREMOVED:
            _pads.pop(event.instance_id, None)
    except Exception:
        pass


def nav(event: pygame.event.Event) -> Optional[str]:
    if event.type == pygame.KEYDOWN:
        return KEY_NAV.get(event.key)
    if event.type == pygame.JOYBUTTONDOWN:
        return {0: "confirm", 1: "back", 7: "pause", 6: "back"}.get(event.button)
    if event.type == pygame.JOYHATMOTION:
        x, y = event.value
        if y == 1:
            return "up"
        if y == -1:
            return "down"
        if x == -1:
            return "left"
        if x == 1:
            return "right"
    if event.type == pygame.JOYAXISMOTION and event.axis in (0, 1):
        key = (getattr(event, "instance_id", 0), event.axis)
        v = event.value
        state = 1 if v > 0.6 else -1 if v < -0.6 else 0
        if state != _axis_latch.get(key, 0):
            _axis_latch[key] = state
            if state:
                if event.axis == 1:
                    return "down" if state > 0 else "up"
                return "right" if state > 0 else "left"
    return None


def battle_action(event: pygame.event.Event) -> Optional[Action]:
    if event.type == pygame.KEYDOWN and event.key in KEY_ACTION:
        return KEY_ACTION[event.key]
    if event.type == pygame.JOYBUTTONDOWN and event.button in PAD_ACTION:
        return PAD_ACTION[event.button]
    return None


def is_pause(event: pygame.event.Event) -> bool:
    if event.type == pygame.KEYDOWN and event.key in (pygame.K_p, pygame.K_ESCAPE):
        return True
    return event.type == pygame.JOYBUTTONDOWN and event.button == 7


def steer() -> Tuple[float, float]:
    """Held keys plus the first gamepad's left stick (screen axes: +y is down)."""
    x = y = 0.0
    try:
        k = pygame.key.get_pressed()
        x = (k[pygame.K_RIGHT] or k[pygame.K_d]) - (k[pygame.K_LEFT] or k[pygame.K_a])
        y = (k[pygame.K_DOWN] or k[pygame.K_s]) - (k[pygame.K_UP] or k[pygame.K_w])
    except Exception:
        pass
    for j in list(_pads.values()):
        try:
            ax, ay = j.get_axis(0), j.get_axis(1)
            if abs(ax) > 0.2 or abs(ay) > 0.2:
                x, y = x + ax, y + ay
            hx, hy = j.get_hat(0) if j.get_numhats() else (0, 0)
            x, y = x + hx, y - hy
        except Exception:
            pass
        break
    return (float(x), float(y))
