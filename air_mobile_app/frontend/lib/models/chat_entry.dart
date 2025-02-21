class ChatEntry {
  final String text;
  final DateTime timestamp;
  final bool isUserMessage;
  final String language;
  final double silenceDuration; // in seconds

  ChatEntry({
    required this.text,
    required this.timestamp,
    required this.isUserMessage,
    this.language = 'en',
    this.silenceDuration = 0.0,
  });

  Map<String, dynamic> toJson() => {
    'text': text,
    'timestamp': timestamp.toIso8601String(),
    'isUserMessage': isUserMessage,
    'language': language,
    'silenceDuration': silenceDuration,
  };

  factory ChatEntry.fromJson(Map<String, dynamic> json) => ChatEntry(
    text: json['text'],
    timestamp: DateTime.parse(json['timestamp']),
    isUserMessage: json['isUserMessage'],
    language: json['language'],
    silenceDuration: json['silenceDuration'],
  );
} 