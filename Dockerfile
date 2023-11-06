# Use Python 3.10 base image
FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app
COPY ./requirements.txt /app

# Install any necessary dependencies
RUN pip install -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app

EXPOSE 8000

# Run command
CMD ["python", "main.py"]