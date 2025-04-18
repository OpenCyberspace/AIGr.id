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
  


class TiDBWriter :

  def __init__(self):
    
    from tidb_writer import GstreamerSource

    self.cameraId = os.getenv("SOURCE_ID", "test")

    self.frame_writer = GstreamerSource(
      source_id = self.cameraId,
      validation_function = frame_validator
    )

    
  def send_packet(self, packet, validation_data = {}):
    #self.redis_connection.lpush(self.cameraId, packet)
    self.frame_writer.write_frame(packet, validation_data)


class Tidbsink(GstBase.BaseSink):

    __gstmetadata__ = ('tidbsink','Sink', \
                      'Plugin written using TiDBWriter, a library used to write frames to TiDB', 'prasanna@cognitif.ai')


    __gsttemplates__ = Gst.PadTemplate.new("sink",
                                           Gst.PadDirection.SINK,
                                           Gst.PadPresence.ALWAYS,
                                           Gst.Caps.new_any())

    sync = True

    def __init__(self):


      super(Tidbsink , self).__init__()


      self.client = TiDBWriter()

  

    def do_render(self, buffer):
        
        #map_gst_buffer is a generator that yields buffer data

        with map_gst_buffer(buffer, Gst.MapFlags.READ) as memory_buffer:

          gst_caps = self.sinkpad.get_current_caps().get_structure(0)

          caps_dict = {"width" : gst_caps['width'], "height" : gst_caps['height'], "type" : gst_caps.get_name() }
          
          bytes_frame = convert_frame(memory_buffer)
          packet = create_packet(bytes_frame, include_timestamp = False)
          self.client.send_packet(packet, caps_dict)
          

        return Gst.FlowReturn.OK



GObject.type_register(Tidbsink)
__gstelementfactory__ = ("tidbsink", Gst.Rank.NONE, Tidbsink)

