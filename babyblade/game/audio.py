"""Synthesized audio (no sound files): clashes, launch, finishes, crowd, UI, and a spin hum
that drops in pitch as a top loses energy. Every call is guarded; without an audio device the
game simply stays silent."""

from __future__ import annotations

import array
import math
import random
from typing import Dict, List, Optional

import pygame

SR = 22050
_rng = random.Random(42)


def _env(i: int, n: int, attack: float = 0.004, decay: float = 5.0) -> float:
    t = i / SR
    a = min(1.0, t / attack) if attack > 0 else 1.0
    return a * math.exp(-decay * i / max(1, n))


def _noise() -> float:
    return _rng.uniform(-1.0, 1.0)


def _lp(samples: List[float], k: float) -> List[float]:
    out, y = [], 0.0
    for s in samples:
        y += k * (s - y)
        out.append(y)
    return out


def _clash(variant: int) -> List[float]:
    n = int(SR * 0.32)
    f1, f2 = 1650 + variant * 230, 2700 + variant * 310
    out = []
    for i in range(n):
        t = i / SR
        ring = math.sin(2 * math.pi * f1 * t) * 0.5 + math.sin(2 * math.pi * f2 * t) * 0.3 + math.sin(2 * math.pi * 520 * t) * 0.25
        out.append(0.6 * _noise() * _env(i, n, decay=14) + 0.55 * ring * _env(i, n, decay=7))
    return out


def _grind() -> List[float]:
    n = int(SR * 0.12)
    return [(_noise() * 0.7 + math.sin(2 * math.pi * 3100 * i / SR) * 0.3) * _env(i, n, attack=0.01, decay=3) for i in range(n)]


def _whoosh(dur: float = 0.38, rise: bool = False) -> List[float]:
    n = int(SR * dur)
    raw = [_noise() for _ in range(n)]
    lp = _lp(raw, 0.08)
    out = []
    for i in range(n):
        sw = math.sin(math.pi * i / n)
        out.append(lp[i] * 3.5 * (sw ** (0.6 if rise else 1.2)))
    return out


def _charge() -> List[float]:
    n = int(SR * 0.6)
    out = []
    ph = 0.0
    for i in range(n):
        f = 300 + 900 * (i / n) ** 1.5
        ph += 2 * math.pi * f / SR
        out.append((math.sin(ph) * 0.5 + math.sin(ph * 2.01) * 0.25) * min(1.0, i / (SR * 0.05)) * (1 - i / n) ** 0.4)
    return out


def _guard() -> List[float]:
    n = int(SR * 0.35)
    return [(math.sin(2 * math.pi * 140 * i / SR) * 0.8 + math.sin(2 * math.pi * 880 * i / SR) * 0.2) * _env(i, n, decay=6) for i in range(n)]


def _special() -> List[float]:
    n = int(SR * 0.9)
    lp = _lp([_noise() for _ in range(n)], 0.15)
    out = []
    ph = 0.0
    for i in range(n):
        f = 90 + 400 * (1 - i / n) ** 2
        ph += 2 * math.pi * f / SR
        out.append(lp[i] * 2.4 * math.sin(math.pi * i / n) + math.sin(ph) * 0.7 * _env(i, n, attack=0.05, decay=2.5))
    return out


