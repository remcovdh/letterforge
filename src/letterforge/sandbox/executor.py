from __future__ import annotations

import io
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

from letterforge.config import ConfigurationError, SandboxConfig


class SandboxTimeoutError(RuntimeError):
    pass


@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    output_files: dict[str, bytes] = field(default_factory=dict)
    timed_out: bool = False


class DockerSandbox:
    def __init__(self, config: SandboxConfig) -> None:
        try:
            import docker
        except ImportError:
            raise ConfigurationError(
                "docker package not installed. Run: pip install letterforge"
            )
        try:
            self._docker = docker.from_env()
        except Exception as exc:
            raise ConfigurationError(
                f"Docker daemon not reachable. Is Docker running? ({exc})"
            ) from exc
        self._config = config
        self._sandbox_dir = Path(__file__).parent.parent.parent.parent / "docker" / "sandbox"

    def ensure_image(self) -> None:
        import docker

        try:
            self._docker.images.get(self._config.docker_image)
        except docker.errors.ImageNotFound:
            if not self._config.auto_build:
                raise RuntimeError(
                    f"Sandbox image '{self._config.docker_image}' not found. "
                    "Run: letterforge build-sandbox"
                )
            self._docker.images.build(
                path=str(self._sandbox_dir),
                tag=self._config.docker_image,
                rm=True,
            )

    def run(
        self,
        code: str,
        sheet1_bytes: bytes,
        sheet2_bytes: bytes,
    ) -> SandboxResult:
        self.ensure_image()

        container = self._docker.containers.create(
            image=self._config.docker_image,
            command=["python", "/workspace/generated_code.py"],
            environment={
                "SHEET1_PATH": "/workspace/inputs/sheet1.png",
                "SHEET2_PATH": "/workspace/inputs/sheet2.png",
                "OUTPUT_DIR": "/workspace/outputs",
            },
            mem_limit=self._config.mem_limit,
            cpu_quota=self._config.cpu_quota,
            network_disabled=self._config.network_disabled,
            user="sandboxuser",
        )

        try:
            self._put_files(container, "/workspace", {"generated_code.py": code.encode()})
            self._put_files(
                container,
                "/workspace/inputs",
                {"sheet1.png": sheet1_bytes, "sheet2.png": sheet2_bytes},
            )
            container.exec_run("mkdir -p /workspace/outputs")
            container.start()

            timed_out = False
            exit_code = -1
            try:
                result = container.wait(timeout=self._config.timeout_seconds)
                exit_code = result["StatusCode"]
            except Exception:
                container.stop(timeout=5)
                timed_out = True

            stdout = container.logs(stdout=True, stderr=False).decode(errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode(errors="replace")

            output_files: dict[str, bytes] = {}
            if exit_code == 0:
                output_files = self._get_files(container, "/workspace/outputs")

            return SandboxResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                output_files=output_files,
                timed_out=timed_out,
            )
        finally:
            container.remove(force=True)

    def _put_files(self, container, dest_path: str, files: dict[str, bytes]) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            for name, data in files.items():
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        buf.seek(0)
        container.put_archive(dest_path, buf.getvalue())

    def _get_files(self, container, src_path: str) -> dict[str, bytes]:
        try:
            bits, _ = container.get_archive(src_path)
        except Exception:
            return {}
        buf = io.BytesIO()
        for chunk in bits:
            buf.write(chunk)
        buf.seek(0)
        result: dict[str, bytes] = {}
        with tarfile.open(fileobj=buf, mode="r") as tar:
            for member in tar.getmembers():
                if member.isfile() and member.name.endswith(".png"):
                    f = tar.extractfile(member)
                    if f:
                        result[Path(member.name).name] = f.read()
        return result
