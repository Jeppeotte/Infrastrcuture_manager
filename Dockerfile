FROM python:3.12-slim

# Copy all necessary files
COPY . .

# Install dependencies
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "main.py"]