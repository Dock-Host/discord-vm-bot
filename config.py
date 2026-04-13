import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    discord_token: str
    guild_id: int
    proxmox_host: str
    proxmox_user: str
    proxmox_password: str
    proxmox_verify_ssl: bool
    proxmox_node: str
    proxmox_storage: str
    proxmox_bridge: str
    proxmox_default_cores: int
    proxmox_template_map: dict[str, int]



def _parse_template_map(raw_value: str) -> dict[str, int]:
    template_map: dict[str, int] = {}
    if not raw_value:
        return template_map

    for pair in raw_value.split(","):
        key, sep, value = pair.partition(":")
        if not sep:
            continue
        key = key.strip().lower()
        value = value.strip()
        if not key or not value:
            continue
        template_map[key] = int(value)

    return template_map


settings = Settings(
    discord_token=os.getenv("DISCORD_TOKEN", ""),
    guild_id=int(os.getenv("DISCORD_GUILD_ID", "0")),
    proxmox_host=os.getenv("PROXMOX_HOST", ""),
    proxmox_user=os.getenv("PROXMOX_USER", ""),
    proxmox_password=os.getenv("PROXMOX_PASSWORD", ""),
    proxmox_verify_ssl=_as_bool(os.getenv("PROXMOX_VERIFY_SSL", "false")),
    proxmox_node=os.getenv("PROXMOX_NODE", ""),
    proxmox_storage=os.getenv("PROXMOX_STORAGE", "local-lvm"),
    proxmox_bridge=os.getenv("PROXMOX_BRIDGE", "vmbr0"),
    proxmox_default_cores=int(os.getenv("PROXMOX_DEFAULT_CORES", "2")),
    proxmox_template_map=_parse_template_map(os.getenv("PROXMOX_TEMPLATE_MAP", "")),
)
