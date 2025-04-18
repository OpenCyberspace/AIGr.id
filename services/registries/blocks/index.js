require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const blockRoutes = require('./src/router'); 

const app = express();
const PORT = process.env.PORT || 3001;

const mongoHostUrl = process.env.MONGO_HOST_URL || "mongodb://localhost:27017/blocks";
const mongoUsername = process.env.MONGO_USERNAME;
const mongoPassword = process.env.MONGO_PASSWORD;
const mongoDbName = process.env.MONGO_DBNAME;

const mongoUrl = mongoHostUrl

mongoose.connect(mongoUrl, { useNewUrlParser: true, useUnifiedTopology: true })
    .then(() => console.log('MongoDB connected...'))
    .catch(err => console.log(err));

app.use(express.json());
app.use('/', blockRoutes);

app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});