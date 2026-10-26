# Validate the full installer as an ordinary Ubuntu user without motor hardware.
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends sudo ca-certificates \
    && useradd --create-home --shell /bin/bash developer \
    && echo 'developer ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/developer
WORKDIR /home/developer/robstride-jetson-env
COPY --chown=developer:developer . .
RUN chown developer:developer /home/developer/robstride-jetson-env
USER developer
RUN bash install.sh
RUN bash install.sh --check && bash install.sh --skip-system
