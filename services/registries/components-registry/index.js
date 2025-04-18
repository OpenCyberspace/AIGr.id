const express = require('express')
const dotenv = require('dotenv')
const mongoose = require('mongoose')
const cors_fn = require('cors')
const bp = require('body-parser')
const logger = require('./aios_logger')

const routes = require('./src/routes')


// initialize logger
const loggingPath = (parseInt(process.env.CONTAINER) !== 1) ? "./log_config.json" : "./log_config_container.json"

const logging = new logger.AiosLogger('index.js', loggingPath)

const connectToDB = (url) => {
    mongoose.connect(url, {
        useNewUrlParser : true, 
        useUnifiedTopology : true,
        autoIndex: true,
        reconnectTries: parseInt(process.env.MAX_RETRIES) || 10,
        reconnectInterval: parseInt(process.env.RECONNECT_INTERVAL) || 500,
        bufferMaxEntries: parseInt(process.env.BUFFER_MAX_RETRIES) || 0,
        poolSize: parseInt(process.env.POOL_SIZE) || 10,
        keepAlive: parseInt(process.env.KEEP_ALIVE_TIME) || 120
    })

    mongoose.set('useCreateIndex', true);

    const db = mongoose.connection
    
    db.on('error', (err) => {
        console.log(err)
        logging.error("Failed to connect to DB", {err : err, action: "db_connect"})
    })
}

const prepareMongoURL = () => {
    if (process.env.DB_URL) {
        return process.env.MONGO_URL
    }

    // get username and password
    const username = process.env.MONGO_USERNAME
    const password = process.env.MONGO_PASSWORD

    if ((!username) || (!password)) {
        return process.env.MONF
    } else {
        return `mongodb://${username}:${password}@${process.env.MONGO_HOST}/admin?authSource=admin`
    }
}


//read env variables:
if (parseInt(process.env.CONTAINER) !== 1) {
    dotenv.config()
}


//connect to mongodb
connectToDB(prepareMongoURL())

const ql_router = require('./gql_router').ql_router

//REST PORT
const REST_API_PORT = process.env.REST_API_PORT || 4000

const app = express()
app.use(cors_fn())
app.use(bp.json())
app.use((req, resp, next) => {
    logging.info("Request logging", {
        "action": "request_logging",
        "request_data" : {
            "headers": req.headers,
            "httpVersion": req.httpVersion,
            "hostName": req.hostname,
            "ip" : req.ip
        }
    })

    next()
})

//register the health endpoint
app.get("/health", (req, resp) => {
    return resp.status(200).json({
        status: 'ok',
        success: true
    })
})

//register the route
app.use("/api", routes.componentRouter)

//register graphQL router
app.use("/gql", ql_router)

//run the server
app.listen(REST_API_PORT, '0.0.0.0', (err) => {
    if (err) {
        logging.error("Failed to start server", {
            err : err,
            action: "server_start",
            port: REST_API_PORT
        })
    } else {
        logging.info(`Started REST server on 0.0.0.0:${REST_API_PORT}`, {
            action: "server_start",
            port: REST_API_PORT
        })
    }
})