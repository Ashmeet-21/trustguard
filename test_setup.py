#!/usr/bin/env python3
"""
TrustGuard - Quick Test Script
Tests if everything is set up correctly
"""

import sys
import os
os.environ["PYTHONUTF8"] = "1"
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
import subprocess
import importlib.util

def check_python_version():
    """Check if Python version is 3.8+"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor} detected")
        print("   ⚠️  Python 3.8+ required")
        return False

def check_package(package_name, display_name=None):
    """Check if a package is installed"""
    if display_name is None:
        display_name = package_name
    
    spec = importlib.util.find_spec(package_name)
    if spec is not None:
        print(f"   ✅ {display_name}")
        return True
    else:
        print(f"   ❌ {display_name} not found")
        return False

def check_dependencies():
    """Check if all required packages are installed"""
    print("\n📦 Checking dependencies...")
    
    packages = [
        ('torch', 'PyTorch'),
        ('torchvision', 'TorchVision'),
        ('cv2', 'OpenCV'),
        ('PIL', 'Pillow'),
        ('fastapi', 'FastAPI'),
        ('uvicorn', 'Uvicorn'),
        ('numpy', 'NumPy'),
    ]
    
    all_installed = True
    for package, display in packages:
        if not check_package(package, display):
            all_installed = False
    
    return all_installed

def check_directories():
    """Check if required directories exist"""
    print("\n📁 Checking directory structure...")
    
    required_dirs = [
        'backend/core',
        'backend/api',
        'backend/models',
        'datasets',
        'frontend/src',
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"   ✅ {dir_path}/")
        else:
            print(f"   ❌ {dir_path}/ not found")
            all_exist = False
    
    return all_exist

def check_env_file():
    """Check if .env file exists"""
    print("\n⚙️  Checking configuration...")
    
    env_path = Path('.env')
    env_example = Path('.env.example')

    if env_path.exists():
        print("   ✅ .env file found")
        return True
    elif env_example.exists():
        print("   ⚠️  .env file not found")
        print("   💡 Run: cp .env.example .env")
        return False
    else:
        print("   ❌ No .env or .env.example found")
        return False

def test_deepfake_detector():
    """Test if deepfake detector can be imported"""
    print("\n🤖 Testing deepfake detector...")
    
    try:
        sys.path.append(str(Path('backend')))
        from core.deepfake_detector import DeepfakeDetector
        
        detector = DeepfakeDetector()
        print("   ✅ Deepfake detector initialized")
        return True
    except Exception as e:
        print(f"   ❌ Failed to initialize: {str(e)}")
        return False

def check_api_server():
    """Check if API server can start"""
    print("\n🌐 Checking API server...")
    
    try:
        import requests
        response = requests.get('http://localhost:8000/health', timeout=2)
        if response.status_code == 200:
            print("   ✅ API server is running")
            return True
    except:
        pass
    
    print("   ⚠️  API server not running")
    print("   💡 Start with: python backend/main.py")
    return False

def main():
    """Run all checks"""
    print("="*60)
    print("🛡️  TrustGuard - System Check")
    print("="*60)
    
    results = {
        'Python Version': check_python_version(),
        'Dependencies': check_dependencies(),
        'Directory Structure': check_directories(),
        'Configuration': check_env_file(),
        'Deepfake Detector': test_deepfake_detector(),
        'API Server': check_api_server()
    }
    
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check}")
    
    print("="*60)
    print(f"Score: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All checks passed! You're ready to go!")
        print("\n📝 Next steps:")
        print("   1. Start API server: python backend/main.py")
        print("   2. Open browser: http://localhost:8000/docs")
        print("   3. Test with sample images")
    elif passed >= total - 2:
        print("\n👍 Almost there! Fix the failed checks above.")
    else:
        print("\n⚠️  Several issues found. Please fix them before proceeding.")
        print("\n💡 Quick fixes:")
        if not results['Dependencies']:
            print("   • Install dependencies: pip install -r requirements.txt")
        if not results['Configuration']:
            print("   • Create config: cp .env.template .env")
        if not results['Directory Structure']:
            print("   • You may be in the wrong directory")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
