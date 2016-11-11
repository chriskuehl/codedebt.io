FROM debian:jessie
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential \
        git \
        lib32z1-dev \
        libssl-dev \
        libxslt1-dev \
        libyaml-dev \
        python3 \
        python3-dev \
        python3-pip \
        virtualenv \
    && apt-get clean

RUN install -d /opt/codedebt

COPY setup.py /opt/codedebt/
COPY requirements.txt /opt/codedebt/

RUN virtualenv -ppython3 /opt/codedebt/venv
RUN /opt/codedebt/venv/bin/pip install pip==8.1.2
COPY codedebt_io /opt/codedebt/codedebt_io
RUN /opt/codedebt/venv/bin/pip install -r /opt/codedebt/requirements.txt /opt/codedebt

WORKDIR /opt/codedebt
