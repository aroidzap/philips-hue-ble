# Philips Hue Bluetooth example app
# Requirements: 
# - Win/Linux/MacOS with Bluetooth LE
# - Paired Philips Hue Light (to make light visible, go to 
#   Hue app > Settings > Voice Assistants > Google Home > Make Visible)
# - Python library: bleak

# pip install bleak
from bleak import BleakClient
from bleak import BleakScanner

import asyncio
import struct
import uuid

class PhilipsHueScanner(BleakScanner):
    SERVICE_UUID = '0000fe0f-0000-1000-8000-00805f9b34fb'
    def __init__(self):
        super().__init__(service_uuids=[PhilipsHueScanner.SERVICE_UUID])

class PhilipsHueClient(BleakClient):   
    def _command(code):
        return uuid.UUID('932c32bd-'+ str(code).zfill(4) + '-47a2-835a-a8d455b859dd')

    def __init__(self, address):
        super().__init__(address)

    async def get_power(self):
        resp = await self.read_gatt_char(PhilipsHueClient._command(2))
        return bool(resp == b'\x01')
    
    async def set_power(self, enabled):
        data = b'\x01' if enabled else b'\x00'
        return await self.write_gatt_char(PhilipsHueClient._command(2), data)

    async def get_brightness(self):
        resp = await self.read_gatt_char(PhilipsHueClient._command(3))
        return struct.unpack("B", resp)[0] / 254
    
    async def set_brightness(self, ratio):
        data = struct.pack("B", max(1, min(ratio * 254, 254)))
        return await self.write_gatt_char(PhilipsHueClient._command(3), data)

    async def get_temperature_k(self):
        resp = await self.read_gatt_char(PhilipsHueClient._command(4))
        colortemp_mireds = struct.unpack("h", resp)[0]
        if colortemp_mireds == -1:
            return None
        return int(round(1e6 / colortemp_mireds))
    
    async def set_temperature_k(self, temperature_k):
        colortemp_mireds = int(round(1e6 / temperature_k))
        data = struct.pack("h", max(153, min(colortemp_mireds, 500)))
        return await self.write_gatt_char(PhilipsHueClient._command(4), data)

    async def get_xy(self):
        scale = 1 / 2**16
        resp = await self.read_gatt_char(PhilipsHueClient._command(5))
        x, y = [x * scale for x in struct.unpack('HH', resp)]
        return (x, y)
    
    async def set_xy(self, xy):
        scale = 2**16
        data = struct.pack('HH', bytearray([scale * val for val in xy]))
        return await self.write_gatt_char(PhilipsHueClient._command(5), data)

async def main(address = None):

    if address is None:
        print("BLE Scanning...")
        print()

        hue_devices = await PhilipsHueScanner.discover()
        hue_devices = sorted(hue_devices, key=lambda d: d.rssi, reverse=True)
        
        device = hue_devices[0]
        address = device.address
        print(f"BLE Device: {device.name}")
        print(f"BLE rssi: {device.rssi}")
    
    print()
    print(f"BLE Address: {address}")

    async with PhilipsHueClient(address) as hue:
        print(f"BLE connected: {hue.is_connected}")
        print()

        while True:
            print(f"power: {await hue.get_power()}")
            print(f"brightness: {await hue.get_brightness()}")
            print(f"temperature_k: {await hue.get_temperature_k()}")
            print(f"get_xy: {await hue.get_xy()}") # TODO: convert xy/temperature + brightness to rgb/hsb/hsv and vice versa
            print()
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Philips Hue White And Color Ambiance A67 - Example BLE App",
        epilog="* Pair Philips Hue in advance! "
        "(Hue App > Settings > Voice Assistants > Google Home > Make Visible, then pair on PC)"
    )
    parser.add_argument("address", type=str, default=None, nargs="?")
    args = parser.parse_args()

    asyncio.run(main(args.address))
