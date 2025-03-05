import psutil
import platform
from datetime import datetime, timedelta
import os
from typing import Dict, Any

class SystemMonitor:
    def __init__(self):
        self.boot_time = datetime.fromtimestamp(psutil.boot_time())
        
    def get_basic_status(self) -> Dict[str, Any]:
        """Get basic robot status information"""
        return {
            "connection_status": "online",  # This would need proper implementation
            "battery_level": self._get_battery_level(),
            "cpu_temperature": self._get_cpu_temperature(),
            "system_uptime": self._get_uptime(),
            "last_sync": datetime.now().isoformat(),
            "operating_mode": self._get_operating_mode()
        }
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get system health metrics"""
        return {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage": psutil.virtual_memory().percent,
            "storage_space": self._get_storage_info(),
            "network_strength": self._get_network_strength(),
            "load_average": os.getloadavg(),
            "active_processes": len(psutil.pids()),
            "critical_services": self._get_critical_services_status()
        }
    
    def get_diagnostic_info(self) -> Dict[str, Any]:
        """Get diagnostic information"""
        return {
            "system_errors": self._get_system_errors(),
            "hardware_warnings": self._get_hardware_warnings(),
            "software_version": platform.version(),
            "last_update": self._get_last_update_time(),
            "connected_peripherals": self._get_connected_peripherals(),
            "network_config": self._get_network_config()
        }

    def _get_battery_level(self) -> float:
        """Get battery level percentage"""
        battery = psutil.sensors_battery()
        return battery.percent if battery else 0.0

    def _get_cpu_temperature(self) -> float:
        """Get CPU temperature"""
        try:
            # Try Raspberry Pi specific method first
            try:
                temp = os.popen("vcgencmd measure_temp").readline()
                return float(temp.replace("temp=", "").replace("'C\n", ""))
            except:
                # If vcgencmd fails, try reading from thermal zone
                if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                    with open('/sys/class/thermal/thermal_zone0/temp') as f:
                        temp = float(f.read().strip()) / 1000
                    return temp
                
                # On macOS, we can try using system_profiler
                if platform.system() == 'Darwin':
                    try:
                        cmd = "system_profiler SPHardwareDataType | grep 'CPU Temperature'"
                        temp = os.popen(cmd).readline()
                        if temp:
                            return float(temp.split(':')[1].strip().replace('°C', ''))
                    except:
                        pass
                
                return 0.0
        except:
            return 0.0

    def _get_uptime(self) -> str:
        """Get system uptime"""
        return str(datetime.now() - self.boot_time)

    def _get_operating_mode(self) -> str:
        """Determine current operating mode"""
        # This would need proper implementation based on your robot's states
        return "standby"

    def _get_storage_info(self) -> Dict[str, float]:
        """Get storage space information"""
        disk = psutil.disk_usage('/')
        return {
            "total": disk.total / (1024**3),  # GB
            "used": disk.used / (1024**3),    # GB
            "free": disk.free / (1024**3)     # GB
        }

    def _get_network_strength(self) -> int:
        """Get network signal strength"""
        # This would need proper implementation
        return 100

    def _get_critical_services_status(self) -> Dict[str, str]:
        """Get status of critical services"""
        # Implement based on your critical services
        return {
            "main_service": "running",
            "camera_service": "running",
            "motor_service": "running"
        }

    def _get_system_errors(self) -> list:
        """Get system errors"""
        # Implement based on your error logging system
        return []

    def _get_hardware_warnings(self) -> list:
        """Get hardware warnings"""
        # Implement based on your hardware monitoring
        return []

    def _get_last_update_time(self) -> str:
        """Get last system update time"""
        # Implement based on your update system
        return datetime.now().isoformat()

    def _get_connected_peripherals(self) -> Dict[str, str]:
        """Get connected peripheral devices"""
        # Implement based on your peripheral detection system
        return {}

    def _get_network_config(self) -> Dict[str, str]:
        """Get network configuration"""
        return {
            "hostname": platform.node(),
            "interfaces": self._get_network_interfaces()
        }

    def _get_network_interfaces(self) -> Dict[str, Dict]:
        """Get network interfaces information"""
        interfaces = {}
        for iface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == 2:  # IPv4
                    interfaces[iface] = {
                        "ip": addr.address,
                        "netmask": addr.netmask
                    }
        return interfaces 