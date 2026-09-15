FROM pytorch/pytorch@sha256:db80a41f8428644cebcb3d75b0b62df334ab6c0e75785951eb25f48bfbd42407
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONUNBUFFERED=1 HF_HOME=/cache/huggingface TOKENIZERS_PARALLELISM=false
WORKDIR /workspace
COPY requirements-gpu.txt /tmp/requirements-gpu.txt
RUN apt-get update && apt-get install -y --no-install-recommends python3.12-venv build-essential git && rm -rf /var/lib/apt/lists/*
RUN python -m venv --system-site-packages /opt/briefcard && /opt/briefcard/bin/pip install --no-cache-dir -r /tmp/requirements-gpu.txt
ENV PATH="/opt/briefcard/bin:$PATH"
CMD ["python", "-m", "src.infer", "--help"]
