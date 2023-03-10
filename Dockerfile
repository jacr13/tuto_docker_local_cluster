FROM dmml/conda:py39

# define non-root user (created in conda image default: container)
ARG USERNAME=container

WORKDIR /

RUN apt-get update -q \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        git=1:2.25.* \
        vim=2:8.1.* \
        cmake=3.16.* \
        build-essential=12.* \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the default user to be non-root.
USER $USERNAME

# udpate conda
RUN conda update -n base -c defaults conda && \
    conda clean -ya

# copy and install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt && \
    sudo rm requirements.txt

WORKDIR /workspace
RUN sudo chmod -R a+w /workspace && git config --global --add safe.directory /workspace

