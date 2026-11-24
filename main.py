"""BABY BLADE 2.0 — entry point.

    python main.py                  play
    python main.py --smoke 120      run 120 frames headless and exit (CI check)
    python main.py --tournament 20  run a 20-match AI benchmark in the terminal
"""

import argparse
import asyncio
import os
import sys

import pygame  # noqa: F401  (imported here so the browser build bundles pygame-ce)


def parse(argv=None):
    p = argparse.ArgumentParser(description="BABY BLADE 2.0")
    p.add_argument("--smoke", type=int, default=None, metavar="FRAMES", help="headless run for N frames")
    p.add_argument("--shot", type=str, default=None, help="save the last frame as PNG")
    p.add_argument("--tournament", type=int, default=None, metavar="N", help="headless AI benchmark")
    p.add_argument("--a", default="Ironclad")
    p.add_argument("--b", default="Cyclone")
    p.add_argument("--diff", default="Medium")
    p.add_argument("--out", default=None, help="export tournament JSON/CSV to this folder")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse(argv)
    if args.tournament:
        from babyblade.tournament import Tournament, TournamentConfig
        cfg = TournamentConfig(args.a, args.b, args.diff, args.diff, matches=args.tournament)
        s = Tournament(cfg).run()
        print(f"{s.played} matches  A={cfg.agent_a} B={cfg.agent_b} ({args.diff})")
        print(f"A wins {s.wins('A')} ({s.win_rate('A') * 100:.0f}%)  B wins {s.wins('B')} ({s.win_rate('B') * 100:.0f}%)  draws {s.draws}")
        print(f"avg duration {s.avg_seconds:.1f}s / {s.avg_rounds:.1f} rounds  decision ms A={s.avg_think_ms('A'):.1f} B={s.avg_think_ms('B'):.1f}")
        print("finishes", s.finishes())
        if args.out:
            print("exported to", s.export(args.out))
        return 0
    if args.smoke is not None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    from babyblade.game.app import App
    return App(max_frames=args.smoke, shot=args.shot).run()


async def main_web() -> None:
    from babyblade.game.app import App
    await App().run_async()


if __name__ == "__main__":
    if sys.platform == "emscripten":
        asyncio.run(main_web())
    else:
        sys.exit(main())
