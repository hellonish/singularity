"""Stateful, policy-controlled Modal Sandbox workspaces."""
from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Awaitable, Callable
from uuid import uuid4

import modal

from engine.chat.modal_tools import modal_environment_name


MAX_COMMAND_OUTPUT = 50_000
MAX_WRITE_BYTES = 500_000
MAX_READ_FILE_BYTES = 10_000_000


class SandboxProfile(StrEnum):
    REPOSITORY = "repository"
    REPOSITORY_BUILD = "repository_build"
    CODE = "code"
    DATA = "data"
    SERVICE = "service"
    GPU = "gpu"


@dataclass(frozen=True)
class SandboxWorkspaceDescriptor:
    workspace_id: str
    profile: SandboxProfile
    purpose: str
    status: str
    repository_url: str | None = None
    ref: str | None = None
    commit_sha: str | None = None
    created_at: float = field(default_factory=time.time)

    def public_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxCommand:
    workspace_id: str
    argv: tuple[str, ...]
    workdir: str = "/workspace"
    timeout_seconds: int = 60


@dataclass(frozen=True)
class SandboxCommandResult:
    exit_code: int
    stdout: str
    stderr: str
    elapsed_seconds: float
    truncated: bool
    changed_files: tuple[str, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class _Workspace:
    descriptor: SandboxWorkspaceDescriptor
    modal_object_id: str
    sandbox: Any
    run_id: str
    command_limit: int = 30
    commands_used: int = 0
    pending_changed_files: set[str] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


@dataclass(frozen=True)
class _ProfilePolicy:
    cpu: tuple[float, float]
    memory: tuple[int, int]
    block_network: bool = False
    outbound_domains: tuple[str, ...] = ()
    gpu: str | None = None


_POLICIES: dict[SandboxProfile, _ProfilePolicy] = {
    SandboxProfile.REPOSITORY: _ProfilePolicy(
        cpu=(1.0, 4.0), memory=(2048, 8192),
        outbound_domains=(
            "github.com", "*.github.com", "githubusercontent.com", "*.githubusercontent.com"
        ),
    ),
    SandboxProfile.REPOSITORY_BUILD: _ProfilePolicy(
        cpu=(1.0, 4.0), memory=(2048, 8192),
        outbound_domains=(
            "github.com", "*.github.com", "githubusercontent.com", "*.githubusercontent.com", "pypi.org",
            "*.pythonhosted.org", "registry.npmjs.org",
        ),
    ),
    SandboxProfile.CODE: _ProfilePolicy(cpu=(1.0, 4.0), memory=(2048, 8192), block_network=True),
    SandboxProfile.DATA: _ProfilePolicy(cpu=(1.0, 4.0), memory=(2048, 8192), block_network=True),
    SandboxProfile.SERVICE: _ProfilePolicy(
        cpu=(1.0, 4.0), memory=(2048, 8192),
        outbound_domains=("pypi.org", "*.pythonhosted.org", "registry.npmjs.org"),
    ),
    SandboxProfile.GPU: _ProfilePolicy(
        cpu=(2.0, 8.0), memory=(4096, 16384), block_network=True,
        gpu=os.getenv("SINGULARITY_MODAL_SANDBOX_GPU", "T4"),
    ),
}


def _inline_image(profile: SandboxProfile) -> modal.Image:
    base = modal.Image.debian_slim(python_version="3.12").apt_install(
        "git", "ripgrep", "curl", "build-essential"
    )
    if profile in {SandboxProfile.REPOSITORY_BUILD, SandboxProfile.CODE, SandboxProfile.SERVICE}:
        return base.apt_install("nodejs", "npm").uv_pip_install("pytest", "ruff")
    if profile == SandboxProfile.REPOSITORY:
        return base.uv_pip_install("pytest", "ruff")
    if profile == SandboxProfile.DATA:
        return base.uv_pip_install("pandas", "numpy", "matplotlib", "scipy")
    return base


def _image(profile: SandboxProfile) -> modal.Image:
    key = f"SINGULARITY_MODAL_SANDBOX_IMAGE_{profile.value.upper()}"
    name = os.getenv(key) or os.getenv("SINGULARITY_MODAL_SANDBOX_IMAGE")
    if name:
        return modal.Image.from_name(name, environment_name=modal_environment_name())
    if profile == SandboxProfile.GPU:
        raise ValueError("GPU Sandbox requires a pre-published named Image")
    return _inline_image(profile)


def _workspace_path(raw: str, *, allow_root: bool = True) -> str:
    path = PurePosixPath(raw)
    if not path.is_absolute():
        path = PurePosixPath("/workspace") / path
    if path != PurePosixPath("/workspace") and PurePosixPath("/workspace") not in path.parents:
        raise ValueError("Sandbox paths must stay under /workspace")
    if ".." in path.parts or (not allow_root and path == PurePosixPath("/workspace")):
        raise ValueError("unsafe Sandbox path")
    return str(path)


def _validate_argv(argv: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    if not argv or len(argv) > 64:
        raise ValueError("Sandbox command must contain between 1 and 64 arguments")
    values = tuple(str(item) for item in argv)
    if any(not item or len(item) > 2_000 or "\x00" in item for item in values):
        raise ValueError("Sandbox command contains an invalid argument")
    return values


class SandboxWorkspaceManager:
    """Own stateful workspaces for one chat task or durable research run."""

    def __init__(
        self,
        *,
        sandbox_factory: Callable[..., Any] | None = None,
        sandbox_lookup: Callable[[str], Awaitable[Any]] | None = None,
        app_resolver: Callable[[], Awaitable[Any]] | None = None,
        state_reporter: Callable[[list[dict[str, Any]]], Awaitable[None]] | None = None,
    ) -> None:
        self._sandbox_factory = sandbox_factory or modal.Sandbox.create.aio
        self._sandbox_lookup = sandbox_lookup or self._lookup_sandbox
        self._app_resolver = app_resolver or self._lookup_app
        self._state_reporter = state_reporter
        self._app: Any | None = None
        self._app_lock = asyncio.Lock()
        self._create_lock = asyncio.Lock()
        self._workspaces: dict[str, _Workspace] = {}
        self._reuse: dict[tuple[str, SandboxProfile, str], str] = {}

    async def _lookup_app(self) -> Any:
        return await modal.App.lookup.aio(
            os.getenv("SINGULARITY_MODAL_SANDBOX_APP", "singularity-agent-sandboxes"),
            environment_name=modal_environment_name(),
            create_if_missing=True,
        )

    async def _lookup_sandbox(self, object_id: str) -> Any:
        return await modal.Sandbox.from_id.aio(object_id)

    async def _get_app(self) -> Any:
        if self._app is not None:
            return self._app
        async with self._app_lock:
            if self._app is None:
                self._app = await self._app_resolver()
        return self._app

    async def create(
        self,
        *,
        run_id: str,
        purpose: str,
        profile: SandboxProfile,
        repository_url: str | None = None,
        ref: str | None = None,
        command_limit: int = 30,
    ) -> SandboxWorkspaceDescriptor:
        async with self._create_lock:
            return await self._create_locked(
                run_id=run_id,
                purpose=purpose,
                profile=profile,
                repository_url=repository_url,
                ref=ref,
                command_limit=command_limit,
            )

    async def _create_locked(
        self,
        *,
        run_id: str,
        purpose: str,
        profile: SandboxProfile,
        repository_url: str | None = None,
        ref: str | None = None,
        command_limit: int = 30,
    ) -> SandboxWorkspaceDescriptor:
        reuse_key = (run_id, profile, repository_url or purpose)
        existing_id = self._reuse.get(reuse_key)
        if existing_id and existing_id in self._workspaces:
            return self._workspaces[existing_id].descriptor

        policy = _POLICIES[profile]
        kwargs: dict[str, Any] = {
            "app": await self._get_app(),
            "image": _image(profile),
            "timeout": int(os.getenv("SINGULARITY_MODAL_SANDBOX_TIMEOUT", "1800")),
            "idle_timeout": int(os.getenv("SINGULARITY_MODAL_SANDBOX_IDLE_TIMEOUT", "300")),
            "cpu": policy.cpu,
            "memory": policy.memory,
            "block_network": policy.block_network,
            "tags": {"run_id": run_id[:64], "purpose": purpose[:64], "profile": profile.value},
        }
        if policy.outbound_domains:
            kwargs["outbound_domain_allowlist"] = list(policy.outbound_domains)
        if policy.gpu:
            kwargs["gpu"] = policy.gpu

        sandbox = await self._sandbox_factory(**kwargs)
        workspace_id = f"ws_{uuid4().hex}"
        object_id = str(getattr(sandbox, "object_id", workspace_id))
        descriptor = SandboxWorkspaceDescriptor(
            workspace_id=workspace_id,
            profile=profile,
            purpose=purpose,
            status="ready",
            repository_url=repository_url,
            ref=ref,
        )
        workspace = _Workspace(
            descriptor=descriptor,
            modal_object_id=object_id,
            sandbox=sandbox,
            run_id=run_id,
            command_limit=max(1, min(int(command_limit), 100)),
        )
        self._workspaces[workspace_id] = workspace
        self._reuse[reuse_key] = workspace_id
        try:
            await sandbox.filesystem.make_directory.aio("/workspace", create_parents=True)
            if repository_url:
                argv = ["git", "clone", "--depth", "1"]
                if ref:
                    argv.extend(["--branch", ref])
                argv.extend([repository_url, "/workspace/repository"])
                cloned = await self.exec(SandboxCommand(workspace_id, tuple(argv), "/workspace", 120))
                if cloned.exit_code != 0:
                    raise RuntimeError(f"repository clone failed: {cloned.stderr or cloned.stdout}")
                commit = await self.exec(SandboxCommand(
                    workspace_id, ("git", "rev-parse", "HEAD"), "/workspace/repository", 30
                ))
                if commit.exit_code == 0:
                    descriptor = SandboxWorkspaceDescriptor(
                        **{**descriptor.public_dict(), "commit_sha": commit.stdout.strip()[:40]}
                    )
                    workspace.descriptor = descriptor
            await self._report_state()
            return descriptor
        except BaseException:
            await self.close(workspace_id)
            raise

    async def reconnect(
        self,
        *,
        descriptor: SandboxWorkspaceDescriptor,
        modal_object_id: str,
        run_id: str,
        command_limit: int = 30,
        commands_used: int = 0,
        pending_changed_files: list[str] | tuple[str, ...] = (),
    ) -> SandboxWorkspaceDescriptor:
        sandbox = await self._sandbox_lookup(modal_object_id)
        return_code = await sandbox.poll.aio()
        if return_code is not None:
            raise RuntimeError("persisted Modal Sandbox is no longer running")
        self._workspaces[descriptor.workspace_id] = _Workspace(
            descriptor,
            modal_object_id,
            sandbox,
            run_id,
            max(1, min(command_limit, 100)),
            max(0, int(commands_used)),
            {
                str(path)
                for path in pending_changed_files
                if isinstance(path, str) and path and not path.startswith("/") and ".." not in PurePosixPath(path).parts
            },
        )
        self._reuse[(run_id, descriptor.profile, descriptor.repository_url or descriptor.purpose)] = (
            descriptor.workspace_id
        )
        try:
            if descriptor.repository_url and not descriptor.commit_sha:
                commit = await self.exec(SandboxCommand(
                    descriptor.workspace_id,
                    ("git", "rev-parse", "HEAD"),
                    "/workspace/repository",
                    30,
                ))
                if commit.exit_code == 0:
                    updated = SandboxWorkspaceDescriptor(
                        **{**descriptor.public_dict(), "commit_sha": commit.stdout.strip()[:40]}
                    )
                    self._workspaces[descriptor.workspace_id].descriptor = updated
                    descriptor = updated
            await self._report_state()
            return descriptor
        except BaseException:
            self._forget(descriptor.workspace_id)
            raise

    async def restore_states(self, states: list[dict[str, Any]]) -> list[SandboxWorkspaceDescriptor]:
        """Reconnect persisted workspaces or replay only their validated bootstrap."""
        restored: list[SandboxWorkspaceDescriptor] = []
        for state in states[:8]:
            try:
                raw_descriptor = dict(state.get("descriptor") or {})
                raw_descriptor["profile"] = SandboxProfile(raw_descriptor["profile"])
                descriptor = SandboxWorkspaceDescriptor(**raw_descriptor)
                run_id = str(state.get("run_id") or "")
                object_id = str(state.get("modal_object_id") or "")
            except (KeyError, TypeError, ValueError):
                continue
            if not run_id or not object_id:
                continue
            try:
                restored.append(await self.reconnect(
                    descriptor=descriptor,
                    modal_object_id=object_id,
                    run_id=run_id,
                    command_limit=int(state.get("command_limit") or 30),
                    commands_used=int(state.get("commands_used") or 0),
                    pending_changed_files=list(state.get("pending_changed_files") or []),
                ))
            except Exception:
                self._forget(descriptor.workspace_id)
                restored.append(await self.create(
                    run_id=run_id,
                    purpose=descriptor.purpose,
                    profile=descriptor.profile,
                    repository_url=descriptor.repository_url,
                    ref=descriptor.ref,
                    command_limit=int(state.get("command_limit") or 30),
                ))
        return restored

    async def exec(self, command: SandboxCommand) -> SandboxCommandResult:
        workspace = self._require(command.workspace_id)
        argv = _validate_argv(command.argv)
        workdir = _workspace_path(command.workdir)
        timeout = max(1, min(int(command.timeout_seconds), 420))
        async with workspace.lock:
            if workspace.commands_used >= workspace.command_limit:
                raise ValueError("Sandbox command budget exhausted for this workspace")
            workspace.commands_used += 1
            changed_files = tuple(sorted(workspace.pending_changed_files))
            workspace.pending_changed_files.clear()
            started = time.monotonic()
            try:
                process = await workspace.sandbox.exec.aio(*argv, workdir=workdir, timeout=timeout)
                stdout, stderr = await asyncio.gather(process.stdout.read.aio(), process.stderr.read.aio())
                return_code = int(await process.wait.aio())
                elapsed = time.monotonic() - started
            except BaseException:
                await self._report_state()
                raise
        raw_stdout, raw_stderr = str(stdout), str(stderr)
        truncated = len(raw_stdout) + len(raw_stderr) > MAX_COMMAND_OUTPUT
        safe_stdout = raw_stdout[:MAX_COMMAND_OUTPUT]
        remaining = max(0, MAX_COMMAND_OUTPUT - len(safe_stdout))
        safe_stderr = raw_stderr[:remaining]
        result = SandboxCommandResult(
            exit_code=return_code,
            stdout=safe_stdout,
            stderr=safe_stderr,
            elapsed_seconds=elapsed,
            truncated=truncated,
            changed_files=changed_files,
            provenance={
                "workspace_id": workspace.descriptor.workspace_id,
                "profile": workspace.descriptor.profile.value,
                "purpose": workspace.descriptor.purpose,
                "repository_url": workspace.descriptor.repository_url,
                "commit_sha": workspace.descriptor.commit_sha,
            },
        )
        await self._report_state()
        return result

    async def list_files(self, workspace_id: str, path: str) -> list[dict[str, Any]]:
        workspace = self._require(workspace_id)
        entries = await workspace.sandbox.filesystem.list_files.aio(_workspace_path(path))
        return [
            {"name": str(item.name), "type": str(item.type.value), "size": int(item.size)}
            for item in entries[:1_000]
        ]

    async def read_text(self, workspace_id: str, path: str, *, offset: int = 0, limit: int = 50_000) -> str:
        workspace = self._require(workspace_id)
        safe_path = _workspace_path(path, allow_root=False)
        info = await workspace.sandbox.filesystem.stat.aio(safe_path)
        if str(info.type.value) == "symlink":
            raise ValueError("Sandbox reads do not follow symbolic links")
        if int(info.size) > MAX_READ_FILE_BYTES:
            raise ValueError("Sandbox file exceeds the 10 MB read limit")
        content = await workspace.sandbox.filesystem.read_text.aio(safe_path)
        start = max(0, int(offset))
        return str(content)[start : start + max(1, min(int(limit), 100_000))]

    async def write_files(self, workspace_id: str, files: dict[str, str]) -> list[str]:
        workspace = self._require(workspace_id)
        if not files or len(files) > 20:
            raise ValueError("Sandbox writes must contain between 1 and 20 files")
        if sum(len(value.encode("utf-8")) for value in files.values()) > MAX_WRITE_BYTES:
            raise ValueError("Sandbox writes exceed the 500 KB request limit")
        written: list[str] = []
        async with workspace.lock:
            for raw_path, content in files.items():
                path = _workspace_path(raw_path, allow_root=False)
                await workspace.sandbox.filesystem.make_directory.aio(
                    str(PurePosixPath(path).parent), create_parents=True
                )
                await workspace.sandbox.filesystem.write_text.aio(content, path)
                relative = path.removeprefix("/workspace/") or path
                written.append(relative)
                workspace.pending_changed_files.add(relative)
        await self._report_state()
        return written

    def status(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._require(workspace_id)
        return {
            **workspace.descriptor.public_dict(),
            "commands_used": workspace.commands_used,
            "command_limit": workspace.command_limit,
        }

    def private_state(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._require(workspace_id)
        return {
            "descriptor": workspace.descriptor.public_dict(),
            "modal_object_id": workspace.modal_object_id,
            "run_id": workspace.run_id,
            "command_limit": workspace.command_limit,
            "commands_used": workspace.commands_used,
            "pending_changed_files": sorted(workspace.pending_changed_files),
        }

    def private_states(self) -> list[dict[str, Any]]:
        return [self.private_state(workspace_id) for workspace_id in sorted(self._workspaces)]

    async def close(self, workspace_id: str) -> None:
        workspace = self._workspaces.get(workspace_id)
        if workspace is None:
            return
        async with workspace.lock:
            if self._workspaces.get(workspace_id) is not workspace:
                return
            try:
                await workspace.sandbox.terminate.aio(wait=True)
            except TypeError:
                await workspace.sandbox.terminate.aio()
            except BaseException:
                # Keep the private Modal object ID persisted so cleanup can be
                # retried instead of losing the only handle to a live Sandbox.
                try:
                    await self._report_state()
                except Exception:
                    pass
                raise
            self._forget(workspace_id)
            detach = getattr(workspace.sandbox, "detach", None)
            if detach is not None:
                try:
                    await detach.aio()
                except Exception:
                    pass
            await self._report_state()

    async def aclose(self) -> None:
        await asyncio.gather(*(self.close(workspace_id) for workspace_id in tuple(self._workspaces)))

    async def _report_state(self) -> None:
        if self._state_reporter is not None:
            await self._state_reporter(self.private_states())

    def _require(self, workspace_id: str) -> _Workspace:
        try:
            return self._workspaces[workspace_id]
        except KeyError as exc:
            raise ValueError("unknown or closed Sandbox workspace") from exc

    def _forget(self, workspace_id: str) -> None:
        self._workspaces.pop(workspace_id, None)
        for key, value in list(self._reuse.items()):
            if value == workspace_id:
                self._reuse.pop(key, None)


def result_content(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)
