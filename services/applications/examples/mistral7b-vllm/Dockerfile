FROM aios_transformers:v1

# Install basic packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl git ca-certificates gnupg software-properties-common \
    python3 python3-pip python3-dev python3-venv \
    build-essential libssl-dev libffi-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3 /usr/bin/python && ln -s /usr/bin/pip3 /usr/bin/pip

# Install NVIDIA CUDA Toolkit (12.1 or latest compatible with PyTorch)
# You can check versions at: https://developer.nvidia.com/cuda-downloads
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin && \
    mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600 && \
    wget https://developer.download.nvidia.com/compute/cuda/12.1.1/local_installers/cuda-repo-ubuntu2204-12-1-local_12.1.1-530.30.02-1_amd64.deb && \
    dpkg -i cuda-repo-ubuntu2204-12-1-local_12.1.1-530.30.02-1_amd64.deb && \
    cp /var/cuda-repo-ubuntu2204-12-1-local/cuda-*-keyring.gpg /usr/share/keyrings/ && \
    apt-get update && apt-get -y install cuda && \
    rm -f cuda-repo-ubuntu2204-12-1-local_12.1.1-530.30.02-1_amd64.deb

# Install pip dependencies (adjust versions if needed)
RUN pip install --upgrade pip setuptools wheel

COPY . /app

WORKDIR /app

RUN pip3 install -r requirements.txt

ENTRYPOINT [ "python3", "block.py" ]