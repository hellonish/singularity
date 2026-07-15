"""Build and publish versioned Modal Sandbox Images outside request handling.

Run this module from an authenticated operator shell. Runtime Sandbox creation
uses the resulting names through SINGULARITY_MODAL_SANDBOX_IMAGE_* variables.
"""
from __future__ import annotations

import os

import modal

from engine.chat.modal_tools import modal_environment_name


def sandbox_images() -> dict[str, modal.Image]:
    base = modal.Image.debian_slim(python_version="3.12").apt_install(
        "git", "ripgrep", "curl", "build-essential"
    )
    code = base.apt_install("nodejs", "npm").uv_pip_install("pytest", "ruff")
    return {
        "repository": base.uv_pip_install("pytest", "ruff"),
        "repository_build": code,
        "code": code,
        "data": base.uv_pip_install("pandas", "numpy", "scipy", "matplotlib"),
        "service": code,
        "gpu": base.uv_pip_install("torch", "pytest"),
    }


def publish() -> None:
    environment = modal_environment_name()
    prefix = os.getenv("SINGULARITY_MODAL_SANDBOX_IMAGE_PREFIX", "singularity-sandbox")
    app = modal.App.lookup(
        os.getenv("SINGULARITY_MODAL_SANDBOX_APP", "singularity-agent-sandboxes"),
        environment_name=environment,
        create_if_missing=True,
    )
    for profile, image in sandbox_images().items():
        name = f"{prefix}-{profile}"
        image.build(app).publish(name, environment_name=environment)
        print(f"{profile}: {name}")


if __name__ == "__main__":
    publish()
