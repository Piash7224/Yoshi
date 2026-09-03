const express = require('express');
const cors = require('cors');
const mongoose = require('mongoose');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;
const MONGODB_URI = process.env.MONGODB_URI;

// Middleware
app.use(cors());
app.use(express.json());

console.log('Attempting to connect to MongoDB...');

// Database Connection with 5-second timeout safety
mongoose.connect(MONGODB_URI, {
  serverSelectionTimeoutMS: 5000
})
  .then(() => console.log('MongoDB connected successfully!'))
  .catch((err) => {
    console.error('!!! MongoDB connection error !!!');
    console.error(err.message);
  });

// Health-check endpoint
app.get('/api/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'Backend skeleton is running perfectly.' });
});

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
