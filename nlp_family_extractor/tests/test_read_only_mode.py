import asyncio
import unittest
from unittest import mock

import api

BOOTSTRAPS = [
    "bootstrap_gemini_usage",
    "bootstrap_auth",
    "bootstrap_documents",
    "bootstrap_pipeline",
    "bootstrap_vgp",
    "bootstrap_workspace",
    "bootstrap_hannom",
    "bootstrap_settings",
]


def _run_lifespan(env: dict[str, str]) -> dict[str, mock.Mock]:
    patches = {name: mock.patch.object(api, name) for name in BOOTSTRAPS}
    with mock.patch.dict("os.environ", env, clear=False), \
            mock.patch.object(api, "init_database"), \
            mock.patch.object(api, "load_local_engines"), \
            mock.patch.object(api, "database_enabled", return_value=True):
        started = {name: p.start() for name, p in patches.items()}
        try:
            async def go() -> None:
                async with api._lifespan(api.app):
                    pass

            asyncio.run(go())
        finally:
            for p in patches.values():
                p.stop()
    return started


class ReadOnlyModeTest(unittest.TestCase):
    def test_flag_parsing(self) -> None:
        for value, expected in [("1", True), ("true", True), ("YES", True), ("0", False), ("", False), ("off", False)]:
            with mock.patch.dict("os.environ", {"READ_ONLY_MODE": value}):
                self.assertEqual(api.read_only_mode(), expected, value)

    def test_read_only_skips_every_bootstrap(self) -> None:
        started = _run_lifespan({"READ_ONLY_MODE": "1"})
        for name, fn in started.items():
            fn.assert_not_called()

    def test_default_still_runs_every_bootstrap(self) -> None:
        started = _run_lifespan({"READ_ONLY_MODE": "0"})
        for name, fn in started.items():
            fn.assert_called_once()


if __name__ == "__main__":
    unittest.main()
