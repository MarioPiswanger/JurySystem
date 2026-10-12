FROM python:3.12-slim

WORKDIR /usr/src/app

# set environment variables - has advantages for python in docker container
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ="Europe/Berlin"
# do not ping model hosters on every start, models are baked into the image
ENV PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
ENV YOLO_CONFIG_DIR=/usr/src/app/.ultralytics

# opencv / paddle runtime libraries
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# install python dependencies (CPU-only torch keeps the image ~2 GB smaller)
RUN pip install --upgrade pip
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# download model weights at build time instead of at the first request
RUN mkdir -p models && cd models && \
    python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')" && \
    python -c "from paddleocr import PaddleOCR; PaddleOCR(text_detection_model_name='PP-OCRv5_mobile_det', text_recognition_model_name='PP-OCRv5_mobile_rec', use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)"

COPY ./src /usr/src/app/src

EXPOSE 5610
CMD ["sh", "-c", "cd /usr/src/app/src && uvicorn main:api --host 0.0.0.0 --port ${PORT_BIB_OCR:-5610} --workers 1 --proxy-headers"]
