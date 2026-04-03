"""
Detect the server's outbound IP address.
This is the IP that will be used for all Meritto API calls.

Run this on your server to see what IP it uses for outbound connections.
"""

import socket
import httpx


def get_my_ip_method_1():
    """Method 1: Connect to a public IP and see what local IP is used."""
    try:
        # Connect to Google DNS (doesn't actually send data)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception as e:
        return f"Error: {e}"


def get_my_ip_method_2():
    """Method 2: Use an external API to see what IP we look like from outside."""
    try:
        response = httpx.get("https://api.ipify.org?format=json", timeout=10)
        return response.json().get("ip", "Not found")
    except Exception as e:
        return f"Error: {e}"


def get_my_ip_method_3():
    """Method 3: Check local network interfaces."""
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    print("\n" + "="*70)
    print("SERVER OUTBOUND IP DETECTION")
    print("="*70)
    
    print("\n1. Local Connection IP (Method 1):")
    print(f"   {get_my_ip_method_1()}")
    
    print("\n2. External IP (What Meritto sees) (Method 2):")
    print(f"   {get_my_ip_method_2()}")
    
    print("\n3. Hostname Resolution (Method 3):")
    print(f"   {get_my_ip_method_3()}")
    
    print("\n" + "="*70)
    print("RECOMMENDATION:")
    print("="*70)
    print("""
Use the IP from Method 2 (External IP) - that's what Meritto sees
when your server makes API calls.

Steps:
1. Run this script and note the IP from Method 2
2. Log into Meritto Dashboard
3. Settings → Security → IP Whitelist
4. Add that single IP
5. Save and test
    """)
    print("="*70 + "\n")
