# Public system libraries for offline VTK/PyVista probes. No task/evaluator data.
FROM python@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
RUN apt-get update \
    && apt-get install --no-install-recommends -y libx11-6 libgl1 libxrender1 libsm6 libice6 \
    && rm -rf /var/lib/apt/lists/*
