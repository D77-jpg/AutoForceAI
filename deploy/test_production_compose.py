"""H-13 offline safety checks: no production service may expose private ports."""
import pathlib
import re
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent


class ProductionComposeChecks(unittest.TestCase):
    def test_compose_renders_and_only_ingress_publishes(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed; docker compose config still required")
        result = subprocess.run(
            ["docker", "compose", "--env-file", str(ROOT / ".env.production.example"),
             "-f", str(ROOT / "compose.yaml"), "config"],
            capture_output=True, text=True, check=True,
        )
        document = yaml.safe_load(result.stdout)
        services = document["services"]
        self.assertEqual(set(services), {"postgres", "mongo", "backend", "worker", "web", "genesis-server", "genesis-web", "nginx"})
        for name, service in services.items():
            if name == "nginx":
                self.assertEqual({item["published"] for item in service["ports"]}, {"80", "443"})
            else:
                self.assertNotIn("ports", service, name)
            self.assertEqual(service["restart"], "unless-stopped", name)
            self.assertIn("logging", service, name)
            self.assertIn("mem_limit", service, name)
            self.assertIn("cpus", service, name)
        for name in ("postgres", "mongo", "backend", "web", "genesis-server", "genesis-web"):
            self.assertIn("healthcheck", services[name], name)
        self.assertTrue(document["networks"]["data"]["internal"])
        self.assertIn("pgvector/pgvector", services["postgres"]["image"])

    def test_tls_domains_and_no_dev_websocket(self):
        config = (ROOT / "nginx/conf.d/production.conf.template").read_text(encoding="utf-8")
        self.assertIn("server_name ${APP_DOMAIN}", config)
        self.assertIn("server_name ${CRM_DOMAIN}", config)
        self.assertIn("/.well-known/acme-challenge/", config)
        self.assertIn("X-Content-Type-Options", config)
        self.assertIn("client_max_body_size", config)
        self.assertIn("_next/webpack-hmr", config)
        self.assertNotRegex(config, r"proxy_set_header\s+Upgrade\s+\$http_upgrade")
        template = (ROOT / ".env.production.example").read_text(encoding="utf-8")
        for key in ("JWT_SECRET", "GENESIS_JWT_SECRET", "POSTGRES_PASSWORD", "MONGO_ROOT_PASSWORD"):
            self.assertRegex(template, rf"(?m)^{key}=REPLACE_")
        self.assertNotIn("PRIVATE KEY-----", template)


if __name__ == "__main__":
    unittest.main()
