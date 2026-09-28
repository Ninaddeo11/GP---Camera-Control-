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

# Plate-localization weights — see plate_detector.py's docstring for the
# full provenance/license/accuracy-caveat writeup; short version: a real,
# verified, Apache-2.0 YOLOv8 model (yasirfaizahmed/license-plate-object-detection
# on Hugging Face, trained on the public keremberke license-plate-detection
# dataset), not a fine-tuned Indian-plate model, since no labeled Indian-plate
# dataset exists in this environment to train one from. Retries a couple
# times but never fails the build on a network hiccup — plate_detector.py
# already handles a missing weights file by disabling ANPR cleanly, exactly
# as it would if this download simply didn't happen.
RUN curl -sL --retry 3 --retry-delay 2 -f \
      -o models/plate-detector-generic.pt \
      "https://huggingface.co/yasirfaizahmed/license-plate-object-detection/resolve/main/best.pt" \
    || echo "WARNING: plate detector download failed — ANPR will stay disabled until models/plate-detector-generic.pt is provided some other way"

EXPOSE 9090

CMD ["python", "-u", "main.py"]
