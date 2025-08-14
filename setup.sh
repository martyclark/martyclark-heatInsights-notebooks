#!/bin/bash

echo "🌡️  EHF Heat Insights Environment Setup"
echo "======================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3.8 or later"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
if pip3 install -r requirements.txt; then
    echo "✅ Successfully installed Python packages"
else
    echo "❌ Failed to install Python packages"
    echo "Try: pip3 install --user -r requirements.txt"
    exit 1
fi

# Check for earthengine CLI
echo ""
echo "🌍 Checking Google Earth Engine setup..."
if command -v earthengine &> /dev/null; then
    echo "✅ Earth Engine CLI found"
    
    # Check if authenticated
    if earthengine ls > /dev/null 2>&1; then
        echo "✅ Earth Engine authenticated"
    else
        echo "⚠️  Earth Engine not authenticated"
        echo "Run: earthengine authenticate"
        echo "Then: earthengine set_project YOUR_PROJECT_ID"
    fi
else
    echo "⚠️  Earth Engine CLI not found"
    echo "Installing Earth Engine CLI..."
    pip3 install earthengine-api[cli]
    
    echo "Please run:"
    echo "  earthengine authenticate"
    echo "  earthengine set_project YOUR_PROJECT_ID"
fi

# Check Jupyter installation
echo ""
echo "📓 Checking Jupyter setup..."
if command -v jupyter &> /dev/null; then
    echo "✅ Jupyter found"
    echo "Start with: jupyter lab"
else
    echo "❌ Jupyter not found"
    echo "Installing Jupyter..."
    pip3 install jupyter jupyterlab
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Authenticate with Google Earth Engine:"
echo "   earthengine authenticate"
echo "   earthengine set_project YOUR_PROJECT_ID"
echo ""
echo "2. Start Jupyter Lab:"
echo "   jupyter lab"
echo ""
echo "3. Open and run: 09_phase1_era5_data_setup.ipynb"
echo ""
echo "For detailed instructions, see: SETUP_INSTRUCTIONS.md"