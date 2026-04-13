import asyncio

import discord
from discord import app_commands

from config import settings
from proxmox_client import ProxmoxClient


intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
proxmox = ProxmoxClient()


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
    await interaction.response.defer(thinking=True)

    def run_create() -> dict:
        return proxmox.create_vm(
            vm_name=vm_name,
            operating_system=operating_system,
            ram_mb=ram,
            disk_gb=disk,
        )

    try:
        if no_timeout:
            result = await asyncio.wait_for(asyncio.to_thread(run_create), timeout=None)
        else:
            result = await asyncio.wait_for(asyncio.to_thread(run_create), timeout=45)
    except TimeoutError:
        await interaction.followup.send("⏱️ Timeout while creating VM. Try with no-timeout=true.")
        return
    except Exception as exc:  # noqa: BLE001
        await interaction.followup.send(f"❌ Error: {exc}")
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


@client.event
async def on_ready() -> None:
    guild = discord.Object(id=settings.guild_id) if settings.guild_id else None
    await tree.sync(guild=guild)
    print(f"Logged in as {client.user} (ID: {client.user.id})")


if __name__ == "__main__":
    if not settings.discord_token:
        raise RuntimeError("DISCORD_TOKEN is not set")
    client.run(settings.discord_token)
