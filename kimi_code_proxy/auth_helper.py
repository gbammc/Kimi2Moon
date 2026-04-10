"""
Kimi Code 认证辅助工具

帮助用户设置和刷新 Kimi Code 认证
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any

KIMI_CREDENTIALS_PATH = Path.home() / ".kimi" / "credentials" / "kimi-code.json"


def check_kimi_cli() -> bool:
    """检查是否安装了 Kimi CLI"""
    try:
        result = subprocess.run(
            ["kimi", "--version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def read_credentials() -> Optional[Dict[str, Any]]:
    """读取凭证文件"""
    if not KIMI_CREDENTIALS_PATH.exists():
        return None
    
    try:
        with open(KIMI_CREDENTIALS_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def refresh_token() -> bool:
    """尝试刷新 token"""
    print("🔄 尝试刷新 Kimi Code token...")
    
    try:
        result = subprocess.run(
            ["kimi", "whoami"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ Token 刷新成功")
            return True
        else:
            print(f"❌ Token 刷新失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Token 刷新超时")
        return False
    except FileNotFoundError:
        print("❌ 未找到 kimi 命令，请确保 Kimi CLI 已安装")
        return False


def setup_auth():
    """设置认证"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           🔐 Kimi Code 认证设置向导                          ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # 检查 Kimi CLI
    if not check_kimi_cli():
        print("❌ 未检测到 Kimi CLI")
        print("   请先安装 Kimi Code CLI: https://kimi.com")
        sys.exit(1)
    
    print("✅ 已检测到 Kimi CLI")
    
    # 检查当前认证状态
    creds = read_credentials()
    
    if creds:
        print(f"\n📄 发现已有凭证文件: {KIMI_CREDENTIALS_PATH}")
        
        # 检查是否过期
        import time
        expires_at = creds.get("expires_at")
        if expires_at:
            expires_in = expires_at - time.time()
            if expires_in > 0:
                print(f"   凭证有效，将在 {int(expires_in / 60)} 分钟后过期")
            else:
                print(f"   凭证已过期，需要刷新")
                if refresh_token():
                    print("\n✅ 认证设置完成")
                    return
        else:
            print("   凭证状态未知")
    else:
        print(f"\n⚠️  未找到凭证文件: {KIMI_CREDENTIALS_PATH}")
    
    # 提示用户登录
    print("\n📝 请运行以下命令登录 Kimi Code:")
    print("   kimi --login")
    print("\n   或检查当前登录状态:")
    print("   kimi whoami")
    
    # 尝试自动刷新
    if creds:
        print("\n🔄 尝试自动刷新 token...")
        if refresh_token():
            print("\n✅ 认证设置完成")
        else:
            print("\n⚠️  自动刷新失败，请手动登录")


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Kimi Code 认证辅助工具")
    parser.add_argument("--check", action="store_true", help="检查认证状态")
    parser.add_argument("--refresh", action="store_true", help="刷新 token")
    parser.add_argument("--setup", action="store_true", help="运行设置向导")
    
    args = parser.parse_args()
    
    if args.check:
        creds = read_credentials()
        if creds:
            print(f"✅ 凭证文件存在: {KIMI_CREDENTIALS_PATH}")
            expires_at = creds.get("expires_at")
            if expires_at:
                import time
                expires_in = expires_at - time.time()
                if expires_in > 0:
                    print(f"   有效，将在 {int(expires_in / 60)} 分钟后过期")
                else:
                    print(f"   已过期 {int(-expires_in / 60)} 分钟")
        else:
            print(f"❌ 未找到凭证文件: {KIMI_CREDENTIALS_PATH}")
    
    elif args.refresh:
        if refresh_token():
            print("✅ 刷新成功")
        else:
            print("❌ 刷新失败")
            sys.exit(1)
    
    else:
        setup_auth()


if __name__ == "__main__":
    main()
