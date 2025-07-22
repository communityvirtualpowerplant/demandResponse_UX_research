import asyncio
from bleak import BleakScanner, BleakClient

TARGET_NAME_PART = "AC2A"  # Case-insensitive match in device name
TARGET_ADDRESS = "C8:A0:09:CD:DA:61"  # Optional: replace with exact MAC

async def main():
    print("Scanning for AC2A device...")
    devices = await BleakScanner.discover()
    
    # Match by name or address
    target = None
    for d in devices:
        if (TARGET_NAME_PART.lower() in (d.name or "").lower()) or (d.address.upper() == TARGET_ADDRESS.upper()):
            print(f"Found matching device: {d.address} ({d.name})")
            target = d
            break

    if not target:
        print("AC2A device not found. Is it powered on and advertising?")
        return

    print(f"Connecting to {target.address} ({target.name})...")

    async with BleakClient(target) as client:
        if not client.is_connected:
            print("Failed to connect.")
            return
        print("Connected!")

        print("Discovering services and characteristics...")
        for service in client.services:
            print(f"Service {service.uuid} ({service.description})")
            for char in service.characteristics:
                props = ", ".join(char.properties)
                print(f"  └── * Char {char.uuid} ({char.description})")
                print(f"      Properties: {props}")
                # Try reading if readable
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        try:
                            decoded = value.decode("utf-8").strip()
                        except:
                            decoded = value.hex()
                        print(f"      Value: {decoded}")
                    except Exception as e:
                        print(f"      [!] Read failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
