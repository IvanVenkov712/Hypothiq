"""HTTP smoke tests against a running Compose deployment; no Yahoo downloads."""

import json
import os
import re
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = os.environ.get("HYPOTHIQ_URL", "http://localhost:8080").rstrip("/")


class DeploymentTests(unittest.TestCase):
    def test_frontend_routes_serve_the_same_app(self):
        with urlopen(f"{BASE_URL}/", timeout=10) as response:
            index = response.read()
            self.assertIn("text/html", response.headers["Content-Type"])
        self.assertIn(b'<div id="root">', index)
        for route in ("/strategies", "/backtesting?strategy=BuyAndHold"):
            with self.subTest(route=route):
                with urlopen(f"{BASE_URL}{route}", timeout=10) as response:
                    self.assertEqual(response.read(), index)
        assets = re.findall(rb'(?:src|href)="(/assets/[^"]+)"', index)
        self.assertTrue(assets, "The HTML must reference built assets")
        for asset in assets:
            with urlopen(BASE_URL + asset.decode(), timeout=10) as response:
                self.assertNotIn("text/html", response.headers["Content-Type"])
                self.assertTrue(response.read())

    def test_api_health_and_catalogue(self):
        with urlopen(f"{BASE_URL}/api/health", timeout=10) as response:
            self.assertEqual(json.load(response), {"status": "ok"})
        with urlopen(f"{BASE_URL}/api/strategies", timeout=10) as response:
            self.assertIn("application/json", response.headers["Content-Type"])
            self.assertIn("BuyAndHold", [item["class_name"] for item in json.load(response)])

    def test_docs_use_the_public_api_prefix(self):
        with urlopen(f"{BASE_URL}/api/docs", timeout=10) as response:
            self.assertIn(b"/api/openapi.json", response.read())
        with urlopen(f"{BASE_URL}/api/openapi.json", timeout=10) as response:
            schema = json.load(response)
        self.assertIn({"url": "/api"}, schema["servers"])
        self.assertIn("/backtests/run-backtest", schema["paths"])

    def test_invalid_backtest_preserves_json_validation_error(self):
        request = Request(
            f"{BASE_URL}/api/backtests/run-backtest",
            data=b"{}",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=10)
        with caught.exception as response:
            self.assertEqual(response.code, 422)
            self.assertTrue(json.load(response)["detail"])

    def test_missing_api_and_assets_do_not_return_the_spa(self):
        for path in ("/api/not-an-endpoint", "/assets/not-a-file.js"):
            with self.subTest(path=path):
                with self.assertRaises(HTTPError) as caught:
                    urlopen(BASE_URL + path, timeout=10)
                with caught.exception as response:
                    self.assertEqual(response.code, 404)
                    if path.startswith("/api/"):
                        self.assertIn("application/json", response.headers["Content-Type"])
                        self.assertEqual(json.load(response)["detail"], "Not Found")

    def test_backtest_body_reaches_the_backend(self):
        request = Request(
            f"{BASE_URL}/api/backtests/run-backtest",
            data=json.dumps({
                "strategy": {"name": "DeploymentSmokeTestUnknownStrategy"},
                "data_request": {
                    "ticker": "AAPL",
                    "start": "2024-01-01T00:00:00",
                    "end": "2025-01-01T00:00:00",
                },
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        # Strategy resolution fails before the service contacts Yahoo Finance.
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=10)
        with caught.exception as response:
            self.assertEqual(response.code, 400)
            self.assertIn("DeploymentSmokeTestUnknownStrategy", json.load(response)["detail"])

    def test_api_root_redirect_preserves_the_public_port(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(f"{BASE_URL}/api", timeout=10)
        with caught.exception as response:
            self.assertEqual(response.code, 404)
            self.assertEqual(response.url, f"{BASE_URL}/api/")
            self.assertEqual(json.load(response)["detail"], "Not Found")

    def test_backend_redirect_keeps_public_host_and_prefix(self):
        # FastAPI redirects a trailing slash to its canonical route.
        with urlopen(f"{BASE_URL}/api/strategies/?check=1", timeout=10) as response:
            self.assertEqual(response.url, f"{BASE_URL}/api/strategies?check=1")
            self.assertIsInstance(json.load(response), list)


if __name__ == "__main__":
    unittest.main()
