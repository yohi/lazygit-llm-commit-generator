#!/usr/bin/env python3
"""
ネットワーク接続確認ユーティリティ

Gemini CLI実行前のネットワーク環境確認に使用
"""

import socket
import subprocess
import time
import sys
from typing import Tuple, List


def check_dns_resolution(hostname: str = "google.com") -> Tuple[bool, str]:
    """
    DNS解決の確認

    Args:
        hostname: 確認するホスト名

    Returns:
        (成功/失敗, メッセージ)
    """
    try:
        # ホスト名の基本検証
        if not hostname or len(hostname) > 255:
            return False, f"無効なホスト名: {hostname}"

        socket.gethostbyname(hostname)
        return True, f"DNS解決成功: {hostname}"
    except socket.gaierror as e:
        return False, f"DNS解決失敗: {hostname} ({str(e)})"
    except Exception as e:
        return False, f"DNS解決エラー: {hostname} (予期しないエラー)"


def check_internet_connectivity(host: str = "8.8.8.8", port: int = 53, timeout: int = 3) -> Tuple[bool, str]:
    """
    インターネット接続の確認

    Args:
        host: 接続先ホスト
        port: 接続先ポート
        timeout: タイムアウト秒数

    Returns:
        (成功/失敗, メッセージ)
    """
    try:
        socket.setdefaulttimeout(timeout)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
        return True, f"インターネット接続確認済み: {host}:{port}"
    except socket.error as e:
        return False, f"インターネット接続失敗: {host}:{port} ({str(e)})"


def check_google_api_connectivity() -> Tuple[bool, str]:
    """
    Google API接続の確認

    Returns:
        (成功/失敗, メッセージ)
    """
    return check_internet_connectivity("generativelanguage.googleapis.com", 443, 5)


def ping_test(host: str = "google.com") -> Tuple[bool, str]:
    """
    Pingテスト

    Args:
        host: Ping送信先ホスト

    Returns:
        (成功/失敗, メッセージ)
    """
    try:
        # ホスト名の基本検証
        if not host or len(host) > 255:
            return False, f"無効なホスト名: {host}"

        # Windows/Linux対応
        ping_cmd = ["ping", "-c", "1"] if sys.platform != "win32" else ["ping", "-n", "1"]
        ping_cmd.append(host)

        result = subprocess.run(
            ping_cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False  # 明示的にcheck=Falseを設定
        )

        if result.returncode == 0:
            return True, f"Ping成功: {host}"
        else:
            return False, f"Ping失敗: {host} (戻り値: {result.returncode})"

    except subprocess.TimeoutExpired:
        return False, f"Pingタイムアウト: {host}"
    except (subprocess.SubprocessError, OSError) as e:
        return False, f"Pingエラー: {host} ({str(e)})"


def comprehensive_network_check() -> List[Tuple[str, bool, str]]:
    """
    包括的なネットワーク確認

    Returns:
        [(チェック名, 成功/失敗, メッセージ), ...]
    """
    checks = []

    # DNS解決確認
    success, msg = check_dns_resolution("google.com")
    checks.append(("DNS解決", success, msg))

    # インターネット接続確認
    success, msg = check_internet_connectivity()
    checks.append(("インターネット接続", success, msg))

    # Google API接続確認
    success, msg = check_google_api_connectivity()
    checks.append(("Google API接続", success, msg))

    # Pingテスト
    success, msg = ping_test("8.8.8.8")
    checks.append(("Ping (8.8.8.8)", success, msg))

    return checks


def print_network_status() -> bool:
    """
    ネットワーク状態を表示

    Returns:
        全てのネットワークチェックが成功した場合True
    """
    print("🌐 ネットワーク接続確認中...")
    print("=" * 50)

    checks = comprehensive_network_check()

    all_passed = True
    for check_name, success, message in checks:
        status = "✅ OK" if success else "❌ NG"
        print(f"{status} {check_name}: {message}")
        if not success:
            all_passed = False

    print("=" * 50)

    if all_passed:
        print("✅ 全てのネットワークチェックが成功しました")
        print("Gemini CLIが動作しない場合は、以下を確認してください:")
        print("  - geminiコマンドのインストール状況")
        print("  - Google Cloud認証設定")
        print("  - APIキー設定(必要な場合)")
    else:
        print("❌ ネットワーク接続に問題があります")
        print("\n🔧 対処方法:")
        print("  1. インターネット接続を確認してください")
        print("  2. プロキシ設定を確認してください")
        print("  3. ファイアウォール設定を確認してください")
        print("  4. VPN接続状況を確認してください")
        print("  5. 少し時間をおいて再試行してください")

    return all_passed


if __name__ == "__main__":
    print_network_status()
