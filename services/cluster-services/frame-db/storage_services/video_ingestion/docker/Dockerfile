FROM nvidia/cuda:11.2.1-devel-ubuntu20.04

# nvidia gpu parameters
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES all
ARG DEBIAN_FRONTEND=noninteractive

# expect a build-time variable
# use the value to set the ENV var default
ENV BRANCH=$VERSION
ENV PATH="${PATH}:/root/.local/bin:/usr/local/cuda-11.2/bin"
ENV LD_LIBRARY_PATH="/usr/local:/usr/local/cuda-11.2/lib64"

RUN apt-get update && apt-get install -y \
        cmake git autoconf autopoint libtool libreadline-dev \
        automake unzip nano wget python3-pip \
        gtk-doc-tools glib-2.0 freeglut3 \
        bison flex libglib2.0-dev libgvc6 graphviz-dev \
        libunwind-dev libdw-dev libgtk-3-dev \
        liborc-0.4-0 liborc-0.4-dev \
        libx11-dev xorg-dev libglu1-mesa-dev freeglut3-dev \
        libglew1.5 libglew1.5-dev \
        libglu1-mesa libglu1-mesa-dev libgl1-mesa-glx \
        libgl1-mesa-dev \
        libtheora-bin libtheora-dev libtheora-doc \
        libvorbis-dev \
        libcdparanoia-dev \
        alsa-base alsa-tools \
        libasound2-dev \
        libopus-dev libvisual-0.4-dev libpango1.0 \
        libwavpack-dev libspeex-dev libdv4-dev \
        libsoup2.4-dev qtdeclarative5-dev \
        libcairo-dev \
        yasm nasm libbz2-dev liblzma-dev \
        libx264-dev \
        x265 x264 \
        libx264-dev \
        python-gi-dev \
        python3-dev \
        gir1.2-gst-plugins-base-1.0 && \
        pip3 install --user meson && \
        wget https://github.com/ninja-build/ninja/releases/download/v1.9.0/ninja-linux.zip && \
        unzip ninja-linux.zip && \
        mv ninja /usr/local/bin/ && \
        rm ninja-linux.zip && \
        git clone https://gitlab.freedesktop.org/gstreamer/gst-build.git

ARG VERSION="master"

WORKDIR /gst-build
RUN git checkout "$VERSION"
RUN /root/.local/bin/meson build;
RUN apt install -y libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0

#for running GRPC scripts
RUN pip3 install grpcio protobuf

#some additional pip packages used by example plugins
RUN pip3 install matplotlib numpy_ringbuffer pillow

#clone NVIDIA patch
RUN git clone https://github.com/keylase/nvidia-patch.git
#COPY ./nvidia-patch nvidia-patch

RUN apt install -y libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0

#for camera manager server
RUN pip3 install flask

RUN pip3 install redis kafka-python grpcio



RUN apt update -y && apt install -y ffmpeg libleveldb-dev
RUN pip3 install requests

COPY . /gst-build/video_ingestion
COPY setup_env.sh /gst-build/
COPY env.sh /gst-build
COPY build.sh /
COPY gst-python-build.1.19.0.1.build gst-build/gst-python/meson.build

RUN chmod 777 /build.sh

WORKDIR /gst-build

#build gstreamer
RUN meson configure build/ -Dgst-plugins-bad:nvcodec=enabled && ninja -C build/;


#install ingestion_library used for TiDB 
RUN pip3 install -e video_ingestion/ingestion_library

#install routing_libary used for in-memory routing system
RUN pip3 install -e video_ingestion/routing_library

RUN chmod 777 env.sh
RUN chmod 777 setup_env.sh


ENTRYPOINT ["./env.sh" ]