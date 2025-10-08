import os
import subprocess
import sqlite3
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


# 获取 Chrome 的主密钥从 Keychain（使用 security 命令）
def get_master_key():
    # 调用 macOS security 工具获取 "Chrome Safe Storage" 的密码
    # 这可能会弹出密码提示
    try:
        output = subprocess.check_output(
            ['security', 'find-generic-password', '-ga', 'Chrome'],
            stderr=subprocess.DEVNULL
        ).decode()
        # 解析输出，提取密码部分（格式如 "password: \"your_key\"")
        for line in output.splitlines():
            if line.startswith('password: '):
                return line.split('"')[1].encode()  # 返回字节
        raise ValueError("无法从 Keychain 获取密钥")
    except subprocess.CalledProcessError:
        raise ValueError("Keychain 访问失败 - 可能需要解锁或权限")


# 派生解密密钥（使用 PBKDF2）
def derive_key(master_key, salt=b'saltysalt', iterations=1003, key_length=32):
    backend = default_backend()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA1(),
        length=key_length,
        salt=salt,
        iterations=iterations,
        backend=backend
    )
    return kdf.derive(master_key)


# 解密单个密码
def decrypt_password(encrypted_password, key):
    try:
        # macOS 上 Chrome 使用 v10 格式：前3字节是 'v10' 或类似
        if encrypted_password.startswith(b'v10') or encrypted_password.startswith(b'v11'):
            iv = encrypted_password[3:15]  # IV 是 12 字节
            ciphertext = encrypted_password[15:]
            aesgcm = AESGCM(key)
            decrypted = aesgcm.decrypt(iv, ciphertext, None)
            return decrypted.decode('utf-8')
        else:
            return "不支持的加密格式"
    except Exception as e:
        return f"解密失败: {str(e)}"


# 主函数：读取 Chrome 密码
def get_chrome_passwords():
    # 获取主密钥并派生
    master_key = get_master_key()
    derived_key = derive_key(master_key)

    # Chrome 密码数据库路径
    login_db_path = os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Login Data')

    # 为了安全，先复制到临时文件（避免锁定）
    temp_db = '/tmp/chrome_login_data.db'
    subprocess.call(['cp', login_db_path, temp_db])

    # 连接 SQLite
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT origin_url, username_value, password_value FROM logins")

    for row in cursor.fetchall():
        url = row[0]
        username = row[1]
        encrypted_pass = row[2]  # 这是加密的字节
        decrypted = decrypt_password(encrypted_pass, derived_key)
        print(f"URL: {url}\nUsername: {username}\nPassword: {decrypted}\n{'-' * 40}")

    conn.close()
    os.remove(temp_db)  # 清理临时文件


# 运行
if __name__ == "__main__":
    try:
        get_chrome_passwords()
    except Exception as e:
        print(f"错误: {str(e)}")