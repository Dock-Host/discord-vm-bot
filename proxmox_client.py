from proxmoxer import ProxmoxAPI

from config import settings


class ProxmoxClient:
    def __init__(self) -> None:
        self._api = ProxmoxAPI(
            host=settings.proxmox_host,
            user=settings.proxmox_user,
            password=settings.proxmox_password,
            verify_ssl=settings.proxmox_verify_ssl,
        )

    def _next_vmid(self) -> int:
        return int(self._api.cluster.nextid.get())

    def create_vm(
        self,
        vm_name: str,
        operating_system: str,
        ram_mb: int,
        disk_gb: int,
    ) -> dict:
        template_id = settings.proxmox_template_map.get(operating_system.lower())
        if template_id is None:
            return {
                "ok": False,
                "message": (
                    f"OS '{operating_system}' не найден. "
                    f"Доступные: {', '.join(settings.proxmox_template_map.keys()) or 'нет'}"
                ),
            }

        vmid = self._next_vmid()

        clone_task = self._api.nodes(settings.proxmox_node).qemu(template_id).clone.post(
            newid=vmid,
            name=vm_name,
            full=1,
            target=settings.proxmox_node,
            storage=settings.proxmox_storage,
        )

        self._api.nodes(settings.proxmox_node).qemu(vmid).config.post(
            memory=ram_mb,
            cores=settings.proxmox_default_cores,
            net0=f"virtio,bridge={settings.proxmox_bridge}",
            scsi0=f"{settings.proxmox_storage}:{disk_gb}",
        )

        return {
            "ok": True,
            "vmid": vmid,
            "task": clone_task,
            "message": f"VM '{vm_name}' (ID: {vmid}) создана.",
        }
