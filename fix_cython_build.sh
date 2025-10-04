#!/bin/bash

# Quick Fix Script for Cython Build Issue
# Run this script to fix the current build problem

echo "🔧 BecaTicker Quick Fix - Cython Build Issue"
echo "============================================"

# Get to the right directory
cd "$(dirname "$0")"

echo "📍 Working in: $(pwd)"

# Check if we're in a virtual environment or create one
if [ -z "$VIRTUAL_ENV" ]; then
    if [ ! -d "venv" ]; then
        echo "📦 Creating virtual environment..."
        python3 -m venv venv
    fi
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
else
    echo "✅ Already in virtual environment: $VIRTUAL_ENV"
fi

# Install Cython in the virtual environment
echo "🐍 Installing Cython..."
pip install --upgrade pip
pip install Cython

# Try to build the RGB matrix library
echo "🔨 Building RGB Matrix library..."
cd hzeller

# Clean any previous failed builds
echo "🧹 Cleaning previous build artifacts..."
make clean

# Try the build with explicit Python
echo "🔄 Attempting build with virtual environment Python..."
if PYTHON=$(which python3) make build-python; then
    echo "✅ Build successful!"
else
    echo "⚠️  Standard build failed, trying direct Python binding installation..."
    
    # Try installing the Python bindings directly via pip
    cd bindings/python
    if pip install .; then
        echo "✅ Python bindings installed successfully via pip!"
    else
        echo "❌ All methods failed. Let's try a system-wide install..."
        cd ../..
        sudo make install-python
        if [ $? -eq 0 ]; then
            echo "✅ System-wide installation successful!"
        else
            echo "❌ Build completely failed. Please check the error messages above."
            exit 1
        fi
    fi
    cd ../..
fi

cd ..

# Test if the installation worked
echo "🧪 Testing the installation..."
if python3 -c "import rgbmatrix; print('✅ rgbmatrix module imported successfully!')"; then
    echo ""
    echo "🎉 Success! The RGB matrix library is now properly installed."
    echo "📋 You can now run:"
    echo "   sudo ./start_becaticker.sh    # To start the application"
    echo "   ./troubleshoot.sh           # To check system status"
else
    echo "❌ Import test failed. The library may not be properly installed."
    echo "📋 You may need to:"
    echo "   1. Check if you have the required hardware libraries"
    echo "   2. Run: sudo apt-get install python3-dev cython3"
    echo "   3. Try running this script again"
fi

echo ""
echo "🔍 Build Summary:"
echo "   Virtual environment: $([ -d "venv" ] && echo "✅ Created" || echo "❌ Missing")"
echo "   Cython installed: $(python3 -c "import Cython; print('✅ Yes')" 2>/dev/null || echo "❌ No")"
echo "   RGB library: $([ -f "hzeller/lib/librgbmatrix.a" ] && echo "✅ Built" || echo "❌ Missing")"
echo "   Python bindings: $(python3 -c "import rgbmatrix" 2>/dev/null && echo "✅ Working" || echo "❌ Failed")"