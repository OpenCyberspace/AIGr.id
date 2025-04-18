from .env import get_env_settings, exit_on_failure, exit_on_success
from .notifier import wrap_notify_failure, wrap_notify_success
from .video_meta import DiscoverVideo
import shlex
import time

import json
import os
import subprocess

TIMEOUT_SIGINT_SUCCESS = 124

env_settings = get_env_settings()

import logging
logging.basicConfig(level = logging.INFO)
logging = logging.getLogger("MainLogger")

validation_keys = [('source_id', str), ('operating_mode', str, ['live', 'batch']), ('url', str), ('fps', str), ('mode', str, ['live', 'video']), ('use_gpu', bool)]
supported_containers = ['mp4', 'mkv', 'flv']

c_map = {
    "mp4" : "qtdemux",
    "mkv" : "matroskademux",
    "flv" : "flvdemux"
}

def wrap_fail(errData):
    wrap_notify_failure(errData)
    exit_on_failure()

def wrap_complete(succData):
    wrap_notify_success(succData)
    exit_on_failure()


def __validate_source_data(data):

    for key in validation_keys:
        key_name, key_type = key[0], key[1]
        if not key_name in data or type(data[key_name]) != key_type: 
            return False, "Key {} missing in source data".format(key_name)
        
        if len(key) > 2:
            #check for category
            val =  data[key_name]
            if val not in key[2]:
                return False, "Key {} has improper value {} supported values are : {}".format(key_name, val, key[2])
    
    if (data['mode'] == 'video') and ((not 'container' in data) or (data['container'] not in supported_containers)):
        return False, "Supported container types not provided container format in supported containers {}".format(supported_containers)
    
    logging.info("Validation passed")

    #check nv-codecs enabled, if not, fallback to CPU mode
    has_env_codecs = os.getenv("NV_CODECS_ENABLED", "No").lower()
    #convert to bool
    has_env_codecs = True if has_env_codecs == "yes" else False
    if (not has_env_codecs) and (data['use_gpu']):
        logging.warning("The worker is not compiled with NVIDIA plugins or not running in a GPU-enabled environment")
        logging.warning("Falling back to CPU mode")

        #disable GPU mode, this will make pipeline to use ffmpeg plugins instead of NV-Codecs
        data['use_gpu'] = False

    return True, "Validation passed"

def run_task():

    try:
        data = env_settings.source_data
        
        source_settings = json.loads(data)

        print(source_settings)
        
        ret, message = __validate_source_data(source_settings)
        if not ret:
            logging.error(message)
            wrap_fail({"errData" : message})
        

        #launch source launcher based on source
        if source_settings['mode'] == 'video':
            StoredVideoDecoder(source_settings).run_pipeline()
        else:
            LiveDecoder(source_settings).run_pipeline()

    except Exception as e:
        logging.error(e)
        wrap_fail({"errData" : "source data is not json decodable"})


