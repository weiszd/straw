#!/bin/bash
set -e

# Python versions to build for
PYTHON_VERSIONS=("3.8" "3.9" "3.10" "3.11" "3.12")

# Create Docker container for each Python version
for py_version in "${PYTHON_VERSIONS[@]}"; do
    echo "Building for Python ${py_version}"
    
    # Create Dockerfile
    cat > Dockerfile.${py_version} << EOF
FROM python:${py_version}-slim

# Install essential packages and development tools
RUN apt-get update && \\
    apt-get install -y \\
    build-essential \\
    pkg-config \\
    git \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Install curl and zlib development packages separately to ensure they're properly installed
RUN apt-get update && \\
    apt-get install -y \\
    libcurl4-openssl-dev \\
    zlib1g-dev \\
    && rm -rf /var/lib/apt/lists/* \\
    && ldconfig

# Verify the installation of development packages
RUN apt list --installed | grep -E 'libcurl4-openssl-dev|zlib1g-dev'

WORKDIR /build
COPY . .

RUN pip install --upgrade pip && \\
    pip install pybind11 setuptools wheel

CMD ["python", "build_prebuilt.py"]
EOF

    # Build Docker image
    docker build -t hicstraw-builder:${py_version} -f Dockerfile.${py_version} .
    
    # Run container to build the extension
    docker run --rm -v $(pwd)/prebuilt:/build/prebuilt hicstraw-builder:${py_version}
    
    # Clean up Dockerfile
    rm Dockerfile.${py_version}
done

echo "All builds completed. Pre-built binaries are in the 'prebuilt' directory."
