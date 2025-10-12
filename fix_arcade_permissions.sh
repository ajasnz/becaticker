#!/bin/bash
# Fix permissions for arcade mode scripts

echo "🔧 Setting up arcade mode permissions..."

# Make arcade scripts executable
if [ -d "arcade" ]; then
    echo "Setting executable permissions on arcade scripts..."
    chmod +x arcade/*.sh
    echo "✅ Arcade scripts are now executable"
else
    echo "❌ Arcade directory not found"
fi

# Check results
echo ""
echo "📋 Arcade script status:"
for script in arcade/*.sh; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            echo "  ✅ $script (executable)"
        else
            echo "  ❌ $script (not executable)"
        fi
    fi
done

echo ""
echo "🎮 Arcade mode setup complete!"
echo "You can now test arcade mode through the web interface or run:"
echo "  python test_arcade_api.py"