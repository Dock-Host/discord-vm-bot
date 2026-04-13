import asyncio
import contextlib
import os
import shlex
from collections.abc import Callable

import discord
from discord import app_commands

from config import settings
from proxmox_client import ProxmoxClient


intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
proxmox = ProxmoxClient()

stream_process: asyncio.subprocess.Process | None = None
preview_task: asyncio.Task | None = None
PREVIEW_FILE = "preview.jpg"
STREAM_FILE = "stream_input.mp4"


async def run_proxmox_action(
    interaction: discord.Interaction,
    action: Callable[[], dict],
    no_timeout: bool,
) -> dict | None:
    await interaction.response.defer(thinking=True)
    try:
        if no_timeout:
            return await asyncio.wait_for(asyncio.to_thread(action), timeout=None)
        return await asyncio.wait_for(asyncio.to_thread(action), timeout=90)
    except TimeoutError:
        await interaction.followup.send("⏱️ Timeout. Повторите команду с no-timeout=true.")
        return None
    except Exception as exc:  # noqa: BLE001
        await interaction.followup.send(f"❌ Error: {exc}")
        return None


async def vm_power_command(
    interaction: discord.Interaction,
    vm_name: str,
    method: Callable[[str, bool], dict],
    action_name: str,
    no_timeout: bool,
    wait: bool,
) -> None:
    result = await run_proxmox_action(
        interaction=interaction,
        action=lambda: method(vm_name, wait),
        no_timeout=no_timeout,
    )
    if not result:
        return
    if not result.get("ok"):
        await interaction.followup.send(f"❌ {result['message']}")
        return
    await interaction.followup.send(
        f"✅ {action_name}\nName: **{vm_name}**\nVMID: **{result['vmid']}**\nTask: `{result['task']}`"
    )


async def run_preview_loop(rtmp_url: str) -> None:
    while True:
        with contextlib.suppress(FileNotFoundError):
            os.remove(PREVIEW_FILE)

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            rtmp_url,
            "-frames:v",
            "1",
            PREVIEW_FILE,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        await asyncio.sleep(1)


@tree.command(name="create-vm", description="Create VM in Proxmox")
@app_commands.describe(
    vm_name="VM name",
    operating_system="OS key (e.g. ubuntu-24.04)",
    ram="RAM in MB",
    disk="Disk size in GB",
    no_timeout="Skip Discord interaction timeout (long operation)",
)
async def create_vm(
    interaction: discord.Interaction,
    vm_name: str,
    operating_system: str,
    ram: app_commands.Range[int, 256, 262144],
    disk: app_commands.Range[int, 4, 4096],
    no_timeout: bool = False,
) -> None:
    result = await run_proxmox_action(
        interaction=interaction,
        action=lambda: proxmox.create_vm(vm_name, operating_system, ram, disk),
        no_timeout=no_timeout,
    )
    if not result:
        return
    if not result.get("ok"):
        await interaction.followup.send(f"❌ {result['message']}")
        return

    await interaction.followup.send(
        "✅ VM creation completed\n"
        f"Name: **{vm_name}**\n"
        f"VMID: **{result['vmid']}**\n"
        f"Task: `{result['task']}`"
    )


@tree.command(name="start-vm", description="Start VM and wait for task")
@app_commands.describe(vm_name="VM name", no_timeout="Skip timeout")
async def start_vm(interaction: discord.Interaction, vm_name: str, no_timeout: bool = False) -> None:
    await vm_power_command(interaction, vm_name, proxmox.start_vm, "VM started", no_timeout, wait=True)


@tree.command(name="stop-vm", description="Stop VM and wait for task")
@app_commands.describe(vm_name="VM name", no_timeout="Skip timeout")
async def stop_vm(interaction: discord.Interaction, vm_name: str, no_timeout: bool = False) -> None:
    await vm_power_command(interaction, vm_name, proxmox.stop_vm, "VM stopped", no_timeout, wait=True)


@tree.command(name="restart-vm", description="Restart VM and wait for task")
@app_commands.describe(vm_name="VM name", no_timeout="Skip timeout")
async def restart_vm(interaction: discord.Interaction, vm_name: str, no_timeout: bool = False) -> None:
    await vm_power_command(interaction, vm_name, proxmox.restart_vm, "VM restarted", no_timeout, wait=True)


