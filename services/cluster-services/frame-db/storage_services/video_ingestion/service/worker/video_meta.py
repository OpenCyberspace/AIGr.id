import json
import subprocess
import shlex
import time
import os

class DiscoverVideo:

    @staticmethod
    def GetVideoData(url):
        if not url.startswith("rtsp://") :
            if not os.path.exists(url) :
                return False, "stored video does not exist"

        ffmpeg_command = "ffprobe -show_entries stream=codec_type,codec_name,width,height -v quiet -of json"
        args = shlex.split(ffmpeg_command)
        args.append(url)

        try:
            ffprobe_output = subprocess.check_output(args)

            # check stream :
            result = json.loads(ffprobe_output.decode('utf-8'))
    
            #check if video element is present :
            streams = result['streams']
            for stream in streams :
                if stream['codec_type'] == "video" :
                    return True, stream
    
            return False, "Failed to get any known video sources from {}".format(url)

        except Exception as e :
            return False, "Failed to get metadata,  unknown exception {}".format(e)

