const bunyan = require('./b')
const fs = require('fs')
const path = require('path')

const ErrorSeverityHigh = "HIGH"
const ErrorSeverityMedium = "MEDIUM"
const ErrorSeverityLow = "LOW"

const defaultConfig = {
    "service_name": "testing_service",
    "logging_path": ".",
    "serialize": true,
    "enable_compression": false,
    "compression_value": null,
    "enable_log_rotation": false,
    "enable_error_callbacks": false,
    "rotation_value": "10MB",
    "use_verbose_mode": true
}

class AiosLogger {
    constructor(processName, config) {
        if (typeof config === 'string') {

            if (config === 'default') {
                config = defaultConfig
            } else {
                config = JSON.parse(fs.readFileSync(config).toString())
            }
        }

        this.config = config
        this.logger = null

        this.verboseMode = false
        this.callbackMap = {}

        this.setConfig()

        this.pid = process.pid
        this.processName = processName

        this.tid = 0
        this.thread = "MainThread"
        this.language = "js"
    }

    configStream(config) {
        if (config.enable_log_rotation) {
            return {
                type: 'rotating-file',
                path: path.join(config.logging_path, `${config.service_name}.json`),
                period: config.rotation_value
            }
        } else {
            return {
                type: 'file',
                path: path.join(config.logging_path, `${config.service_name}.json`)
            }
        }
    }

    setConfig(config) {
        if (!config) {
            config = this.config
        }

        if (typeof config === 'string') {
            if (config === 'default') {
                config = defaultConfig
            } else {
                config = fs.readFileSync(config).toJSON()
            }
        }

        console.log(config)

        const stream_config = this.configStream(config)
        //change logger as per the config
        this.logger = bunyan.createLogger({
            name: config.service_name,
            streams: [stream_config],
            level: "info",
            serializers: { err: bunyan.stdSerializers.err },
            src: true
        })
    }

    error(message, err, extras, severity, cb, cb_params) {
        if (this.logger) {

            extras['err'] = err
            extras['severity'] = severity
            extras['pid'] = this.pid
            extras['process'] = this.processName
            extras['tid'] = this.tid
            extras['thread'] = this.thread
            extras['language'] = this.language
            extras['service_name'] = this.config.service_name
            extras['l'] = 'error'

            this.logger.error(extras, message)
        }

        if (this.cb && this.config.enable_error_callbacks) {
            const callback = this.callbackMap[cb]
            if (callback) {
                callback(cb_params)
            }
        }
    }

    info(message, extras) {
        if (this.logger) {
            extras['pid'] = this.pid
            extras['process'] = this.processName
            extras['tid'] = this.tid
            extras['thread'] = this.thread
            extras['language'] = this.language
            extras['service_name'] = this.config.service_name
            extras['l'] = 'info'

            this.logger.info(extras, message)
        }
    }

    warning(message, extras, cb, cb_params) {
        if (this.logger) {
            extras['pid'] = this.pid
            extras['process'] = this.processName
            extras['tid'] = this.tid
            extras['thread'] = this.thread
            extras['language'] = this.language
            extras['service_name'] = this.config.service_name
            extras['l'] = 'warning'

            this.logger.warn(extras, message)
        }

        if (this.cb && this.config.enable_error_callbacks) {
            const callback = this.callbackMap[cb]
            if (callback) {
                callback(cb_params)
            }
        }
    }

    registerCallback(name, func) {
        this.callbackMap[name] = func
    }

    unregisterCallback(name) {
        if (this.callbackMap[name]) {
            delete this.callbackMap[name]
        }
    }

    i() {
        return this.logger
    }
}

module.exports.AiosLogger = AiosLogger