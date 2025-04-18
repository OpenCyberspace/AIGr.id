import logging
import timeit
import traceback
import time

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')

from gi.repository import Gst, GObject, GLib, GstBase  # noqa:F401,F402


class Timestamper(GstBase.BaseTransform):

    GST_PLUGIN_NAME = 'timestamper'

    __gstmetadata__ = ("timstamper",
                       "A workaround to fix pts issues",
                       "Adds buffer.pts to system clock time",
                       "prasanna@cognitif.ai")

    __gsttemplates__ = (Gst.PadTemplate.new("src",
                                            Gst.PadDirection.SRC,
                                            Gst.PadPresence.ALWAYS,
                                            Gst.Caps.new_any()),
                        Gst.PadTemplate.new("sink",
                                            Gst.PadDirection.SINK,
                                            Gst.PadPresence.ALWAYS,
                                            Gst.Caps.new_any()))
    

    def __init__(self):

        self.std_time_unit = 1 * Gst.SECOND
        self.s = 0
        self.is_initial = True


    def do_transform_ip(self, buffer: Gst.Buffer) -> Gst.FlowReturn:

        current_time = int(time.perf_counter() * self.std_time_unit)

        if not self.is_initial:
            buffer.pts  = current_time - self.s
        else:
            buffer.pts = 0
            self.s = current_time
            self.is_initial = False
            
        return Gst.FlowReturn.OK


# Register plugin to use it from command line
GObject.type_register(Timestamper)
__gstelementfactory__ = (Timestamper.GST_PLUGIN_NAME,
                         Gst.Rank.NONE, Timestamper)
