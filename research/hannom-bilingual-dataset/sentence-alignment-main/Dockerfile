# FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04
# ARG CUDA_IMAGE="11.8.0-devel-ubuntu22.04"
# FROM nvidia/cuda:${CUDA_IMAGE}
FROM python:3.9

WORKDIR /app

RUN python -m pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]