@tree.command(name="pause-vm", description="Pause VM and wait for task")
@app_commands.describe(vm_name="VM name", no_timeout="Skip timeout")
async def pause_vm(interaction: discord.Interaction, vm_name: str, no_timeout: bool = False) -> None:
    await vm_power_command(interaction, vm_name, proxmox.pause_vm, "VM paused", no_timeout, wait=True)


@tree.command(name="start-vm-background", description="Start VM in background")
@app_commands.describe(vm_name="VM name")
async def start_vm_background(interaction: discord.Interaction, vm_name: str) -> None:
    await vm_power_command(interaction, vm_name, proxmox.start_vm, "VM start queued (background)", True, wait=False)


@tree.command(name="stop-vm-background", description="Stop VM in background")
@app_commands.describe(vm_name="VM name")
async def stop_vm_background(interaction: discord.Interaction, vm_name: str) -> None:
    await vm_power_command(interaction, vm_name, proxmox.stop_vm, "VM stop queued (background)", True, wait=False)


@tree.command(name="restart-vm-background", description="Restart VM in background")
@app_commands.describe(vm_name="VM name")
async def restart_vm_background(interaction: discord.Interaction, vm_name: str) -> None:
    await vm_power_command(interaction, vm_name, proxmox.restart_vm, "VM restart queued (background)", True, wait=False)


@tree.command(name="pause-vm-background", description="Pause VM in background")
@app_commands.describe(vm_name="VM name")
async def pause_vm_background(interaction: discord.Interaction, vm_name: str) -> None:
    await vm_power_command(interaction, vm_name, proxmox.pause_vm, "VM pause queued (background)", True, wait=False)


@tree.command(name="edit-vm", description="Edit existing VM")
@app_commands.describe(
    vm_name="VM name",
    ram="New RAM in MB",
    disk="New disk size in GB",
    no_timeout="Skip timeout for long operation",
)
async def edit_vm(
    interaction: discord.Interaction,
    vm_name: str,
    ram: app_commands.Range[int, 256, 262144] | None = None,
    disk: app_commands.Range[int, 4, 4096] | None = None,
    no_timeout: bool = False,
) -> None:
    result = await run_proxmox_action(
        interaction=interaction,
        action=lambda: proxmox.edit_vm(vm_name, ram, disk),
        no_timeout=no_timeout,
    )
    if not result:
        return
    if not result.get("ok"):
        await interaction.followup.send(f"❌ {result['message']}")
        return

    await interaction.followup.send(
        f"✅ VM updated\nName: **{vm_name}**\nVMID: **{result['vmid']}**\nTask: `{result['task']}`"
    )


@tree.command(name="delete-vm", description="Delete VM")
@app_commands.describe(
    vm_name="VM name",
    purge="Delete all related storage",
    no_timeout="Skip timeout for long operation",
)
async def delete_vm(
    interaction: discord.Interaction,
    vm_name: str,
    purge: bool = False,
    no_timeout: bool = False,
) -> None:
    result = await run_proxmox_action(
        interaction=interaction,
        action=lambda: proxmox.delete_vm(vm_name, purge),
        no_timeout=no_timeout,
    )
    if not result:
        return
    if not result.get("ok"):
        await interaction.followup.send(f"❌ {result['message']}")
        return

    await interaction.followup.send(
        f"✅ VM deletion started\nName: **{vm_name}**\nVMID: **{result['vmid']}**\nTask: `{result['task']}`"
    )


@tree.command(name="preview-vm", description="Preview VM info")
@app_commands.describe(vm_name="VM name", no_timeout="Skip timeout for long operation")
async def preview_vm(
    interaction: discord.Interaction,
    vm_name: str,
    no_timeout: bool = False,
) -> None:
    result = await run_proxmox_action(
        interaction=interaction,
        action=lambda: proxmox.preview_vm(vm_name),
        no_timeout=no_timeout,
    )
    if not result:
        return
    if not result.get("ok"):
        await interaction.followup.send(f"❌ {result['message']}")
        return

    status = result["status"]
    config = result["config"]
    message = (
        "🖥️ VM preview\n"
        f"Name: **{result['name']}**\n"
        f"VMID: **{result['vmid']}**\n"
        f"State: **{status.get('status', 'unknown')}**\n"
        f"CPU: `{config.get('cores', 'n/a')}`\n"
        f"RAM: `{config.get('memory', 'n/a')} MB`\n"
        f"Disk: `{config.get('scsi0', 'n/a')}`"
    )

    if os.path.exists(PREVIEW_FILE):
        await interaction.followup.send(message, file=discord.File(PREVIEW_FILE, filename="preview.jpg"))
        with contextlib.suppress(FileNotFoundError):
            os.remove(PREVIEW_FILE)
        return

    await interaction.followup.send(message)


