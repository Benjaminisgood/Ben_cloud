#!/bin/bash
# Benome 媒体功能测试脚本
# 使用方法：./test_media_upload.sh <property_id> <file_path>

set -e

PROPERTY_ID=${1:-1}
FILE_PATH=${2:-}

if [ -z "$FILE_PATH" ]; then
    echo "❌ 请提供文件路径"
    echo "用法：$0 <property_id> <file_path>"
    echo "示例：$0 1 /path/to/image.jpg"
    exit 1
fi

if [ ! -f "$FILE_PATH" ]; then
    echo "❌ 文件不存在：$FILE_PATH"
    exit 1
fi

echo "📤 测试上传媒体文件"
echo "房间 ID: $PROPERTY_ID"
echo "文件：$FILE_PATH"
echo ""

# 获取管理员会话（需要先登录）
echo "⚠️  注意：需要先通过 Benbot SSO 登录获取会话 cookie"
echo "请手动访问 http://localhost:8200/auth/sso?token=YOUR_TOKEN 登录"
echo ""

# 示例 curl 命令
cat << EOF
使用以下 curl 命令上传文件：

curl -X POST "http://localhost:8200/api/properties/${PROPERTY_ID}/media/upload" \\
  -H "Cookie: session=YOUR_SESSION_COOKIE" \\
  -F "file=@${FILE_PATH}" \\
  -F "title=测试图片" \\
  -F "description=这是一张测试图片" \\
  -F "is_cover=false"

或者使用 Python 脚本：

python3 << 'PYTHON'
import requests

# 需要先登录获取 session cookie
session = requests.Session()
# session.cookies.set('session', 'YOUR_COOKIE')

with open('${FILE_PATH}', 'rb') as f:
    files = {'file': f}
    data = {
        'title': '测试图片',
        'description': '这是一张测试图片',
        'is_cover': 'false'
    }
    response = session.post(
        f'http://localhost:8200/api/properties/${PROPERTY_ID}/media/upload',
        files=files,
        data=data
    )
    print(response.json())
PYTHON

EOF

echo ""
echo "📋 查看媒体列表："
echo "curl http://localhost:8200/api/properties/${PROPERTY_ID}/media"
echo ""
echo "🌐 查看房间详情页："
echo "http://localhost:8200/properties/${PROPERTY_ID}"
