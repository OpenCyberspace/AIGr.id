import loguru
import enum
import os
import json
import traceback


class ErrorSeverity(enum.Enum):
    HIGH = 0
    MEDIUM = 1
    LOW = 2


IS_CONTAINER = int(os.getenv("CONTAINER", "0"))
lpath = "." if IS_CONTAINER == 0 else "/logs"


def get_default_config():
    return {
        "service_name": "dag-block-executor",
        "logging_path": lpath,
        "serialize": True,
        "enable_compression": False,
        "compression_value": None,
        "enable_log_rotation": False,
        "enable_error_callbacks": False,
        "rotation_value": "10MB",
        "use_verbose_mode": False
    }


def key_checker(data: dict, keys: list):
    dict_keys = list(data.keys())
    for key in keys:
        if key not in dict_keys:
            return False, key
    return True, None


class Logger__internal:

    def __init__(self, config: dict = None):
        self.logger = loguru.logger
        self.enable_callbacks_dispatch = False
        self.callbacks = {}
        self.config = {}
        self.service_name = None
        # self.set_config(config)

        self.custom_verbose_patcher = None
        self.custom_minimal_patcher = None

    def patch_verbose(self, record):
        custom_message = {
            "function": record['function'],
            "level": record['level'].name.lower(),
            "message": record['message'],
            "timestamp": record['time'].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "file": os.path.abspath(record['file'].path),
            "pid": record['process'].id,
            "process": record['process'].name,
            "tid": record['thread'].id,
            "thread": record['thread'].name,
            "language": "python"
        }

        custom_message.update(record['extra'])
        if 'exception' in custom_message:
            exception: Exception = custom_message['exception']
            custom_message['exception'] = str(custom_message['exception'])
            custom_message['exception_trace'] = ''.join(
                traceback.format_tb(exception.__traceback__)
            )

        record['extra']['serialized'] = json.dumps(custom_message)

    def patch_light(self, record):
        custom_message = {
            "message": record['message'],
            "timestamp": record['time'].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record['level'].name.lower()
        }

        # write extras
        custom_message.update(record['extra'])
        if 'exception' in custom_message:
            exception: Exception = custom_message['exception']
            custom_message['exception'] = str(exception)

        record['extra']['serialized'] = json.dumps(custom_message)

    def set_config(self, config: dict = None):

        try:

            if not config:
                config = get_default_config()
            # check keys against default config:
            default_keys = list(get_default_config().keys())
            default_keys.remove("rotation_value")
            ok, key = key_checker(config, default_keys)
            if not ok:
                raise Exception("Key {} not found".format(key))

            # check if logging_path exists:
            if not os.path.exists(config['logging_path']):
                raise Exception(
                        "Path {} does not exist".format(config['logging_path'])
                    )

            rotation_value = None
            # log rotation check
            if config['enable_log_rotation']:
                if 'rotation_config' not in config:
                    default = get_default_config()
                    rotation_value = default['rotation_value']
                else:
                    rotation_value = config['rotation_value']

            svc_name = config['service_name']
            # switch and path to verbose mode if enabled
            if config['serialize']:
                if config['use_verbose_mode']:
                    if self.custom_verbose_patcher:
                        self.logger = self.logger.patch(
                            self.custom_verbose_patcher
                        )
                    else:
                        self.logger = self.logger.patch(self.patch_verbose)
                else:
                    if self.custom_minimal_patcher:
                        self.logger = self.logger.patch(
                            self.custom_minimal_patcher
                        )
                    else:
                        self.logger = self.logger.patch(self.patch_light)

            compression_f = None
            if config['enable_compression']:
                compression_f = config['compression_value']

            # set config
            self.logger.add(
                sink=os.path.join(config['logging_path'], svc_name + ".json"),
                rotation=rotation_value,
                compression=compression_f,
                format="{extra[serialized]}"
            )

            # set callback dispatch enable/disable
            self.enable_callbacks_dispatch = config['enable_error_callbacks']
            self.config = config
            self.service_name = svc_name

        except Exception as e:
            # use default config in case of exceptions:
            print('Failed to parse logging config, using default', e)
            self.set_config(config=get_default_config())

    def info(self, message: str, extra: dict = {}):
        extra['service_name'] = self.service_name
        self.logger.opt(depth=2).info(
            message,
            **extra
        )

    def warning(self, message: str, extra: dict = {}):
        extra['service_name'] = self.service_name
        self.logger.opt(depth=2).warning(
            message,
            **extra
        )

    def error(self, message: str, extra: dict = {}):
        extra['service_name'] = self.service_name
        self.logger.opt(depth=2).error(
            message,
            **extra
        )

    def get_current_config(self):
        return self.config

    def get_logger_reference(self):
        # use this function to change logging references directly
        return self.logger


class AIOSLogger:

    def __init__(self, config=None):
        self.logger = Logger__internal()
        self.set_config(config)

    def register_callback(self, name, callback):
        self.logger.callbacks[name] = callback

    def remove_callback(self, name):
        if name in self.logger.callbacks:
            del self.logger.callbacks[name]

    def set_config(self, config=None):
        if type(config) == dict:
            self.logger.set_config(config)
        elif type(config) == str:
            if not os.path.exists(config):
                self.logger.set_config(
                    get_default_config()
                )
            else:
                self.logger.set_config(
                    json.load(open(config))
                )
        elif callable(config):
            config_data = config()
            if type(config_data) != dict:
                self.logger.set_config(get_default_config())
            else:
                self.logger.set_config(config_data)
        else:
            self.logger.set_config(get_default_config())

    def info(self, action: str, message: str, extras: dict = {}):
        extras['action'] = action
        self.logger.info(message, extras)

    def warning(self, action: str,
                message: str, extras: dict = {}, callback_name: str = None,
                exception: Exception = None, c_params: dict = {}):

        extras['action'] = action
        if exception:
            exception['exception'] = exception

        self.logger.warning(message, extras)

        # dispatch the callback
        if self.logger.enable_callbacks_dispatch and callback_name:
            if callback_name in self.logger.callbacks:
                self.logger.callbacks[callback_name](**c_params)

    def error(self, action: str, severity: ErrorSeverity,
              message: str, extras: dict = {}, callback_name: str = None,
              exception: Exception = None, c_params: dict = {}):

        extras['severity'] = severity.name
        extras['action'] = action
        if exception:
            extras['exception'] = exception

        self.logger.error(message, extras)

        # dispatch the callback
        if self.logger.enable_callbacks_dispatch and callback_name:
            if callback_name in self.logger.callbacks:
                self.logger.callbacks[callback_name](**c_params)

    def get_current_config(self):
        return self.logger.config

    def get_logger_reference(self):
        return self.logger.get_logger_reference()

    def set_custom_verbose_formatter(self, formatter_function):
        self.logger.custom_verbose_patcher = formatter_function

        # re-configure logger to bring changes into effect
        self.logger.set_config(self.logger.get_current_config())

    def set_custom_minimal_formatter(self, formatter_function):
        self.logger.custom_minimal_patcher = formatter_function

        # re-configure logger to bring changes into effect
        self.logger.set_config(self.logger.get_current_config())

    def unset_custom_verbose_formatter(self, formatter_function):
        self.logger.custom_verbose_patcher = None

        # re-configure logger to bring changes into effect
        self.logger.set_config(self.logger.get_current_config())

    def unset_custom_minimal_formatter(self, formatter_function):
        self.logger.custom_minimal_patcher = None

        # re-configure logger to bring changes into effect
        self.logger.set_config(self.logger.get_current_config())

    def i(self):
        return self.logger.logger
