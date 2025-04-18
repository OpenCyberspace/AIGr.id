FROM streamer:latest


RUN apt update -y && apt install -y ffmpeg
RUN pip3 install requests

COPY . /gst-build/routing_client
COPY setup_env.sh /gst-build/
COPY env.sh /gst-build
COPY build.sh /
COPY gst-python-build.1.19.0.1.build gst-build/gst-python/meson.build

RUN chmod 777 /build.sh && /build.sh

WORKDIR /gst-build

#build gstreamer 
RUN meson configure build/ -Dgst-plugins-bad:nvcodec=enabled;
RUN ninja -C build/;

RUN pip3 install -e routing_client/

RUN chmod 777 env.sh
RUN chmod 777 setup_env.sh


ENTRYPOINT ["./env.sh" ]