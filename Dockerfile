# AWS Lambda Python 3.11 Base Image
FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies for GDAL, GEOS, and PROJ
RUN dnf install -y \
    gcc \
    gcc-c++ \
    make \
    tar \
    gzip \
    geos-devel \
    && dnf clean all

# Copy requirements and install python packages
COPY backend/requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt pypdf

# Copy application source code and bind_data library
COPY backend/src ${LAMBDA_TASK_ROOT}/
COPY backend/app ${LAMBDA_TASK_ROOT}/app
COPY backend/data ${LAMBDA_TASK_ROOT}/data

# Set PYTHONPATH to include LAMBDA_TASK_ROOT
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}:${LAMBDA_TASK_ROOT}/app"

# Command handler for Mangum FastAPI adapter
CMD [ "app.main.handler" ]
