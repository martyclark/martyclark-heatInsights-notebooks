#!/usr/bin/env python3
"""
Setup script for EHF Heat Insights environment
This script installs required packages and sets up Google Earth Engine authentication
"""

import subprocess
import sys
import os

def install_requirements():
    """Install required packages"""
    print("Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Successfully installed all requirements")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing requirements: {e}")
        return False

def setup_gee_authentication():
    """Setup Google Earth Engine authentication"""
    print("\nSetting up Google Earth Engine authentication...")
    print("Please follow these steps:")
    print("1. Run: earthengine authenticate")
    print("2. Follow the browser authentication flow")
    print("3. Set your default project: earthengine set_project YOUR_PROJECT_ID")
    print("\nAlternatively, if you don't have GEE access yet:")
    print("1. Visit: https://earthengine.google.com/signup/")
    print("2. Sign up for Google Earth Engine")
    print("3. Once approved, run the authentication commands above")
    
    # Try to import earthengine to check if it's installed
    try:
        import ee
        print("✅ Earth Engine API installed")
        
        # Try to initialize (this will fail if not authenticated)
        try:
            ee.Initialize()
            print("✅ Earth Engine authenticated and ready")
            return True
        except Exception as e:
            print(f"⚠️  Earth Engine not authenticated: {e}")
            print("Run: earthengine authenticate")
            return False
            
    except ImportError:
        print("❌ Earth Engine API not installed")
        return False

def main():
    """Main setup function"""
    print("EHF Heat Insights Environment Setup")
    print("=" * 50)
    
    # Install requirements
    req_success = install_requirements()
    
    # Setup GEE authentication
    gee_success = setup_gee_authentication()
    
    print("\n" + "=" * 50)
    print("SETUP SUMMARY")
    print("=" * 50)
    print(f"Requirements installation: {'✅ Success' if req_success else '❌ Failed'}")
    print(f"Google Earth Engine setup: {'✅ Ready' if gee_success else '⚠️  Needs authentication'}")
    
    if req_success and gee_success:
        print("\n🎉 Environment setup complete! You can now run the EHF notebooks.")
    elif req_success:
        print("\n⚠️  Packages installed, but GEE authentication needed.")
        print("Please run 'earthengine authenticate' before using the notebooks.")
    else:
        print("\n❌ Setup incomplete. Please check the error messages above.")

if __name__ == "__main__":
    main()