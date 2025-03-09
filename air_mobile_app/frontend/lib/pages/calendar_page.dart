import 'package:flutter/material.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:intl/intl.dart';

class CalendarPage extends StatefulWidget {
  const CalendarPage({Key? key}) : super(key: key);

  @override
  _CalendarPageState createState() => _CalendarPageState();
}

class _CalendarPageState extends State<CalendarPage> {
  CalendarFormat _calendarFormat = CalendarFormat.month;
  DateTime _focusedDay = DateTime.now();
  DateTime? _selectedDay;
  Map<DateTime, List<Event>> _events = {};

  @override
  void initState() {
    super.initState();
    _selectedDay = _focusedDay;
    // Add some sample events
    _events = {
      DateTime.now(): [
        Event('Daily Check-up', 'Routine system diagnostics', EventType.maintenance),
        Event('Voice Training', 'Scheduled voice model update', EventType.training),
      ],
      DateTime.now().add(const Duration(days: 1)): [
        Event('Battery Maintenance', 'Scheduled battery check', EventType.maintenance),
      ],
      DateTime.now().add(const Duration(days: 3)): [
        Event('Software Update', 'System software update scheduled', EventType.system),
      ],
    };
  }

  List<Event> _getEventsForDay(DateTime day) {
    return _events[DateTime(day.year, day.month, day.day)] ?? [];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AIR Calendar'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => _showAddEventDialog(context),
          ),
        ],
      ),
      body: Column(
        children: [
          TableCalendar(
            firstDay: DateTime.utc(2024, 1, 1),
            lastDay: DateTime.utc(2025, 12, 31),
            focusedDay: _focusedDay,
            calendarFormat: _calendarFormat,
            selectedDayPredicate: (day) {
              return isSameDay(_selectedDay, day);
            },
            eventLoader: _getEventsForDay,
            onDaySelected: (selectedDay, focusedDay) {
              setState(() {
                _selectedDay = selectedDay;
                _focusedDay = focusedDay;
              });
            },
            onFormatChanged: (format) {
              setState(() {
                _calendarFormat = format;
              });
            },
            calendarStyle: const CalendarStyle(
              markersMaxCount: 3,
              markerDecoration: BoxDecoration(
                color: Colors.blue,
                shape: BoxShape.circle,
              ),
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: _buildEventList(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddEventDialog(context),
        child: const Icon(Icons.add),
        tooltip: 'Add Event',
      ),
    );
  }

  Widget _buildEventList() {
    final events = _getEventsForDay(_selectedDay!);

    if (events.isEmpty) {
      return const Center(
        child: Text('No events scheduled for this day'),
      );
    }

    return ListView.builder(
      itemCount: events.length,
      itemBuilder: (context, index) {
        final event = events[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          child: ListTile(
            leading: Icon(
              event.type.icon,
              color: event.type.color,
            ),
            title: Text(event.title),
            subtitle: Text(event.description),
            trailing: IconButton(
              icon: const Icon(Icons.delete),
              onPressed: () {
                setState(() {
                  _events[_selectedDay!]?.remove(event);
                  if (_events[_selectedDay!]?.isEmpty ?? false) {
                    _events.remove(_selectedDay!);
                  }
                });
              },
            ),
          ),
        );
      },
    );
  }

  Future<void> _showAddEventDialog(BuildContext context) async {
    final titleController = TextEditingController();
    final descriptionController = TextEditingController();
    EventType selectedType = EventType.general;

    await showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add Event'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: titleController,
                decoration: const InputDecoration(
                  labelText: 'Event Title',
                ),
              ),
              TextField(
                controller: descriptionController,
                decoration: const InputDecoration(
                  labelText: 'Event Description',
                ),
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<EventType>(
                value: selectedType,
                decoration: const InputDecoration(
                  labelText: 'Event Type',
                ),
                items: EventType.values.map((type) {
                  return DropdownMenuItem(
                    value: type,
                    child: Row(
                      children: [
                        Icon(type.icon, color: type.color),
                        const SizedBox(width: 8),
                        Text(type.name),
                      ],
                    ),
                  );
                }).toList(),
                onChanged: (value) {
                  selectedType = value!;
                },
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              if (titleController.text.isNotEmpty) {
                setState(() {
                  final events = _events[_selectedDay!] ?? [];
                  events.add(Event(
                    titleController.text,
                    descriptionController.text,
                    selectedType,
                  ));
                  _events[_selectedDay!] = events;
                });
                Navigator.pop(context);
              }
            },
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }
}

class Event {
  final String title;
  final String description;
  final EventType type;

  Event(this.title, this.description, this.type);
}

enum EventType {
  general(Icons.event, Colors.blue),
  maintenance(Icons.build, Colors.orange),
  training(Icons.school, Colors.green),
  system(Icons.computer, Colors.purple),
  task(Icons.task, Colors.red);

  final IconData icon;
  final Color color;

  const EventType(this.icon, this.color);
} 