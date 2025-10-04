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
    echo "⚠️  Standard build failed, trying manual Cython compilation..."
    
    # Go to the Python bindings directory and manually build
    cd bindings/python/rgbmatrix
    
    # Check if core.pyx exists and manually compile it
    if [ -f "core.pyx" ]; then
        echo "🔨 Manually compiling Cython files..."
        
        # Try using cython3 first, then fall back to cython
        if command -v cython3 &> /dev/null; then
            cython3 --cplus -o core.cpp core.pyx
        elif python3 -c "import Cython" &> /dev/null; then
            python3 -c "from Cython.Build import cythonize; cythonize('core.pyx', language_level=3)"
        else
            echo "❌ No Cython available for manual compilation"
            cd ../../..
            exit 1
        fi
        
        # Check if core.cpp was created
        if [ -f "core.cpp" ]; then
            echo "✅ Cython compilation successful!"
            cd ..
            
            # Now try pip install again
            if pip install .; then
                echo "✅ Python bindings installed successfully after manual Cython compilation!"
            else
                echo "⚠️  Pip install still failed, trying system-wide install..."
                cd ../..
                sudo make install-python
                if [ $? -eq 0 ]; then
                    echo "✅ System-wide installation successful!"
                else
                    echo "❌ All build methods failed."
                    exit 1
                fi
            fi
            cd ../..
        else
            echo "❌ Manual Cython compilation failed"
            cd ../../..
            exit 1
        fi
    else
        echo "❌ core.pyx file not found"
        cd ../../..
        exit 1
    fi
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