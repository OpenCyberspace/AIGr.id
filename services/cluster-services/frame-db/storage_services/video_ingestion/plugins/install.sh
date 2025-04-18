#!/bin/bash

cp tidbsink.py /cognit_plugins/python
echo "installed plugin...tidbsink"
echo "run 'gst-inspect-1.0 tidbsink' to know more about the plugin."

cp timestamper.py /cognit_plugins/python
echo "installed plugin...timestamper"
echo "run 'gst-inspect-1.0 timestamper' to know more about the plugin."

cp framedbsink.py /cognit_plugins/python
echo "installed plugin...framedbsink"
echo "run 'gst-inspect-1.0 framedbsink' to know more about the plugin."