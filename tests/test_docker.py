"""Tests for Docker infrastructure — static file validation (no runtime needed)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# docker-compose.yml tests
# ---------------------------------------------------------------------------


class TestDockerCompose:
    @pytest.fixture(autouse=True)
    def _load_compose(self):
        compose_path = PROJECT_ROOT / "docker-compose.yml"
        assert compose_path.exists(), "docker-compose.yml not found"
        with open(compose_path) as f:
            self.compose = yaml.safe_load(f)

    def test_valid_yaml(self):
        assert isinstance(self.compose, dict)

    def test_defines_all_services(self):
        services = set(self.compose.get("services", {}).keys())
        expected = {
            "api",
            "postgres",
            "redpanda",
            "redpanda-console",
            "airflow-webserver",
            "airflow-scheduler",
            "airflow-init",
            "stream-producer",
        }
        assert expected == services

    def test_api_port(self):
        api = self.compose["services"]["api"]
        assert "8000:8000" in api["ports"]

    def test_postgres_port(self):
        pg = self.compose["services"]["postgres"]
        assert "5432:5432" in pg["ports"]

    def test_redpanda_port(self):
        rp = self.compose["services"]["redpanda"]
        assert "9092:9092" in rp["ports"]

    def test_airflow_webserver_port(self):
        ws = self.compose["services"]["airflow-webserver"]
        assert "8080:8080" in ws["ports"]

    def test_api_depends_on_postgres_and_redpanda(self):
        api = self.compose["services"]["api"]
        deps = api.get("depends_on", {})
        assert "postgres" in deps
        assert "redpanda" in deps

    def test_airflow_depends_on_postgres(self):
        ws = self.compose["services"]["airflow-webserver"]
        deps = ws.get("depends_on", {})
        assert "postgres" in deps

    def test_stream_producer_depends_on_redpanda(self):
        sp = self.compose["services"]["stream-producer"]
        deps = sp.get("depends_on", {})
        assert "redpanda" in deps

    def test_shared_network(self):
        networks = self.compose.get("networks", {})
        assert "fulfillment-net" in networks

    def test_postgres_volume(self):
        volumes = self.compose.get("volumes", {})
        assert "postgres_data" in volumes


# ---------------------------------------------------------------------------
# Dockerfile tests
# ---------------------------------------------------------------------------


class TestDockerfiles:
    def test_dockerfile_exists(self):
        assert (PROJECT_ROOT / "Dockerfile").exists()

    def test_dockerfile_base_image(self):
        content = (PROJECT_ROOT / "Dockerfile").read_text()
        assert "python:3.11-slim" in content

    def test_dockerfile_exposes_8000(self):
        content = (PROJECT_ROOT / "Dockerfile").read_text()
        assert "EXPOSE 8000" in content

    def test_dockerfile_producer_exists(self):
        assert (PROJECT_ROOT / "Dockerfile.producer").exists()

    def test_dockerfile_producer_base_image(self):
        content = (PROJECT_ROOT / "Dockerfile.producer").read_text()
        assert "python:3.11-slim" in content


# ---------------------------------------------------------------------------
# .env.example tests
# ---------------------------------------------------------------------------


class TestEnvExample:
    def test_env_example_exists(self):
        assert (PROJECT_ROOT / ".env.example").exists()

    def test_env_example_has_required_vars(self):
        content = (PROJECT_ROOT / ".env.example").read_text()
        required = [
            "DATABASE_URL",
            "KAFKA_BROKER",
            "OPENAI_API_KEY",
            "MODEL_PATH",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
            "AIRFLOW_UID",
            "EVENTS_PER_SECOND",
        ]
        for var in required:
            assert var in content, f"Missing env var: {var}"
