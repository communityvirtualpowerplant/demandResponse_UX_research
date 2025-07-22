import asyncio
from bleak import BleakScanner, BleakClient

TARGET_NAME_PART = "AC2A"
TARGET_ADDRESS = "C8:A0:09:CD:DA:61"

# Notification handler
def notification_handler(sender, data):
    print(f"\n📩 Notification from {sender}:\n  Raw: {data}\n  Hex: {data.hex()}")

async def main():
    print("🔍 Scanning for Bluetti AC2A...")
    devices = await BleakScanner.discover()
    
    target = None
    for d in devices:
        if (TARGET_NAME_PART.lower() in (d.name or "").lower()) or (d.address.upper() == TARGET_ADDRESS.upper()):
            print(f"✓ Found device: {d.address} ({d.name})")
            target = d
            break

    if not target:
        print("❌ Target device not found.")
        return

    print(f"🔗 Connecting to {target.address}...")
    async with BleakClient(target) as client:
        if not client.is_connected:
            print("❌ Connection failed.")
            return
        print("✅ Connected!\n")

        print("🔍 Discovering services and characteristics...\n")
        subscribable_chars = []

        for service in client.services:
            for char in service.characteristics:
                if "notify" in char.properties or "indicate" in char.properties:
                    print(f"🧩 Subscribable: {char.uuid} ({char.description}) [{', '.join(char.properties)}]")
                    subscribable_chars.append(char)

        if not subscribable_chars:
            print("⚠️ No subscribable characteristics found.")
            return

        # Subscribe to each one
        for char in subscribable_chars:
            try:
                await client.start_notify(char.uuid, notification_handler)
                print(f"🔔 Subscribed to {char.uuid}")
            except Exception as e:
                print(f"❌ Failed to subscribe to {char.uuid}: {e}")

        print("\n📡 Listening for notifications... Press Ctrl+C to stop.\n")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping...")

        # Clean up
        for char in subscribable_chars:
            try:
                await client.stop_notify(char.uuid)
                print(f"🔕 Unsubscribed from {char.uuid}")
            except Exception:
                pass

if __name__ == "__main__":
    asyncio.run(main())
