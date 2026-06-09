import subprocess
import sys

def install_package(package):
    try:
        print(f"正在安装 {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✓ {package} 安装成功")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ {package} 安装失败")
        return False

if __name__ == "__main__":
    packages = [
        "opencv-python",
        "numpy",
        "ultralytics",
        "dashscope",
        "requests",
        "keyboard"
    ]
    
    print("开始安装依赖包...")
    print("=" * 50)
    
    for pkg in packages:
        install_package(pkg)
    
    print("=" * 50)
    print("安装完成！")