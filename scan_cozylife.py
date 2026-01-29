#!/usr/bin/env python3
"""
Network scanner for CozyLife devices.
Scans specified IP ranges for CozyLife devices on port 5555.

Usage:
  python3 scan_cozylife.py 192.168.1.0/24
  python3 scan_cozylife.py 192.168.1.100-192.168.1.200
  python3 scan_cozylife.py 192.168.1.50
"""

import socket
import json
import time
import sys
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

PORT = 5555
TIMEOUT = 2


def scan_device(ip):
    """Try to connect to a device and get its info."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect((str(ip), PORT))

        # Send CMD_INFO (0) to get device information
        sn = str(int(time.time() * 1000))
        message = json.dumps({
            "cmd": 0,
            "pv": 0,
            "sn": sn,
            "msg": {}
        }) + "\r\n"

        sock.send(message.encode('utf-8'))

        # Wait for response
        sock.settimeout(3)
        response = sock.recv(1024).decode('utf-8').strip()
        sock.close()

        # Parse response
        data = json.loads(response)
        if data.get('cmd') == 0 and 'msg' in data:
            msg = data['msg']
            return {
                'ip': str(ip),
                'serial_number': msg.get('did', 'unknown'),
                'device_type': msg.get('dtp', 'unknown'),
                'product_id': msg.get('pid', 'unknown'),
                'model': msg.get('model', 'unknown'),
                'mac': msg.get('mac', 'unknown'),
                'software_version': msg.get('sv', 'unknown'),
                'hardware_version': msg.get('hv', 'unknown'),
            }
    except (socket.timeout, socket.error, json.JSONDecodeError, KeyError):
        pass
    except Exception as e:
        pass

    return None


def parse_ip_range(ip_str):
    """Parse IP range string into list of IPs."""
    ips = []

    # CIDR notation (e.g., 192.168.1.0/24)
    if '/' in ip_str:
        try:
            network = ipaddress.ip_network(ip_str, strict=False)
            ips = list(network.hosts())
        except ValueError as e:
            print(f"Invalid CIDR notation: {e}")
            sys.exit(1)

    # Range notation (e.g., 192.168.1.100-192.168.1.200)
    elif '-' in ip_str:
        try:
            start_str, end_str = ip_str.split('-')
            start = ipaddress.ip_address(start_str.strip())
            end = ipaddress.ip_address(end_str.strip())

            current = int(start)
            end_int = int(end)
            while current <= end_int:
                ips.append(ipaddress.ip_address(current))
                current += 1
        except ValueError as e:
            print(f"Invalid IP range: {e}")
            sys.exit(1)

    # Single IP
    else:
        try:
            ips = [ipaddress.ip_address(ip_str.strip())]
        except ValueError as e:
            print(f"Invalid IP address: {e}")
            sys.exit(1)

    return ips


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 scan_cozylife.py 192.168.1.0/24")
        print("  python3 scan_cozylife.py 192.168.1.100-192.168.1.200")
        print("  python3 scan_cozylife.py 192.168.1.50")
        sys.exit(1)

    ip_range = sys.argv[1]
    ips = parse_ip_range(ip_range)

    print(f"Scanning {len(ips)} IP addresses for CozyLife devices on port {PORT}...")
    print("This may take a few moments...\n")

    devices = []

    # Scan IPs concurrently
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(scan_device, ip): ip for ip in ips}

        for future in as_completed(futures):
            ip = futures[future]
            result = future.result()
            if result:
                devices.append(result)
                device_type_name = {
                    '00': 'Switch/Plug',
                    '01': 'Light',
                    '02': 'Energy Storage'
                }.get(result['device_type'], 'Unknown')

                print(f"✓ Found device at {result['ip']}")
                print(f"  Type: {device_type_name} ({result['device_type']})")
                print(f"  Serial: {result['serial_number']}")
                print(f"  Model: {result['model']}")
                print()

    # Print summary
    print("=" * 70)
    print(f"Scan complete! Found {len(devices)} CozyLife device(s).")
    print("=" * 70)

    if not devices:
        print("\nNo devices found. Make sure:")
        print("  1. Devices are powered on and connected to your network")
        print("  2. You're scanning the correct IP range")
        print("  3. Your firewall allows connections to port 5555")
        return

    # Generate configuration
    print("\n" + "=" * 70)
    print("Configuration for configuration.yaml:")
    print("=" * 70)
    print("\nhass_cozylife_local_pull:")
    print("  lang: en")
    print("  devices:")

    for i, device in enumerate(devices, 1):
        # Generate friendly alias based on device type
        device_type_name = {
            '00': 'Switch',
            '01': 'Light',
            '02': 'EnergyStorage'
        }.get(device['device_type'], 'Device')

        alias = f"{device_type_name}_{i:02d}"

        print(f"    - serial_number: {device['serial_number']}")
        print(f"      alias: {alias}")
        print(f"      ip: {device['ip']}")

    print("\n" + "=" * 70)
    print("Copy the configuration above into your configuration.yaml file.")
    print("You can customize the alias names to something more meaningful.")
    print("=" * 70)


if __name__ == "__main__":
    main()
