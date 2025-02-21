import 'dart:core';

class TaskModel {
  String? key;
  String? title;
  String? category;
  String? description;
  String? image;
  String? periority;
  String? time;
  String? date;
  String? show;
  int? progress;
  String? status;

  TaskModel(
      {required this.key,
      required this.time,
      required this.date,
      required this.periority,
      required this.description,
      required this.category,
      required this.title,
      required this.image,
      required this.show,
      required this.progress,
      required this.status});

  TaskModel.fromMap(Map<String, dynamic> res) {
    key = res['_id']?.toString();
    title = res['title'];
    category = res['category'];
    description = res['description'];
    image = res['image'];
    periority = res['priority'];
    show = 'yes';
    time = res['time'];
    date = res['date'];
    progress = res['progress'] as int?;
    status = res['status'];
  }

  Map<String, Object?> toMap() {
    return {
      'key': key,
      'title': title,
      'category': category,
      'description': description,
      'image': image,
      'periority': periority,
      'time': time,
      'date': date,
      'show': show,
      'status': status,
      'progress': progress,
    };
  }
}
