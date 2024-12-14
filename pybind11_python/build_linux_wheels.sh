#!/bin/bash
set -e

# Parse command line arguments
SKIP_EXISTING=false

print_usage() {
    echo "Usage: $0 [-s|--skip-existing]"
    echo "Options:"
    echo "  -s, --skip-existing    Skip building if the binary already exists"
    echo "  -h, --help            Show this help message"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--skip-existing)
            SKIP_EXISTING=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Python versions to build for
PYTHON_VERSIONS=( "3.6" "3.7" "3.8" "3.9" "3.10" "3.11" "3.12" "3.13" )

# Create Docker container for each Python version
for py_version in "${PYTHON_VERSIONS[@]}"; do
    echo "Building for Python ${py_version}"
    
    # Check if binary exists and skip if requested
    binary_path="prebuilt/hicstraw.linux.x86_64.cp${py_version}-${py_version}.so"
    if [[ "$SKIP_EXISTING" == true ]] && [[ -f "$binary_path" ]]; then
        echo "Binary already exists for Python ${py_version}, skipping..."
        continue
    fi
    
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

# Commands to check dependencies
echo "Checking dependencies with ldd:"
ldd prebuilt/hicstraw.linux.x86_64.cp3.13-3.13.so

echo -e "\nChecking dependencies with readelf:"
readelf -d prebuilt/hicstraw.linux.x86_64.cp3.13-3.13.so | grep NEEDED
