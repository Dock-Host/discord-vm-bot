import asyncio
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


async def run_proxmox_action(
    interaction: discord.Interaction,
    action: Callable[[], dict],
    no_timeout: bool,
) -> dict | None:
    await interaction.response.defer(thinking=True)
    try:
        if no_timeout:
            return await asyncio.wait_for(asyncio.to_thread(action), timeout=None)
        return await asyncio.wait_for(asyncio.to_thread(action), timeout=45)
    except TimeoutError:
        await interaction.followup.send("⏱️ Timeout. Повторите команду с no-timeout=true.")
        return None
    except Exception as exc:  # noqa: BLE001
        await interaction.followup.send(f"❌ Error: {exc}")
        return None


@tree.command(name="create-vm", description="Create VM in Proxmox")
@app_commands.describe(
    vm_name="VM name",
    operating_system="OS key (e.g. ubuntu-22.04)",
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
        "✅ VM creation started\n"
        f"Name: **{vm_name}**\n"
        f"VMID: **{result['vmid']}**\n"
        f"Task: `{result['task']}`"
    )


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
    await interaction.followup.send(
        "🖥️ VM preview\n"
        f"Name: **{result['name']}**\n"
        f"VMID: **{result['vmid']}**\n"
        f"State: **{status.get('status', 'unknown')}**\n"
        f"CPU: `{config.get('cores', 'n/a')}`\n"
        f"RAM: `{config.get('memory', 'n/a')} MB`\n"
        f"Disk: `{config.get('scsi0', 'n/a')}`"
    )


@tree.command(name="deploy_video-from-rtmp_youtube", description="Download video and start YouTube RTMP loop")
@app_commands.describe(
    youtube_url="YouTube video URL for yt-dlp",
    rtmp_url="YouTube RTMP destination URL",
)
async def deploy_video_from_rtmp_youtube(
    interaction: discord.Interaction,
    youtube_url: str,
    rtmp_url: str,
) -> None:
    global stream_process
    await interaction.response.defer(thinking=True)

    output_file = "stream_input.mp4"
    yt_cmd = [
        "yt-dlp",
        "-f",
        "bestvideo+bestaudio/best",
        "--merge-output-format",
        "mp4",
        "-o",
        output_file,
        youtube_url,
    ]

    try:
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
            f"ffmpeg -re -stream_loop -1 -i {shlex.quote(output_file)} "
            "-c:v libx264 -preset veryfast -maxrate 3000k -bufsize 6000k "
            "-pix_fmt yuv420p -g 50 -c:a aac -b:a 128k -ar 44100 "
            f"-f flv {shlex.quote(rtmp_url)}; "
            "sleep 2; "
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

    except Exception as exc:  # noqa: BLE001
        await interaction.followup.send(f"❌ Deploy error: {exc}")
        return

    await interaction.followup.send(
        "✅ Видео скачано через yt-dlp и ffmpeg loop запущен (no-timeout).\n"
        f"Source: {youtube_url}\n"
        f"RTMP: {rtmp_url}"
    )


@client.event
async def on_ready() -> None:
    guild = discord.Object(id=settings.guild_id) if settings.guild_id else None
    await tree.sync(guild=guild)
    print(f"Logged in as {client.user} (ID: {client.user.id})")


if __name__ == "__main__":
    if not settings.discord_token:
        raise RuntimeError("DISCORD_TOKEN is not set")
    client.run(settings.discord_token)
