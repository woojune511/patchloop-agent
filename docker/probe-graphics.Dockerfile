# Public system libraries for offline VTK/PyVista probes. No task/evaluator data.
FROM patchloop-probe-python312:security-20261023@sha256:3b37b00de42a063f990e9b55d3918bb0a64cf5ec533a79e9650ca3ce9ccbe3b1
RUN apt-get update \
    && apt-get install --no-install-recommends -y libx11-6 libgl1 libxrender1 libsm6 libice6 \
    && rm -rf /var/lib/apt/lists/*
