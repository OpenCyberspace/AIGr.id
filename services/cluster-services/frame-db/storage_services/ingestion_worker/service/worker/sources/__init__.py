from .test import TestSource
from .fs import FsSource, fs_validator
from .redis_source import RedisSource, redis_source_validator
from .kafka_source import KafkaSource, kafka_source_validator
#structure = <source_name, (Class, validator)

sources_list = {
    "redis" : (RedisSource, redis_source_validator),
    "kafka" : (KafkaSource, kafka_source_validator),
    "fs" : (FsSource, fs_validator),
    "test" : (TestSource, None)
}