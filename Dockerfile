FROM python:3.9-slim

WORKDIR /app

# Install dependencies first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Install the package
RUN pip install --no-cache-dir -e .

# Create a non-root user and switch to it
RUN useradd -m bedrock-checker
USER bedrock-checker

# Create a directory for output files
RUN mkdir -p /tmp/bedrock-reports
VOLUME /tmp/bedrock-reports

# Add AWS configuration directory
VOLUME /home/bedrock-checker/.aws

# Set the entrypoint
ENTRYPOINT ["check-bedrock-access"]

# Default command (can be overridden)
CMD ["--help"]