def _burst() -> List[float]:
    n = int(SR * 1.2)
    lp = _lp([_noise() for _ in range(n)], 0.2)
    out = []
    for i in range(n):
        t = i / SR
        boom = math.sin(2 * math.pi * (70 - 30 * i / n) * t) * _env(i, n, decay=3)
        glass = _noise() * _env(i, n, decay=9) * (1 if (i // 900) % 2 == 0 else 0.4)
        out.append(lp[i] * 1.8 * _env(i, n, decay=4) + boom * 0.9 + glass * 0.35)
    return out


def _ringout() -> List[float]:
    n = int(SR * 0.9)
    out, ph = [], 0.0
    lp = _lp([_noise() for _ in range(n)], 0.06)
    for i in range(n):
        f = 900 * (1 - i / n) + 120
        ph += 2 * math.pi * f / SR
        out.append(math.sin(ph) * 0.4 * (1 - i / n) + lp[i] * 2.0 * math.sin(math.pi * i / n))
    return out


def _spinout() -> List[float]:
    n = int(SR * 1.3)
    out, ph = [], 0.0
    for i in range(n):
        f = 260 * (1 - i / n) ** 1.5 + 30
        ph += 2 * math.pi * f / SR
        trem = 0.6 + 0.4 * math.sin(2 * math.pi * (14 * (1 - i / n) + 2) * i / SR)
        out.append(math.sin(ph) * trem * (1 - i / n))
    return out


def _launch() -> List[float]:
    n = int(SR * 0.55)
    out, ph = [], 0.0
    for i in range(n):
        f = 200 + 2400 * (i / n) ** 0.7
        ph += 2 * math.pi * f / SR
        zip_ = 1.0 if (i // 300) % 2 == 0 else 0.55
        out.append((math.sin(ph) * 0.4 + _noise() * 0.5) * zip_ * min(1.0, i / 400) * (1 - i / n) ** 0.3)
    return out


def _beep(freq: float, dur: float = 0.14) -> List[float]:
    n = int(SR * dur)
    return [(math.sin(2 * math.pi * freq * i / SR) + 0.3 * math.sin(4 * math.pi * freq * i / SR)) * _env(i, n, attack=0.003, decay=3) for i in range(n)]


def _go() -> List[float]:
    n = int(SR * 0.6)
    out = [0.0] * n
    for f in (523.25, 659.25, 783.99, 1046.5):
        for i in range(n):
            out[i] += 0.3 * math.sin(2 * math.pi * f * i / SR) * _env(i, n, attack=0.005, decay=2.5)
    return out


def _crowd() -> List[float]:
    n = int(SR * 2.2)
    lp = _lp([_noise() for _ in range(n)], 0.05)
    out = []
    for i in range(n):
        swell = math.sin(math.pi * i / n) ** 0.7
        chatter = 0.75 + 0.25 * math.sin(2 * math.pi * 6.5 * i / SR + math.sin(i / 3000.0))
        out.append(lp[i] * 4.0 * swell * chatter)
    return out


def _alarm() -> List[float]:
    n = int(SR * 0.7)
    return [math.sin(2 * math.pi * (880 if (i // 2200) % 2 == 0 else 660) * i / SR) * 0.6 * (1 - i / n) for i in range(n)]


def _tick() -> List[float]:
    n = int(SR * 0.035)
    return [math.sin(2 * math.pi * 1800 * i / SR) * _env(i, n, decay=6) for i in range(n)]


def _hum(pitch: float) -> List[float]:
    """One second of seamless spin hum (whole-number cycles so it loops cleanly)."""
    n = SR
    f = round(170 * pitch)
    fm = round(f * 3.0)
    out = []
    lp = _lp([_noise() for _ in range(n)], 0.3)
    for i in range(n):
        t = i / SR
        out.append(math.sin(2 * math.pi * f * t) * 0.35 + math.sin(2 * math.pi * fm * t) * 0.12 + lp[i] * 0.25)
    return out


RECIPES = {
    "clash0": (lambda: _clash(0), 0.75), "clash1": (lambda: _clash(1), 0.75), "clash2": (lambda: _clash(2), 0.75),
    "grind": (_grind, 0.25), "whoosh": (_whoosh, 0.55), "charge": (_charge, 0.35), "guard": (_guard, 0.6),
    "special": (_special, 0.85), "burst": (_burst, 0.95), "ringout": (_ringout, 0.8), "spinout": (_spinout, 0.7),
    "launch": (_launch, 0.7), "beep": (lambda: _beep(880), 0.5), "go": (_go, 0.6), "crowd": (_crowd, 0.55),
    "alarm": (_alarm, 0.45), "tick": (_tick, 0.3), "select": (lambda: _beep(1320, 0.08), 0.4),
    "dodge_fail": (lambda: _beep(220, 0.25), 0.5),
}
HUM_LEVELS = (1.0, 0.86, 0.72, 0.58)


def _to_sound(samples: List[float], volume: float) -> pygame.mixer.Sound:
    peak = max(1e-6, max(abs(x) for x in samples))
    k = 32767 * volume / peak
    mono = array.array("h", (int(max(-32767, min(32767, x * k))) for x in samples))
    st = array.array("h", [0]) * (len(mono) * 2)
    st[0::2] = mono
    st[1::2] = mono
    return pygame.mixer.Sound(buffer=st.tobytes())


class Audio:
    def __init__(self) -> None:
        self.ok = False
        self.sfx: Dict[str, pygame.mixer.Sound] = {}
        self.hums: List[pygame.mixer.Sound] = []
        self.master = 0.8
        self.sfx_vol = 0.9
        self.muted = False
        self._hum_level = {1: -1, 2: -1}
        self._hum_ch: Dict[int, Optional[pygame.mixer.Channel]] = {1: None, 2: None}

    def init(self) -> None:
        if self.ok:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SR, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(24)
            pygame.mixer.set_reserved(2)
            self._hum_ch = {1: pygame.mixer.Channel(0), 2: pygame.mixer.Channel(1)}
            self._pending = list(RECIPES.items()) + [(f"hum{i}", (lambda p=p: _hum(p), 0.5)) for i, p in enumerate(HUM_LEVELS)]
            self.ok = True
        except Exception:
            self.ok = False

    def pump(self, budget_s: float = 0.004) -> None:
        """Synthesize pending sounds within a time budget (called once per frame)."""
        if not self.ok or not getattr(self, "_pending", None):
            return
        import time
        end = time.perf_counter() + budget_s
        while self._pending and time.perf_counter() < end:
            name, (fn, vol) = self._pending.pop(0)
            try:
                snd = _to_sound(fn(), vol)
            except Exception:
                continue
            if name.startswith("hum"):
                self.hums.append(snd)
            else:
                self.sfx[name] = snd

    def finish_loading(self) -> None:
        while getattr(self, "_pending", None):
            self.pump(10.0)

    def play(self, name: str, volume: float = 1.0) -> None:
        if not self.ok or self.muted:
            return
        snd = self.sfx.get(name)
        if snd is None:
            return
        try:
            ch = snd.play()
            if ch is not None:
                ch.set_volume(max(0.0, min(1.0, volume * self.master * self.sfx_vol)))
        except Exception:
            pass

    def clash(self, power: float) -> None:
        self.play(f"clash{_rng.randint(0, 2)}", 0.35 + 0.65 * min(1.0, power))

    def hum(self, player: int, energy01: float, active: bool) -> None:
        """Keep a looping hum per top; pitch level follows energy, volume follows activity."""
        if not self.ok:
            return
        ch = self._hum_ch.get(player)
        if ch is None:
            return
        try:
            if not active or self.muted:
                if ch.get_busy():
                    ch.fadeout(300)
                self._hum_level[player] = -1
                return
            level = 0 if energy01 > 0.75 else 1 if energy01 > 0.5 else 2 if energy01 > 0.25 else 3
            if level >= len(self.hums):
                return  # still being synthesized
            if level != self._hum_level[player] or not ch.get_busy():
                ch.play(self.hums[level], loops=-1, fade_ms=120)
                self._hum_level[player] = level
            ch.set_volume(0.18 * self.master * (0.5 + 0.5 * energy01))
        except Exception:
            pass

    def stop_hums(self) -> None:
        for p in (1, 2):
            self.hum(p, 0.0, False)


AUDIO = Audio()
