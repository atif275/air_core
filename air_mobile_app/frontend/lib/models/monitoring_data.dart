class MonitoringData {
  final BasicStatus basicStatus;
  final SensorReadings sensorReadings;
  final MotorMetrics motorMetrics;
  final PerformanceMetrics performanceMetrics;

  MonitoringData({
    required this.basicStatus,
    required this.sensorReadings,
    required this.motorMetrics,
    required this.performanceMetrics,
  });

  factory MonitoringData.fromJson(Map<String, dynamic> json) {
    return MonitoringData(
      basicStatus: BasicStatus.fromJson(json['basic_status']),
      sensorReadings: SensorReadings.fromJson(json['sensor_readings']),
      motorMetrics: MotorMetrics.fromJson(json['motor_metrics']),
      performanceMetrics: PerformanceMetrics.fromJson(json['performance_metrics']),
    );
  }
}

class BasicStatus {
  final Battery battery;
  final double systemHealth;
  final String operatingTime;
  final Network network;

  BasicStatus({
    required this.battery,
    required this.systemHealth,
    required this.operatingTime,
    required this.network,
  });

  factory BasicStatus.fromJson(Map<String, dynamic> json) {
    return BasicStatus(
      battery: Battery.fromJson(json['battery']),
      systemHealth: json['system_health']?.toDouble() ?? 0.0,
      operatingTime: json['operating_time'] ?? '',
      network: Network.fromJson(json['network']),
    );
  }
}

class Battery {
  final double level;
  final bool powerPlugged;
  final double averageDrain;
  final String estimatedRemaining;

  Battery({
    required this.level,
    required this.powerPlugged,
    required this.averageDrain,
    required this.estimatedRemaining,
  });

  factory Battery.fromJson(Map<String, dynamic> json) {
    return Battery(
      level: json['level']?.toDouble() ?? 0.0,
      powerPlugged: json['power_plugged'] ?? false,
      averageDrain: json['average_drain']?.toDouble() ?? 0.0,
      estimatedRemaining: json['estimated_remaining'] ?? '',
    );
  }
}

class Network {
  final double latency;
  final String lastSync;

  Network({
    required this.latency,
    required this.lastSync,
  });

  factory Network.fromJson(Map<String, dynamic> json) {
    return Network(
      latency: json['latency']?.toDouble() ?? 0.0,
      lastSync: json['last_sync'] ?? '',
    );
  }
}

class SensorReadings {
  final double temperature;
  final double humidity;
  final String proximity;
  final String lightLevel;
  final String motionStatus;
  final String orientation;

  SensorReadings({
    required this.temperature,
    required this.humidity,
    required this.proximity,
    required this.lightLevel,
    required this.motionStatus,
    required this.orientation,
  });

  factory SensorReadings.fromJson(Map<String, dynamic> json) {
    return SensorReadings(
      temperature: json['temperature']?.toDouble() ?? 0.0,
      humidity: json['humidity']?.toDouble() ?? 0.0,
      proximity: json['proximity'] ?? '',
      lightLevel: json['light_level'] ?? '',
      motionStatus: json['motion_status'] ?? '',
      orientation: json['orientation'] ?? '',
    );
  }
}

class MotorMetrics {
  final double temperature;
  final double load;
  final double peakLoad;
  final double movementSpeed;

  MotorMetrics({
    required this.temperature,
    required this.load,
    required this.peakLoad,
    required this.movementSpeed,
  });

  factory MotorMetrics.fromJson(Map<String, dynamic> json) {
    return MotorMetrics(
      temperature: json['temperature']?.toDouble() ?? 0.0,
      load: json['load']?.toDouble() ?? 0.0,
      peakLoad: json['peak_load']?.toDouble() ?? 0.0,
      movementSpeed: json['movement_speed']?.toDouble() ?? 0.0,
    );
  }
}

class PerformanceMetrics {
  final Cpu cpu;
  final Memory memory;
  final Disk disk;

  PerformanceMetrics({
    required this.cpu,
    required this.memory,
    required this.disk,
  });

  factory PerformanceMetrics.fromJson(Map<String, dynamic> json) {
    return PerformanceMetrics(
      cpu: Cpu.fromJson(json['cpu']),
      memory: Memory.fromJson(json['memory']),
      disk: Disk.fromJson(json['disk']),
    );
  }
}

class Cpu {
  final double percent;
  final CpuFrequency frequency;
  final int count;

  Cpu({
    required this.percent,
    required this.frequency,
    required this.count,
  });

  factory Cpu.fromJson(Map<String, dynamic> json) {
    return Cpu(
      percent: json['percent']?.toDouble() ?? 0.0,
      frequency: CpuFrequency.fromJson(json['frequency']),
      count: json['count'] ?? 0,
    );
  }
}

class CpuFrequency {
  final double current;
  final double min;
  final double max;

  CpuFrequency({
    required this.current,
    required this.min,
    required this.max,
  });

  factory CpuFrequency.fromJson(Map<String, dynamic> json) {
    return CpuFrequency(
      current: json['current']?.toDouble() ?? 0.0,
      min: json['min']?.toDouble() ?? 0.0,
      max: json['max']?.toDouble() ?? 0.0,
    );
  }
}

class Memory {
  final int total;
  final int available;
  final double percent;

  Memory({
    required this.total,
    required this.available,
    required this.percent,
  });

  factory Memory.fromJson(Map<String, dynamic> json) {
    return Memory(
      total: json['total'] ?? 0,
      available: json['available'] ?? 0,
      percent: json['percent']?.toDouble() ?? 0.0,
    );
  }
}

class Disk {
  final int total;
  final int used;
  final int free;
  final double percent;

  Disk({
    required this.total,
    required this.used,
    required this.free,
    required this.percent,
  });

  factory Disk.fromJson(Map<String, dynamic> json) {
    return Disk(
      total: json['total'] ?? 0,
      used: json['used'] ?? 0,
      free: json['free'] ?? 0,
      percent: json['percent']?.toDouble() ?? 0.0,
    );
  }
}

// Add other classes (BasicStatus, SensorReadings, etc.) with their fromJson methods 