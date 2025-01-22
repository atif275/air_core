const mongoose = require('mongoose');
const dotenv = require('dotenv');
const Task = require('../models/TaskModel'); // Import the Task model

dotenv.config(); // Load environment variables

// Connect to MongoDB
mongoose.connect(process.env.MONGO_URI, {
    useNewUrlParser: true,
    useUnifiedTopology: true
}).then(() => console.log('✅ Database connected for seeding'))
  .catch((error) => console.log('❌ Database connection error:', error));

// Corrected dummy task data
const dummyTasks = [
    {
        title: "Complete Backend API",
        description: "Finish the CRUD operations for the tasks API",
        category: "Work",
        priority: "High",
        progress: 50,
        date: "2025-01-15",
        time: "10:00 AM",
        image: "assets/images/task1.jpg",
        status: "In Progress"  // Updated
    },
    {
        title: "UI Design Update",
        description: "Revamp the existing UI components",
        category: "Design",
        priority: "Medium",
        progress: 30,
        date: "2025-01-20",
        time: "02:00 PM",
        image: "assets/images/task2.jpg",
        status: "Pending"  // Updated
    },
    {
        title: "Testing and Bug Fixes",
        description: "Conduct thorough testing and fix reported bugs",
        category: "QA",
        priority: "Low",
        progress: 70,
        date: "2025-01-22",
        time: "01:00 PM",
        image: "assets/images/task3.jpg",
        status: "Completed"  // Updated
    }
];


// Seed function
const seedTasks = async () => {
    try {
        await Task.deleteMany();  // Clear existing data
        await Task.insertMany(dummyTasks);
        console.log('✅ Dummy tasks added successfully');
        mongoose.connection.close();
    } catch (error) {
        console.error('❌ Error while seeding tasks:', error);
        mongoose.connection.close();
    }
};

seedTasks();
