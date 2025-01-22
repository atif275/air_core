const mongoose = require('mongoose');

const TaskSchema = new mongoose.Schema({
    title: { type: String, required: true },
    description: String,
    category: String,
    priority: { type: String, enum: ['Low', 'Medium', 'High'], required: true },
    progress: { type: Number, default: 0 },
    date: String,
    time: String,
    image: String,
    status: { type: String, enum: ['Pending', 'In Progress', 'Completed'], default: 'Pending' }
},{ collection: 'Task' });

const Task = mongoose.model('Task', TaskSchema);
module.exports = Task;
