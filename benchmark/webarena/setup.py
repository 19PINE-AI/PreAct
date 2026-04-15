"""WebArena environment setup and task generation.

Generates task config files from WebArena's raw task definitions,
replacing URL placeholders with actual server addresses.
"""

import json
import os
import subprocess
import time
from pathlib import Path

WEBARENA_ROOT = Path(__file__).parent.parent.parent / "vendor" / "webarena"
CONFIG_DIR = Path(__file__).parent / "configs"

# Default ports for WebArena services
DEFAULT_PORTS = {
    "SHOPPING": 7770,
    "SHOPPING_ADMIN": 7780,
    "REDDIT": 9999,
    "GITLAB": 8023,
    "WIKIPEDIA": 8888,
    "MAP": 3000,
    "HOMEPAGE": 4399,
}


def generate_task_configs(
    hostname: str = "localhost",
    sites: list[str] | None = None,
    output_dir: str | None = None,
) -> list[Path]:
    """Generate per-task JSON configs from WebArena's raw task definitions.

    Replaces __SITE_NAME__ placeholders with actual URLs.

    Args:
        hostname: Server hostname (localhost for Docker on same machine).
        sites: List of sites to generate configs for. Default: shopping_admin only.
        output_dir: Where to write config files.

    Returns:
        List of paths to generated config files.
    """
    sites = sites or ["shopping_admin"]
    output_dir = Path(output_dir) if output_dir else CONFIG_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_path = WEBARENA_ROOT / "config_files" / "test.raw.json"
    with open(raw_path) as f:
        all_tasks = json.load(f)

    # Build URL replacement map
    url_map = {}
    for site_upper, port in DEFAULT_PORTS.items():
        url_map[f"__{site_upper}__"] = f"http://{hostname}:{port}"

    # Filter tasks by site
    site_set = set(sites)
    filtered = [
        t for t in all_tasks
        if set(t.get("sites", [])).issubset(site_set)
    ]

    generated = []
    for task in filtered:
        # Replace URL placeholders
        task_json = json.dumps(task)
        for placeholder, url in url_map.items():
            task_json = task_json.replace(placeholder, url)
        task_data = json.loads(task_json)

        # Write individual config
        config_path = output_dir / f"{task_data['task_id']}.json"
        with open(config_path, "w") as f:
            json.dump(task_data, f, indent=2)
        generated.append(config_path)

    print(f"Generated {len(generated)} task configs in {output_dir}")
    return generated


def start_shopping_admin(hostname: str = "localhost") -> bool:
    """Start the shopping_admin Docker container.

    Returns True if the container is running and accessible.
    """
    # Check if already running
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=shopping_admin", "--format", "{{.Names}}"],
        capture_output=True, text=True,
    )
    if "shopping_admin" in result.stdout:
        print("shopping_admin container already running")
        return True

    # Check if container exists but stopped
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", "name=shopping_admin", "--format", "{{.Names}}"],
        capture_output=True, text=True,
    )
    if "shopping_admin" in result.stdout:
        print("Starting existing shopping_admin container...")
        subprocess.run(["docker", "start", "shopping_admin"], check=True)
    else:
        # Check if image is loaded
        result = subprocess.run(
            ["docker", "images", "--format", "{{.Repository}}", "shopping_admin_final_0719"],
            capture_output=True, text=True,
        )
        if "shopping_admin_final_0719" not in result.stdout:
            print("ERROR: shopping_admin_final_0719 image not found.")
            print("Load it with: docker load --input shopping_admin_final_0719.tar")
            return False

        print("Creating shopping_admin container...")
        subprocess.run(
            ["docker", "run", "--name", "shopping_admin", "-p", "7780:80", "-d",
             "shopping_admin_final_0719"],
            check=True,
        )

    # Wait for service to start
    print("Waiting for shopping_admin to start (up to 90s)...")
    for i in range(90):
        try:
            import urllib.request
            urllib.request.urlopen(f"http://{hostname}:7780/admin", timeout=3)
            break
        except Exception:
            time.sleep(1)
            if i % 10 == 0:
                print(f"  waiting... ({i}s)")
    else:
        print("WARNING: shopping_admin may not be fully ready")

    # Configure base URL
    print("Configuring base URL...")
    subprocess.run([
        "docker", "exec", "shopping_admin",
        "/var/www/magento2/bin/magento", "setup:store-config:set",
        f"--base-url=http://{hostname}:7780",
    ], capture_output=True)

    subprocess.run([
        "docker", "exec", "shopping_admin",
        "mysql", "-u", "magentouser", "-pMyPassword", "magentodb", "-e",
        f'UPDATE core_config_data SET value="http://{hostname}:7780/" WHERE path = "web/secure/base_url";',
    ], capture_output=True)

    # Disable forced password reset
    subprocess.run([
        "docker", "exec", "shopping_admin",
        "php", "/var/www/magento2/bin/magento", "config:set",
        "admin/security/password_is_forced", "0",
    ], capture_output=True)
    subprocess.run([
        "docker", "exec", "shopping_admin",
        "php", "/var/www/magento2/bin/magento", "config:set",
        "admin/security/password_lifetime", "0",
    ], capture_output=True)

    # Flush cache
    subprocess.run([
        "docker", "exec", "shopping_admin",
        "/var/www/magento2/bin/magento", "cache:flush",
    ], capture_output=True)

    print(f"shopping_admin ready at http://{hostname}:7780/admin")
    return True


def get_auth_cookies(hostname: str = "localhost") -> dict:
    """Get authentication cookies for the shopping_admin site.

    WebArena tasks that require_login need pre-authenticated sessions.
    """
    # The WebArena prepare.sh script handles this.
    # For now, return the path to the auth state file.
    auth_dir = Path(__file__).parent / ".auth"
    auth_dir.mkdir(exist_ok=True)
    return {
        "storage_state": str(auth_dir / "shopping_admin_state.json"),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        hostname = sys.argv[2] if len(sys.argv) > 2 else "localhost"
        if start_shopping_admin(hostname):
            generate_task_configs(hostname, ["shopping_admin"])
    elif len(sys.argv) > 1 and sys.argv[1] == "configs":
        hostname = sys.argv[2] if len(sys.argv) > 2 else "localhost"
        generate_task_configs(hostname, ["shopping_admin"])
    else:
        print("Usage:")
        print("  python setup.py setup [hostname]  — Start Docker + generate configs")
        print("  python setup.py configs [hostname] — Generate configs only")
