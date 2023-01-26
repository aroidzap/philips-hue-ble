# Philips Hue Bluetooth example app
# Requirements: 
# - Win/Linux/MacOS with Bluetooth LE
# - Paired Philips Hue Light (to make light visible, go to 
#   Hue app > Settings > Voice Assistants > Google Home > Make Visible)
# - Python library: bleak

# pip install bleak>=0.19.5

# Name: bleak
# Version: 0.19.5
# Summary: Bluetooth Low Energy platform Agnostic Klient
# Home-page: https://github.com/hbldh/bleak

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

    def __init__(self, ble_address):
        super().__init__(ble_address)

    async def get_power(self):
        """
        Gets power state (True == on, False == off)
        """
        resp = await self.read_gatt_char(PhilipsHueClient._command(2))
        return bool(resp == b'\x01')
    
    async def set_power(self, enabled):
        """
        Sets power state (True == on, False == off)
        """
        data = b'\x01' if enabled else b'\x00'
        return await self.write_gatt_char(PhilipsHueClient._command(2), data, response=True)

    async def get_brightness(self):
        """
        Gets brightness in range (0.0 - 1.0]
        """
        resp = await self.read_gatt_char(PhilipsHueClient._command(3))
        return struct.unpack("B", resp)[0] / 254
    
    async def set_brightness(self, ratio):
        """
        Sets brightness in range (0.0 - 1.0]
        """
        data = struct.pack("B", max(1, min(int(round(ratio * 254)), 254)))
        return await self.write_gatt_char(PhilipsHueClient._command(3), data, response=True)

    async def get_temperature_k(self):
        """
        Gets color temperature in kelvin
        """
        resp = await self.read_gatt_char(PhilipsHueClient._command(4))
        colortemp_mireds = struct.unpack("h", resp)[0]
        if colortemp_mireds == -1:
            return None
        return int(round(1e6 / colortemp_mireds))
    
    async def set_temperature_k(self, temperature_k):
        """
        Sets color temperature in kelvin
        """
        colortemp_mireds = int(round(1e6 / temperature_k))
        data = struct.pack("h", max(153, min(colortemp_mireds, 500)))
        return await self.write_gatt_char(PhilipsHueClient._command(4), data, response=True)

    async def get_xy(self):
        """
        Gets color (XY in CIE 1931 colorspace)
        :return: XY coordinate
        :rtype: Tuple[float,float]
        """
        scale = 1 / 2**16
        resp = await self.read_gatt_char(PhilipsHueClient._command(5))
        x, y = [x * scale for x in struct.unpack('HH', resp)]
        return (x, y)
    
    #Color (XY in CIE 1931 colorspace)
    async def set_xy(self, x, y):
        """
        Sets color (XY in CIE 1931 colorspace)
        :param xy: XY coordinate
        :type xy: Tuple[float,float]
        """
        x = max(1, min(0, x))
        y = max(1, min(0, y))
        xysum = x + y
        if xysum > 1:
            x = x / xysum
            y = y / xysum
        scale = 2**16
        data = struct.pack('HH', *[int(round(scale * val)) for val in (x, y)])
        return await self.write_gatt_char(PhilipsHueClient._command(5), data, response=True)

####
# ChatGPT: Function to convert from RGB to CIE 1931 + Brightness and vice versa.
def rgb_to_cie(r, g, b):
    # Apply a gamma correction
    r = pow((r + 0.055) / (1.0 + 0.055), 2.4) if (r > 0.04045) else (r / 12.92)
    g = pow((g + 0.055) / (1.0 + 0.055), 2.4) if (g > 0.04045) else (g / 12.92)
    b = pow((b + 0.055) / (1.0 + 0.055), 2.4) if (b > 0.04045) else (b / 12.92)
    # Convert to XYZ color space
    X = r * 0.4124 + g * 0.3576 + b * 0.1805
    Y = r * 0.2126 + g * 0.7152 + b * 0.0722
    Z = r * 0.0193 + g * 0.1192 + b * 0.9505
    # Convert to CIE 1931 color space
    x = X / (X + Y + Z)
    y = Y / (X + Y + Z)
    brightness = Y
    return (x, y, brightness)

def cie_to_rgb(x, y, brightness):
    # Convert back to XYZ color space
    Y = brightness
    X = (Y / y) * x
    Z = (Y / y) * (1 - x - y)
    # Convert to RGB color space
    r = X * 3.2406 + Y * -1.5372 + Z * -0.4986
    g = X * -0.9689 + Y * 1.8758 + Z * 0.0415
    b = X * 0.0557 + Y * -0.2040 + Z * 1.0570
    # Apply inverse gamma correction
    r = (1.055 * pow(r, (1 / 2.4)) - 0.055) if (r > 0.0031308) else (12.92 * r)
    g = (1.055 * pow(g, (1 / 2.4)) - 0.055) if (g > 0.0031308) else (12.92 * g)
    b = (1.055 * pow(b, (1 / 2.4)) - 0.055) if (b > 0.0031308) else (12.92 * b)
    return (r, g, b)
####

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

        if True:
            while True:
                print(f"power: {await hue.get_power()}")
                print(f"brightness: {await hue.get_brightness()}")
                print(f"temperature_k: {await hue.get_temperature_k()}")
                print(f"get_xy: {await hue.get_xy()}") # TODO: convert xy/temperature + brightness to rgb/hsb/hsv and vice versa
                print()
                await asyncio.sleep(0.5)

        if False:
            while True:
                await hue.set_power(not await hue.get_power())
                await asyncio.sleep(0.5)

        if False:
            import time, math
            while True:
                await hue.set_brightness(0.5 * (1 + math.sin(time.time() * 4)))
                await asyncio.sleep(0.1)

        if False:
            import random
            while True:
                x,y,b = rgb_to_cie(random.random(), random.random(), random.random())
                await hue.set_xy(x, y)
                await hue.set_brightness(b)
                await asyncio.sleep(0.1)

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
