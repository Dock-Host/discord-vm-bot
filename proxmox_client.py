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

    def _find_vm(self, vm_name: str) -> dict | None:
        vm_name = vm_name.strip().lower()
        for vm in self._api.nodes(settings.proxmox_node).qemu.get():
            if str(vm.get("name", "")).lower() == vm_name:
                return vm
        return None

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

    def edit_vm(self, vm_name: str, ram_mb: int | None, disk_gb: int | None) -> dict:
        vm = self._find_vm(vm_name)
        if not vm:
            return {"ok": False, "message": f"VM '{vm_name}' не найдена."}

        vmid = int(vm["vmid"])
        config_payload: dict = {}
        if ram_mb is not None:
            config_payload["memory"] = ram_mb
        if disk_gb is not None:
            config_payload["scsi0"] = f"{settings.proxmox_storage}:{disk_gb}"

        if not config_payload:
            return {"ok": False, "message": "Не указаны параметры для изменения."}

        task = self._api.nodes(settings.proxmox_node).qemu(vmid).config.post(**config_payload)
        return {
            "ok": True,
            "vmid": vmid,
            "task": task,
            "message": f"VM '{vm_name}' обновлена.",
        }

    def delete_vm(self, vm_name: str, purge: bool = False) -> dict:
        vm = self._find_vm(vm_name)
        if not vm:
            return {"ok": False, "message": f"VM '{vm_name}' не найдена."}

        vmid = int(vm["vmid"])
        task = self._api.nodes(settings.proxmox_node).qemu(vmid).delete(purge=1 if purge else 0)
        return {
            "ok": True,
            "vmid": vmid,
            "task": task,
            "message": f"VM '{vm_name}' удаляется.",
        }

    def preview_vm(self, vm_name: str) -> dict:
        vm = self._find_vm(vm_name)
        if not vm:
            return {"ok": False, "message": f"VM '{vm_name}' не найдена."}

        vmid = int(vm["vmid"])
        status = self._api.nodes(settings.proxmox_node).qemu(vmid).status.current.get()
        config = self._api.nodes(settings.proxmox_node).qemu(vmid).config.get()

        return {
            "ok": True,
            "vmid": vmid,
            "name": vm.get("name", vm_name),
            "status": status,
            "config": config,
        }
