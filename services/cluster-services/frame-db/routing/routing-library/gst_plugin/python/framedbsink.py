from gi.repository import Gst, GObject, GstBase
Gst.init(None)

from pygst_utils import map_gst_buffer, get_buffer_size
import json
import time

import os
import logging

logging.basicConfig(level = logging.INFO)

def create_packet(buffer_data, include_timestamp = True):
  
  return buffer_data[0]

def convert_frame(gstreamer_buffer):
  #write your own encoder here, one of the most basic forms is just to 
  return [bytes(gstreamer_buffer)]



def frame_validator(data : bytes, metadata : dict, frame_data ) :

  width_match = True
  height_match = True
  image_type_match = True

  if 'width' in metadata :
    width_match = ( metadata['width'] == frame_data['width'] )
  
  if 'height' in metadata :
    height_match = ( metadata['height'] == frame_data['height'] )
  
  if 'type' in metadata :
    image_type_match = ( metadata['type'] == frame_data.get_name() )
  
  return width_match and height_match and image_type_match
  


class FramedbRouter :

  def __init__(self):
    
    from redis_router import RedisRouter, FrameValidator

    ROUTING_URI = os.getenv("ROUTING_URI", "http://localhost:8000")
    ROUTING_API = os.getenv("ROUTING_API", "/routing/getMapping")
    UPDATE_API = os.getenv("UPDATE_API", "/routing/updateMapping")

    ROUTING_PUBSUB_HOST = os.getenv("PUBSUB_HOST", "localhost")
    ROUTING_PUBSUB_PORT = int(os.getenv("PUBSUB_PORT", 6379))
    ROUTING_PUBSUB_PASSWORD = os.getenv("PUBSUB_PASSWORD", "Friends123#")

    FRAME_VALIDATION = True if os.getenv("FRAME_VALIDATION", "No").lower() == "yes" else False

    updateChannelData = {
        "host" : ROUTING_PUBSUB_HOST,
        "port" : ROUTING_PUBSUB_PORT,
        "password" : ROUTING_PUBSUB_PASSWORD,
        "db" : 0,
        "isSentinel" : False
    }

    routingService = {
        "uri" : ROUTING_URI,
        "api" : ROUTING_API,
        "update_api" : "/routing/updateMapping"
    }

    self.cameraId = os.getenv("CAMERA_ID", "test")

    self.validator = None

    if FRAME_VALIDATION :
      logging.info("Frame validation turned on")
      self.validator = FrameValidator(self.cameraId, None, use_own_keys = True)

    self.router = RedisRouter(
        self.cameraId, 
        routingService, 
        enableUpdates = True,  
        updateChannelData = updateChannelData,
        asynchronous = True
    )

    self.idx = 0

    self.op = os.getenv("OP", "set").lower()
    
  

  def send_packet(self, packet, appendTail = True):
    #self.redis_connection.lpush(self.cameraId, packet)
    self.router.put(self.cameraId, str(self.idx), packet, self.op)
    self.idx +=1
  


class FramedbSink(GstBase.BaseSink):

    __gstmetadata__ = ('FramedbSink','Sink', \
                      'Plugin written using RedisRouter, a library used to push frames to Redis, used in FrameDB', 'prasanna@cognitif.ai')


    __gsttemplates__ = Gst.PadTemplate.new("sink",
                                           Gst.PadDirection.SINK,
                                           Gst.PadPresence.ALWAYS,
                                           Gst.Caps.new_any())

    sync = True

    #I am hardcoding the camera ID

    def do_get_property(self, prop):

      if prop.name == "camera-id" :
        return self.camera_id
      elif prop.name == "redis-host" :
        return self.redis_host
      elif prop.name == "redis-port" :
        return self.redis_port
      else :
        print('Requested parameter ', prop.name, ' not found')


    def do_set_property(self, prop, value) :

      #print('Setting props')

      if prop.name == "camera-id" :
        self.camera_id = value
      elif prop.name == "redis-host" :
        self.redis_host = value
      elif prop.name == "redis-port" :
        self.redis_port = value
      else :
        print('Ignoring invalid property ', prop.name)

      #print(self.camera_id, self.redis_host, self.redis_port)


    def __init__(self):


      super(FramedbSink , self).__init__()

      self.camera_id = os.environ.get("CAMERA_ID", "CAMERA_ID_UNKNOWN_1")
      #self.redis_port = str(os.environ.get("REDIS_PORT", 6739))
      #self.redis_host = os.environ.get("REDIS_HOST", "localhost")

      self.redisClient = FramedbRouter()
      #print('Initialized redis client at ', self.redis_host, ":", self.redis_port)

      self.validator_ref = self.redisClient.validator

      #print(self.validator_ref)
      self.router_ref = self.redisClient.router
  

    def do_render(self, buffer):
        
        #map_gst_buffer is a generator that yields buffer data

        with map_gst_buffer(buffer, Gst.MapFlags.READ) as memory_buffer:

          #validate frame if validation is turned on
          if self.validator_ref :
            #current frame metadata
            gst_caps = self.sinkpad.get_current_caps().get_structure(0)

            caps_dict = {"width" : gst_caps['width'], "height" : gst_caps['height'], "type" : gst_caps.get_name() }

            if not self.validator_ref.is_valid_frame(routerObject = self.router_ref, frame_data = caps_dict) :
              return Gst.FlowReturn.OK
            
            logging.info("Frame idx={} passed validation".format(self.redisClient.idx))

          bytes_frame = convert_frame(memory_buffer)
          packet = create_packet(bytes_frame, include_timestamp = False)
          self.redisClient.send_packet(packet, appendTail  = True)
          

        return Gst.FlowReturn.OK



GObject.type_register(FramedbSink)
__gstelementfactory__ = ("framedbsink", Gst.Rank.NONE, FramedbSink)

