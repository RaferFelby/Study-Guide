import unittest

from app.server import build_payload


class BuildPayloadTests(unittest.TestCase):
    def test_health_payload_is_ok(self) -> None:
        self.assertEqual(
            build_payload("/health"),
            {"status": "ok", "service": "linux-git-docker-demo"},
        )

    def test_unknown_path_is_not_found(self) -> None:
        self.assertEqual(
            build_payload("/missing"),
            {"status": "not_found", "path": "/missing"},
        )


if __name__ == "__main__":
    unittest.main()
