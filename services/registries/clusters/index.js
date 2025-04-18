const express = require('express');
const mongoose = require('mongoose');
const clusterRoutes = require('./src/router');
const dotenv = require('dotenv');

// Load environment variables from .env file
dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

// Middleware to parse JSON
app.use(express.json());

// Construct MongoDB URI
const mongoUrl = process.env.MONGO_URL;
const mongoUser = process.env.MONGO_USER;
const mongoPass = process.env.MONGO_PASS;

// Options for mongoose connect
const mongoOptions = {};

// Add user and password to options if provided
if (mongoUser && mongoPass) {
    mongoOptions.auth = {
        user: mongoUser,
        password: mongoPass,
    };
}

// Connect to the MongoDB database
mongoose.connect(mongoUrl, mongoOptions)
    .then(() => {
        console.log('Connected to MongoDB');
    })
    .catch(err => {
        console.error('Error connecting to MongoDB', err);
    });

// Use the cluster routes
app.use('/', clusterRoutes);

// Start the server
app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
});
