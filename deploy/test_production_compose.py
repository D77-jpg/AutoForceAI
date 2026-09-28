"""H-13 offline safety checks: no production service may expose private ports."""
import pathlib
import re
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent


class ProductionComposeChecks(unittest.TestCase):
    def test_compose_renders_and_only_ingress_publishes(self):
        import yaml  # Fail closed if the release-gate dependency is missing.
        result = subprocess.run(
            ["docker", "compose", "--env-file", str(ROOT / "production.env.example"),
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
        self.assertIn("server", services["genesis-server"]["networks"]["app"]["aliases"])
        self.assertIn("rpa_browser_data", document["volumes"])
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
        template = (ROOT / "production.env.example").read_text(encoding="utf-8")
        for key in ("JWT_SECRET", "GENESIS_JWT_SECRET", "POSTGRES_PASSWORD", "MONGO_ROOT_PASSWORD"):
            self.assertRegex(template, rf"(?m)^{key}=REPLACE_")
        self.assertNotIn("PRIVATE KEY-----", template)
        worker = (ROOT / "worker.Dockerfile").read_text(encoding="utf-8")
        self.assertIn("PLAYWRIGHT_BROWSERS_PATH=0", worker)
        self.assertIn("playwright install --with-deps chromium", worker)
        # Production builds use same-origin browser API, never visitor localhost.
        # Every browser call must reach the backend through the console's own origin
        # (Next.js rewrites, then the nginx ingress), so no console source may point
        # the API port at a loopback address.
        console = ROOT.parent / "apps/web-console"
        allowed_api_loopback = {
            # Default text of the rpa-worker service-address form. It is a worker
            # endpoint, not a browser API base, and the form has no backend yet.
            "app/platform/skills/page.tsx",
        }
        offenders = []
        for source in sorted(console.rglob("*")):
            if source.suffix not in (".ts", ".tsx") or source.is_symlink():
                continue
            if any(part in ("node_modules", ".next") for part in source.parts):
                continue
            if re.search(r"(?:localhost|127\.0\.0\.1):8010\b", source.read_text(encoding="utf-8")):
                relative = source.relative_to(console).as_posix()
                if relative not in allowed_api_loopback:
                    offenders.append(relative)
        self.assertEqual(offenders, [], f"visitor-localhost API base in {offenders}")
        web_image = (ROOT / "web.Dockerfile").read_text(encoding="utf-8")
        self.assertIn('CMD ["node", "server.js"]', web_image)
        self.assertIn('/workspace/apps/web-console/.next/static ./.next/static', web_image)
        self.assertIn('/workspace/apps/web-console/public ./public', web_image)

    def test_legacy_root_routers_reach_backend_same_origin(self):
        """The digital-employee and content modules call root-mounted routers.

        The backend mounts /agents and /content outside /api/v1, so both the
        ingress and the Next.js proxy must forward them; otherwise the browser
        gets a 404 from the web container instead of the API.
        """
        config = (ROOT / "nginx/conf.d/production.conf.template").read_text(encoding="utf-8")
        backend_location = next(line for line in config.splitlines() if "proxy_pass http://backend:8010" in line)
        self.assertIn("backend:8010", backend_location)
        ingress = next(line for line in config.splitlines()
                       if line.strip().startswith("location ~ ^/(?:") and "api/" in line)
        for prefix in ("api/", "auth/", "agents/", "content/"):
            self.assertIn(prefix, ingress, prefix)
        next_config = (ROOT.parent / "apps/web-console/next.config.js").read_text(encoding="utf-8")
        for source in ("/api/:path*", "/auth/:path*", "/agents/:path*", "/content/:path*", "/uploads/:path*"):
            self.assertIn(f"source: '{source}'", next_config, source)


if __name__ == "__main__":
    unittest.main()
