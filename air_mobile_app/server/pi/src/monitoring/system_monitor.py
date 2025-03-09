import psutil
import platform
from datetime import datetime, timedelta
import os
from typing import Dict, Any
import random  # For simulated values
import logging
import subprocess

logger = logging.getLogger(__name__)

class SystemMonitor:
    def __init__(self):
        self.boot_time = datetime.fromtimestamp(psutil.boot_time())
        self.is_monitoring = True
        self.last_sync_time = datetime.now()
        self.last_battery_level = None
        self.last_battery_time = None
        self.battery_drain_rate = None
        self.is_raspberry_pi = self._is_raspberry_pi()
        
    def _is_raspberry_pi(self) -> bool:
        """Check if running on Raspberry Pi"""
        try:
            with open('/proc/device-tree/model', 'r') as f:
                return 'Raspberry Pi' in f.read()
        except:
            return False

    def _format_uptime(self, delta):
        """Format timedelta to 'Xd Yh Zm'"""
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        return f"{days}d {hours}h {minutes}m"

    def _get_battery_info(self) -> Dict[str, Any]:
        """Get battery information with numeric values"""
        try:
            battery = psutil.sensors_battery()
            if battery:
                level = round(battery.percent)  # Convert to number
                drain_rate = self.battery_drain_rate if self.battery_drain_rate else 0.0
                remaining = str(timedelta(seconds=battery.secsleft)) if battery.secsleft > 0 else "0:00"
                return {
                    "level": level,  # number (0-100)
                    "power_plugged": battery.power_plugged,  # boolean
                    "average_drain": drain_rate,  # number (percent/hour)
                    "estimated_remaining": remaining  # HH:MM format
                }
        except Exception as e:
            logger.error(f"Battery info error: {e}")
        
        return {
            "level": 0,
            "power_plugged": False,
            "average_drain": 0.0,
            "estimated_remaining": "0:00"
        }

    def _get_cpu_temperature(self) -> float:
        """Get CPU temperature as number"""
        try:
            if platform.system() == 'Linux':
                if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                    with open('/sys/class/thermal/thermal_zone0/temp') as f:
                        return round(float(f.read().strip()) / 1000, 1)
                elif self.is_raspberry_pi:
                    try:
                        temp = subprocess.check_output(['vcgencmd', 'measure_temp'])
                        return round(float(temp.decode().split('=')[1].split("'")[0]), 1)
                    except:
                        return 0.0
            return 0.0
        except Exception as e:
            logger.error(f"Temperature reading error: {e}")
            return 0.0

    def get_sensor_readings(self) -> Dict[str, Any]:
        """Get sensor readings with numeric values"""
        return {
            "temperature": self._get_cpu_temperature(),  # Already returns float
            "humidity": 45.0,  # float instead of string
            "proximity": "Clear",  # Keep as string (status)
            "light_level": "Normal",  # Keep as string (status)
            "motion_status": "Stationary",  # Keep as string (status)
            "orientation": "Upright"  # Keep as string (status)
        }

    def get_motor_metrics(self) -> Dict[str, Any]:
        """Get motor metrics with numeric values"""
        return {
            "temperature": self._get_cpu_temperature(),  # Already returns float
            "load": 45.0,  # float instead of string
            "peak_load": 78.0,  # float instead of string
            "movement_speed": 1.2  # Already float
        }

    def get_basic_status(self) -> Dict[str, Any]:
        """Get basic system status with numeric values"""
        battery = self._get_battery_info()
        uptime = datetime.now() - self.boot_time
        latency = self._get_network_latency()  # Now returns float
        
        return {
            "battery": {
                "level": float(battery["level"]),  # Ensure float
                "power_plugged": battery["power_plugged"],
                "average_drain": float(battery["average_drain"]),  # Ensure float
                "estimated_remaining": battery["estimated_remaining"]  # Keep time format as string
            },
            "system_health": self._calculate_system_health(),  # Now returns float
            "operating_time": self._format_uptime(uptime),  # Keep time format as string
            "network": {
                "latency": round(latency, 1),  # Now properly rounds float
                "last_sync": self.last_sync_time.strftime("%Y-%m-%d %H:%M")  # Keep time format as string
            }
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics with numeric values"""
        cpu_freq = self._get_cpu_frequency()
        return {
            "cpu": {
                "percent": round(float(psutil.cpu_percent(interval=None)), 1),  # Ensure float
                "frequency": {
                    "current": float(cpu_freq["current"]),  # Ensure float
                    "min": float(cpu_freq["min"]),  # Ensure float
                    "max": float(cpu_freq["max"])  # Ensure float
                },
                "count": psutil.cpu_count()
            },
            "memory": {
                "total": int(psutil.virtual_memory().total),  # Ensure int for bytes
                "available": int(psutil.virtual_memory().available),  # Ensure int for bytes
                "percent": round(float(psutil.virtual_memory().percent), 1)  # Ensure float
            },
            "disk": {
                "total": int(psutil.disk_usage('/').total),  # Ensure int for bytes
                "used": int(psutil.disk_usage('/').used),  # Ensure int for bytes
                "free": int(psutil.disk_usage('/').free),  # Ensure int for bytes
                "percent": round(float(psutil.disk_usage('/').percent), 1)  # Ensure float
            }
        }

    def get_full_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "basic_status": self.get_basic_status(),
            "sensor_readings": self.get_sensor_readings(),
            "motor_metrics": self.get_motor_metrics(),
            "performance_metrics": self.get_performance_metrics(),
            "timestamp": datetime.now().isoformat()
        }

    def get_health_metrics(self) -> Dict[str, Any]:
        """Get detailed health metrics"""
        return {
            "cpu": {
                "percent": psutil.cpu_percent(interval=None),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
                "count": psutil.cpu_count()
            },
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage('/')._asdict(),
            "temperature": self._get_cpu_temperature(),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_diagnostic_info(self) -> Dict[str, Any]:
        """Get system diagnostic information"""
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "network": self._get_network_info(),
            "timestamp": datetime.now().isoformat()
        }

    def _calculate_system_health(self) -> float:
        """Calculate overall system health based on various metrics"""
        try:
            # Get CPU, memory, and temperature metrics
            cpu_percent = float(psutil.cpu_percent())
            memory_percent = float(psutil.virtual_memory().percent)
            temp = self._get_cpu_temperature()  # Already returns float
            
            # Define weight for each metric
            cpu_weight = 0.3
            memory_weight = 0.3
            temp_weight = 0.4
            
            # Calculate weighted health score
            cpu_health = max(0, 100 - cpu_percent)
            memory_health = max(0, 100 - memory_percent)
            temp_health = max(0, 100 - (temp * 100 / 80))  # Assuming 80°C is max safe temp
            
            health_score = (
                cpu_health * cpu_weight +
                memory_health * memory_weight +
                temp_health * temp_weight
            )
            
            return round(health_score, 1)  # Return float instead of string
            
        except Exception as e:
            logger.error(f"Error calculating system health: {e}")
            return 85.0  # Return float default value

    def _get_cpu_frequency(self) -> Dict[str, float]:
        """Get CPU frequency information safely"""
        try:
            if self.is_raspberry_pi:
                # Raspberry Pi specific method
                with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq') as f:
                    current = float(f.read().strip()) / 1000  # Convert to MHz
                with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq') as f:
                    min_freq = float(f.read().strip()) / 1000
                with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq') as f:
                    max_freq = float(f.read().strip()) / 1000
                return {
                    "current": round(current, 2),
                    "min": round(min_freq, 2),
                    "max": round(max_freq, 2)
                }
            else:
                # Try psutil first
                cpu_freq = psutil.cpu_freq()
                if cpu_freq:
                    return {
                        "current": round(cpu_freq.current, 2),
                        "min": round(cpu_freq.min, 2),
                        "max": round(cpu_freq.max, 2)
                    }
                
                # Fallback values
                return {
                    "current": 1000.0,  # 1 GHz
                    "min": 800.0,      # 800 MHz
                    "max": 1200.0      # 1.2 GHz
                }
                
        except Exception as e:
            logger.debug(f"Could not get CPU frequency: {e}")
            # Return reasonable defaults if unable to get actual values
            return {
                "current": 1000.0,  # 1 GHz
                "min": 800.0,      # 800 MHz
                "max": 1200.0      # 1.2 GHz
            }

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

    def _get_temperature(self) -> Dict[str, float]:
        """Get system temperature if available"""
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                return {sensor: temp.current for sensor, readings in temps.items() 
                       for temp in readings}
        except:
            pass
        return {}

    def _get_network_info(self) -> Dict[str, Any]:
        """Get network interface information"""
        try:
            return {
                interface: addresses._asdict() 
                for interface, addresses in psutil.net_if_stats().items()
            }
        except:
            return {}

    def _get_network_latency(self) -> float:
        """Calculate network latency"""
        try:
            # Ping Google's DNS server
            if platform.system() == "Windows":
                ping_cmd = ['ping', '-n', '1', '8.8.8.8']
            else:
                ping_cmd = ['ping', '-c', '1', '8.8.8.8']
            
            result = subprocess.run(ping_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                if platform.system() == "Windows":
                    time_str = result.stdout.split("Average = ")[-1].split("ms")[0]
                else:
                    time_str = result.stdout.split("time=")[-1].split(" ms")[0]
                return float(time_str)
            return 0.0
        except:
            return 0.0

    def stop_monitoring(self):
        """Stop monitoring - cleanup method"""
        self.is_monitoring = False 