@tree.command(name="deploy_video-from-rtmp_youtube", description="Download video and start YouTube RTMP loop")
@app_commands.describe(
    youtube_url="YouTube video URL for yt-dlp",
    rtmp_url="YouTube RTMP destination URL",
    create_vm_ubuntu="Create Proxmox VM Ubuntu 24.04 8GB/128GB before deploy",
)
async def deploy_video_from_rtmp_youtube(
    interaction: discord.Interaction,
    youtube_url: str,
    rtmp_url: str,
    create_vm_ubuntu: bool = True,
) -> None:
    global stream_process, preview_task
    await interaction.response.defer(thinking=True)

    try:
        if create_vm_ubuntu:
            vm_result = await asyncio.to_thread(proxmox.create_stream_vm)
            if not vm_result.get("ok"):
                await interaction.followup.send(f"❌ VM prepare failed: {vm_result['message']}")
                return

        yt_cmd = [
            "yt-dlp",
            "-f",
            "bestvideo+bestaudio/best",
            "--merge-output-format",
            "mp4",
            "-o",
            STREAM_FILE,
            youtube_url,
        ]
        yt_proc = await asyncio.create_subprocess_exec(
            *yt_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, yt_err = await yt_proc.communicate()
        if yt_proc.returncode != 0:
            await interaction.followup.send(f"❌ yt-dlp failed:\n```{yt_err.decode('utf-8', errors='ignore')[:1500]}```")
            return

        ffmpeg_loop_cmd = (
            "while true; do "
            f"ffmpeg -re -stream_loop -1 -i {shlex.quote(STREAM_FILE)} "
            "-c:v libx264 -preset veryfast -maxrate 3000k -bufsize 6000k "
            "-pix_fmt yuv420p -g 50 -c:a aac -b:a 128k -ar 44100 "
            f"-f flv {shlex.quote(rtmp_url)}; "
            "sleep 1; "
            "done"
        )

        if stream_process and stream_process.returncode is None:
            stream_process.terminate()
            await stream_process.wait()

        stream_process = await asyncio.create_subprocess_exec(
            "bash",
            "-lc",
            ffmpeg_loop_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )

        if preview_task and not preview_task.done():
            preview_task.cancel()
            with contextlib.suppress(Exception):
                await preview_task

        preview_task = asyncio.create_task(run_preview_loop(rtmp_url))

        for _ in range(8):
            if os.path.exists(PREVIEW_FILE):
                break
            await asyncio.sleep(1)

    except Exception as exc:  # noqa: BLE001
        await interaction.followup.send(f"❌ Deploy error: {exc}")
        return

    caption = (
        "✅ Proxmox Creating VM from Ubuntu 24.04, RAM 8GB, DISK 128GB; Starting VM from Ubuntu 24.04.\n"
        "✅ Installing ffmpeg and yt-dlp: run inside guest VM (cloud-init/script).\n"
        "✅ yt-dlp download complete (no-timeout) and ffmpeg RTMP while-true loop started (no-timeout)."
    )

    if os.path.exists(PREVIEW_FILE):
        await interaction.followup.send(
            f"{caption}\nSource: {youtube_url}\nRTMP: {rtmp_url}",
            file=discord.File(PREVIEW_FILE, filename="preview.jpg"),
        )
        with contextlib.suppress(FileNotFoundError):
            os.remove(PREVIEW_FILE)
        return

    await interaction.followup.send(f"{caption}\nSource: {youtube_url}\nRTMP: {rtmp_url}")


@client.event
async def on_ready() -> None:
    guild = discord.Object(id=settings.guild_id) if settings.guild_id else None
    await tree.sync(guild=guild)
    print(f"Logged in as {client.user} (ID: {client.user.id})")


if __name__ == "__main__":
    if not settings.discord_token:
        raise RuntimeError("DISCORD_TOKEN is not set")
    client.run(settings.discord_token)