class LiveDecoder:

    def __init__(self, settings):
        
        self.source_id = settings['source_id']
        self.settings = settings
    
    def create_decoder(self, source_uri, settings : dict):

        units  = []
        
        source_unit = "rtspsrc location=\"{}\"".format(source_uri)
        units.append(source_unit)

        depayer = None

        decoder_unit = None

        #get video metadata and do processing
        result, video_meta = DiscoverVideo.GetVideoData(source_uri)
        if not result:
            return False, video_meta

        
        logging.info("Video metadata {}".format(video_meta))
        
        if video_meta['codec_name'] == 'h264' :

            depayer = "rtph264depay"

            if settings['use_gpu']:
                decoder_unit = "h264parse ! nvh264dec ! videorate"
            else:
                decoder_unit = "h264parse ! avdec_h264 ! videorate"
        
        elif video_meta['codec_name'] == "hevc":

            depayer = "rtph265depay"

            if settings['use_gpu']:
                decoder_unit = "h265parse ! nvh265dec ! videorate"
            else:
                decoder_unit = "h265parse ! avdec_h265 ! videorate"
        else:
            return False, "Unsupported video format {}".format(video_meta['codec_name'])
        
        units.extend([depayer, decoder_unit])

        if 'use_custom_ts' in settings and settings['use_custom_ts']:
            units.append("timestamper")

        if ('width' in settings  or 'height' in settings) :
            scaler = "videoscale"
            units.append(scaler)
        
        #fps and video settings
        caps = "\"video/x-raw"
        if settings['fps'] != "0/0":
            caps = "{}, framerate=(fraction){}".format(caps, settings['fps'])
        
        if 'width' in settings and type(settings['width']) == int:
            caps = "{}, width={}".format(caps, settings['width'])
        
        if 'height' in settings and type(settings['height']) == int:
            caps = "{}, height={}".format(caps, settings['height'])
        

        caps = "{}\"".format(caps)

        units.append(caps)

        
        #generated a metadata, check metadata
        return True, units


    def create_encoder(self, settings):
        
        jpeg_encoder = "jpegenc"
        if 'quality' in settings and type(settings['quality']) == int:
            jpeg_encoder = "{} quality={}".format(jpeg_encoder, settings['quality'])
        
        #sink configuration
        sink = "tidbsink"

        if settings['operating_mode'] == 'live':
            sink = "framedbsink"

        return  True, [jpeg_encoder, sink]

    def parse_pipeline(self):
        

        ret_dec, decoder_units = self.create_decoder(self.settings['url'], self.settings)
        if not ret_dec:
            return False, decoder_units

        ret_enc, encoder_units = self.create_encoder(self.settings)
        if not ret_enc:
            return False, encoder_units

        return True, [*decoder_units, *encoder_units]

    def __attach_units(self, units):

        units = " ! ".join(units)
        return units

    def __live_operator(self, pipeline):

        max_tries = 100
        tries = 0

        buffer_output = {}

        #live source never exists, kill the job or push back suspend
        while True:

            process_string = "gst-launch-1.0 {}".format(pipeline)
            child = subprocess.Popen(process_string, shell = True, stdout = subprocess.PIPE,  stderr = subprocess.PIPE)
            stream_output = child.communicate()[0]

            ret_code = child.returncode

            stream_string = str(stream_output, "utf-8")

            print(stream_string)

            if ret_code != 0:
                tries +=1

                buffer_output['try{}'.format(tries)] = stream_string
                if tries > max_tries:
                    print('Process failed for all {} times, exiting'.format(max_tries))
                    logging.error("process failed")
                    wrap_fail({"errData" : "failed to run task", "log" : buffer_output})
            else:
                print('finished successfully')
                logging.info("Decoding finished successfully")
                wrap_complete({"info" : "decoding finished", "log" : buffer_output})


    def run_pipeline(self):

        try:
            ret, pipeline_uints = self.parse_pipeline()
            if not ret:
                logging.error(pipeline_uints)
                wrap_fail({"errData" : pipeline_uints})
            
            #generate the shelx command:
            pipeline = self.__attach_units(pipeline_uints)

            if self.settings['operating_mode'] == 'live':
                logging.info("Running live operator")
                self.__live_operator(pipeline)

            #run the process:
            process = "gst-launch-1.0 {}".format(pipeline)

            logging.info("Running pipeline " + process)

            #launch a subprocess:
            duration = self.settings['duration']
            remaining_duration = duration

            outputs = {}
            tries = 0

            while remaining_duration > 0 :
                remaining_duration = int(remaining_duration)

                #work until there is still time
                process_timeouts = "timeout -s SIGINT {} {}".format(remaining_duration, process)

                st = time.time()
                child_handle = subprocess.Popen(process_timeouts, shell = True, stdout = subprocess.PIPE)
                output = child_handle.communicate()[0]
                exitcode = child_handle.returncode
                et = time.time()

                sub_time = et - st

                output_str = str(output, "utf-8")
                print(output_str, exitcode)

                outputs["try_{}".format(tries + 1)] = output_str

                if exitcode == TIMEOUT_SIGINT_SUCCESS:
                    logging.info("Process completed successfully")
                    wrap_complete({"message" : "Completed execution", "logs" : outputs})
                else:
                    tries = tries + 1

                    #avoid infinite looping core usage
                    time.sleep(2)

                    #get remaining time
                    remaining_duration = remaining_duration - sub_time

                    #add a small offset to compensate startup time-loss
                    logging.info("Process failed, retrying for remaining time {}".format(remaining_duration))

            # job failed throughout the duration
            logging.error("Job failed to run, tried {} times.".format(tries))
            wrap_fail({"errData" : "Failed to decode live stream", "logs" : outputs})

        except Exception as e:
            logging.error(e)
            wrap_fail({"errData" : "Internal error, failed to run pipeline".format(e)})




