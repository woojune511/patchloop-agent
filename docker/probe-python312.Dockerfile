# Public runtime only; task and evaluator dependencies never enter this image.
FROM python@sha256:e8a38829209aea82774882e5157e1f7c3e8c8393ff53a697b3580896e57f345c

# The official 3.12.15 image has fixed OS CAs but still bundles pip 25.0.1.
# The Python incident advisory supplies this exact wheel URL and checksum.
ADD --chmod=0644 --checksum=sha256:fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70 \
    https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl \
    /tmp/pip-26.2.2-py3-none-any.whl
RUN apt-get update \
    && apt-get upgrade --no-install-recommends -y \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-index --no-deps --no-cache-dir /tmp/pip-26.2.2-py3-none-any.whl \
    && rm /usr/local/lib/python3.12/ensurepip/_bundled/pip-25.0.1-py3-none-any.whl \
    && mv /tmp/pip-26.2.2-py3-none-any.whl /usr/local/lib/python3.12/ensurepip/_bundled/ \
    && sed -i 's/_PIP_VERSION = "25.0.1"/_PIP_VERSION = "26.2.2"/' /usr/local/lib/python3.12/ensurepip/__init__.py \
    && python -c 'import ensurepip, pip; assert ensurepip.version() == pip.__version__ == "26.2.2"'
