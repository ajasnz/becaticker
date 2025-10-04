#!/bin/bash

# Comprehensive RGB Matrix Library Build Script
# This script handles the complex build process for the hzeller RGB matrix library

echo "🔨 RGB Matrix Library Builder"
echo "============================="

# Get to the right directory
cd "$(dirname "$0")"

# Ensure we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    if [ ! -d "venv" ]; then
        echo "📦 Creating virtual environment..."
        python3 -m venv venv
    fi
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
fi

echo "📍 Working in: $(pwd)"
echo "🐍 Python: $(which python3)"
echo "🔧 Virtual Environment: $VIRTUAL_ENV"

# Install essential build dependencies
echo "📦 Installing build dependencies..."
pip install --upgrade pip setuptools wheel
pip install Cython

# Install system dependencies if needed
echo "🔧 Checking system dependencies..."
if ! dpkg -l | grep -q python3-dev; then
    echo "📦 Installing python3-dev..."
    sudo apt-get update
    sudo apt-get install -y python3-dev build-essential
fi

# Navigate to hzeller directory
cd hzeller

echo "🧹 Cleaning previous builds..."
make clean > /dev/null 2>&1

# Step 1: Build the core library first
echo "🔨 Building core RGB matrix library..."
make -C lib

if [ $? -ne 0 ]; then
    echo "❌ Core library build failed"
    exit 1
fi

echo "✅ Core library built successfully"

# Step 2: Manual Cython compilation
echo "🐍 Manually building Python bindings..."
cd bindings/python/rgbmatrix

# Check if core.pyx exists
if [ ! -f "core.pyx" ]; then
    echo "❌ core.pyx not found in $(pwd)"
    cd ../../..
    exit 1
fi

# Remove any existing core.cpp to force regeneration
rm -f core.cpp

# Try different Cython compilation methods
echo "🔄 Compiling Cython files..."

if command -v cython3 &> /dev/null; then
    echo "   Using system cython3..."
    cython3 --cplus -o core.cpp core.pyx
elif python3 -c "import Cython.Compiler.Main" &> /dev/null; then
    echo "   Using Python Cython module..."
    python3 -c "
import Cython.Compiler.Main
Cython.Compiler.Main.compile('core.pyx', options=Cython.Compiler.Main.CompilationOptions(cplus=True, output_file='core.cpp'))
"
else
    echo "❌ No working Cython installation found"
    cd ../../..
    exit 1
fi

# Check if core.cpp was created
if [ ! -f "core.cpp" ]; then
    echo "❌ Cython compilation failed - core.cpp not created"
    cd ../../..
    exit 1
fi

echo "✅ Cython compilation successful!"

# Step 3: Try to build the Python extension
cd ..

# Set up environment variables for the build
export PYTHON=$(which python3)
export CFLAGS="-I../../../include"
export LDFLAGS="-L../../../lib"

echo "🔨 Building Python extension..."

# Try the standard make build
if make build-python PYTHON="$PYTHON"; then
    echo "✅ Python extension built with make!"
else
    echo "⚠️  Make build failed, trying pip install..."
    
    # Try pip install with verbose output
    if pip install . -v; then
        echo "✅ Python extension installed with pip!"
    else
        echo "❌ Both make and pip builds failed"
        
        # Last resort: try system-wide install
        echo "🔄 Trying system-wide installation as last resort..."
        cd ../..
        if sudo make install-python; then
            echo "✅ System-wide installation successful!"
        else
            echo "❌ All installation methods failed"
            exit 1
        fi
    fi
fi

cd ../..

# Step 4: Test the installation
echo "🧪 Testing RGB matrix Python module..."

if python3 -c "
import rgbmatrix
print('✅ rgbmatrix module imported successfully!')
print(f'   Module location: {rgbmatrix.__file__}')
try:
    options = rgbmatrix.RGBMatrixOptions()
    print('✅ RGBMatrixOptions created successfully!')
except Exception as e:
    print(f'⚠️  Options creation failed: {e}')
"; then
    echo ""
    echo "🎉 SUCCESS! RGB Matrix library is now properly installed!"
    echo ""
    echo "📋 Installation Summary:"
    echo "   ✅ Core library built"
    echo "   ✅ Cython compilation successful"  
    echo "   ✅ Python bindings installed"
    echo "   ✅ Module import test passed"
    echo ""
    echo "🚀 You can now run:"
    echo "   sudo ./start_becaticker.sh"
    echo ""
else
    echo "❌ Installation test failed!"
    echo ""
    echo "🔍 Troubleshooting steps:"
    echo "   1. Check if you have GPIO access (run as root)"
    echo "   2. Verify hardware connections"
    echo "   3. Check system logs: dmesg | tail"
    echo "   4. Try: sudo modprobe spi_bcm2835"
    echo ""
    exit 1
fi