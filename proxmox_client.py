import time

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

    def _wait_for_task(self, upid: str, timeout_sec: int = 300) -> dict:
        start = time.time()
        while True:
            status = self._api.nodes(settings.proxmox_node).tasks(upid).status.get()
            if status.get("status") == "stopped":
                return status
            if time.time() - start > timeout_sec:
                raise TimeoutError(f"Task timeout: {upid}")
            time.sleep(2)

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

        self._wait_for_task(clone_task)

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

    def create_stream_vm(self, vm_name: str = "stream-ubuntu-24-04") -> dict:
        result = self.create_vm(
            vm_name=vm_name,
            operating_system="ubuntu-24.04",
            ram_mb=8192,
            disk_gb=128,
        )
        if not result.get("ok"):
            return result

        start_result = self.start_vm(vm_name=vm_name, wait=True)
        if not start_result.get("ok"):
            return start_result

        return {
            "ok": True,
            "vmid": result["vmid"],
            "message": (
                "Proxmox Creating VM from Ubuntu 24.04, RAM 8GB, DISK 128GB; "
                "Starting VM from Ubuntu 24.04. Install ffmpeg + yt-dlp inside guest manually or via cloud-init."
            ),
            "task": start_result.get("task"),
        }

    def _vm_action(self, vm_name: str, action: str, wait: bool) -> dict:
        vm = self._find_vm(vm_name)
        if not vm:
            return {"ok": False, "message": f"VM '{vm_name}' не найдена."}

        vmid = int(vm["vmid"])
        endpoint = self._api.nodes(settings.proxmox_node).qemu(vmid).status
        action_callable = getattr(endpoint, action)
        task = action_callable.post()
        if wait:
            self._wait_for_task(task)
        return {
            "ok": True,
            "vmid": vmid,
            "task": task,
            "message": f"VM '{vm_name}' action '{action}' started.",
        }

    def start_vm(self, vm_name: str, wait: bool) -> dict:
        return self._vm_action(vm_name, "start", wait)

    def stop_vm(self, vm_name: str, wait: bool) -> dict:
        return self._vm_action(vm_name, "stop", wait)

    def restart_vm(self, vm_name: str, wait: bool) -> dict:
        return self._vm_action(vm_name, "reboot", wait)

    def pause_vm(self, vm_name: str, wait: bool) -> dict:
        return self._vm_action(vm_name, "suspend", wait)

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