class StoredVideoDecoder:

    def __init__(self, settings):

        self.source_id = settings['source_id']
        self.settings = settings

    def create_decoder(self, source_uri, settings : dict):

        units = []

        source_unit = "filesrc location=\"{}\"".format(source_uri)
        units.append(source_unit)

        demuxer_unit = c_map[ settings['container'] ]
        units.append(demuxer_unit)

        decoder_unit = None

        #get video metadata and do processing
        result, video_meta = DiscoverVideo.GetVideoData(source_uri)
        if not result:
            return False, video_meta

        logging.info("Video metadata {}".format(video_meta))

        if video_meta['codec_name'] == 'h264' :
            if settings['use_gpu']:
                decoder_unit = "h264parse ! nvh264dec"
            else:
                decoder_unit = "h264parse ! avdec_h264"
        
        elif video_meta['codec_name'] == "hevc":
            if settings['use_gpu']:
                decoder_unit = "h265parse ! nvh265dec"
            else:
                decoder_unit = "h265parse ! avdec_h265"
        else:
            return False, "Unsupported video format {}".format(video_meta['codec_name'])
        
        units.append(decoder_unit)

        if 'use_custom_ts' in settings and settings['use_custom_ts']:
            units.append("timestamper")

        if ('width' in settings  or 'height' in settings) :
            scaler = "videoscale"
            units.append(scaler)
        
        #fps and video settings
        caps = "\"video/x-raw"
        if settings['fps'] != "0/0":
            caps = "{}, framerate=(fraction){}".format(caps, settings['fps'])
        
        if 'width' in settings and type(settings['width']) == int:
            caps = "{}, width={}".format(caps, settings['width'])
        
        if 'height' in settings and type(settings['height']) == int:
            caps = "{}, height={}".format(caps, settings['height'])
        
        caps = "{}\"".format(caps)

        units.append(caps)
        #generated a metadata, check metadata
        return True, units


    def create_encoder(self, settings):
        
        jpeg_encoder = "jpegenc"
        if 'quality' in settings and type(settings['quality']) == int:
            jpeg_encoder = "{} quality={}".format(jpeg_encoder, settings['quality'])
        
        #sink configuration
        sink = "tidbsink"

        if settings['operating_mode'] == 'live':
            sink = 'framedbsink'

        return  True, [jpeg_encoder, sink]

    def parse_pipeline(self):

        ret_dec, decoder_units = self.create_decoder(self.settings['url'], self.settings)
        if not ret_dec:
            return False, decoder_units

        ret_enc, encoder_units = self.create_encoder(self.settings)
        if not ret_enc:
            return False, encoder_units
        return True, [*decoder_units, *encoder_units]

    def __attach_units(self, units):

        units = " ! ".join(units)
        return units


    def __live_operator(self, pipeline):

        max_tries = 100
        tries = 0

        buffer_output = {}

        #live source never exists, kill the job or push back suspend
        while True:

            process_string = "gst-launch-1.0 {}".format(pipeline)
            child = subprocess.Popen(process_string, shell = True, stdout = subprocess.PIPE,  stderr = subprocess.PIPE)
            stream_output = child.communicate()[0]

            ret_code = child.returncode

            stream_string = str(stream_output, "utf-8")

            print(stream_string)

            if ret_code != 0:
                tries +=1

                buffer_output['try{}'.format(tries)] = stream_string
            
                if tries > max_tries:
                    print('Process failed for all {} times, exiting'.format(max_tries))
                    logging.error("process failed")
                    wrap_fail({"errData" : "failed to run task", "log" : buffer_output})
            else:
                print('finished successfully')
                logging.info("Decoding finished successfully")
                wrap_complete({"info" : "decoding finished", "log" : buffer_output})


    def run_pipeline(self):

        try:
            ret, pipeline_uints = self.parse_pipeline()
            if not ret:
                logging.error(pipeline_uints)
                wrap_fail({"errData" : pipeline_uints})

            # generate the shelx command:
            pipeline = self.__attach_units(pipeline_uints)

            if self.settings['operating_mode'] == "live":
                self.__live_operator(pipeline)

            #run the process:
            process = "gst-launch-1.0 {}".format(pipeline)

            logging.info("Running pipeline " + process)

            #launch a subprocess:
            child_handle = subprocess.Popen(process, shell=True, stdout = subprocess.PIPE)
            streamdata = child_handle.communicate()[0]

            ret_code = child_handle.returncode
            streamdata = str(streamdata, "utf-8")

            print(streamdata)

            if ret_code == 0 :
                #success:
                logging.info("Execution of pipeline finished successfully")
                wrap_complete({"message" : "completed properly", "logs" : streamdata})

            else:
                logging.info("Execution terminated because of error ")
                wrap_fail({"errData" : "failed execution", "logs" : streamdata})

        except Exception as e:
            logging.error(e)
            wrap_fail({"errData" : "Internal error, failed to run pipeline".format(e)})