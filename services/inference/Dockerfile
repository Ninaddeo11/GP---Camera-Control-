# CUDA-matched PyTorch base — GPU confirmed available for this deployment
# (see README.md "Assumptions currently in effect"). SENTINELGRID_DEVICE
# still works with "cpu" on this same image if run somewhere without a GPU;
# torch itself supports both from one install.
FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/models /data/snapshots

EXPOSE 9090

CMD ["python", "-u", "main.py"]
