#!/bin/bash
# Benome 服务健康检查脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMPLATES_DIR="${BASE_DIR}/apps/web/templates"
ENV_FILE="${BASE_DIR}/.env"
DB_FILE="${BASE_DIR}/data/benome.sqlite"
LOG_FILE="${BASE_DIR}/logs/benome.log"

echo "======================================"
echo "  Benome 服务健康检查"
echo "======================================"
echo ""

# 检查服务状态
echo "1️⃣  检查服务状态..."
if systemctl is-active --quiet benome.service; then
    echo "   ✅ Benome 服务运行正常"
else
    echo "   ❌ Benome 服务未运行"
    exit 1
fi

# 检查端口
echo ""
echo "2️⃣  检查端口监听..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8200 | grep -q "200\|302"; then
    echo "   ✅ 端口 8200 正常监听"
else
    echo "   ❌ 端口 8200 无法访问"
    exit 1
fi

# 检查首页
echo ""
echo "3️⃣  检查首页..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8200/)
if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ 首页访问正常 (HTTP $HTTP_CODE)"
else
    echo "   ⚠️  首页访问异常 (HTTP $HTTP_CODE)"
fi

# 检查 API 文档
echo ""
echo "4️⃣  检查 API 文档..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8200/docs)
if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ API 文档访问正常 (HTTP $HTTP_CODE)"
else
    echo "   ⚠️  API 文档访问异常 (HTTP $HTTP_CODE)"
fi

# 检查管理员页面（应该重定向）
echo ""
echo "5️⃣  检查管理员页面..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8200/admin/dashboard)
if [ "$HTTP_CODE" = "302" ]; then
    echo "   ✅ 管理员页面重定向正常 (HTTP $HTTP_CODE，需要登录)"
else
    echo "   ⚠️  管理员页面访问异常 (HTTP $HTTP_CODE)"
fi

# 检查模板文件
echo ""
echo "6️⃣  检查模板文件..."
TEMPLATES=(
    "admin_dashboard.html"
    "admin_media_manage.html"
    "dashboard.html"
    "property_detail.html"
    "index.html"
)

for template in "${TEMPLATES[@]}"; do
    if [ -f "${TEMPLATES_DIR}/${template}" ]; then
        SIZE=$(wc -c < "${TEMPLATES_DIR}/${template}")
        echo "   ✅ $template ($SIZE bytes)"
    else
        echo "   ❌ $template 不存在"
    fi
done

# 检查 OSS 配置
echo ""
echo "7️⃣  检查 OSS 配置..."
if [ -f "${ENV_FILE}" ]; then
    if grep -q "ALIYUN_OSS_ACCESS_KEY_ID" "${ENV_FILE}"; then
        echo "   ✅ OSS 配置已设置"
    else
        echo "   ⚠️  OSS 配置未设置（媒体上传功能将不可用）"
    fi
else
    echo "   ⚠️  .env 文件不存在（使用默认配置或环境变量）"
fi

# 检查数据库
echo ""
echo "8️⃣  检查数据库..."
if [ -f "${DB_FILE}" ]; then
    echo "   ✅ 数据库文件存在"
    
    # 检查 property_media 表是否存在
    if sqlite3 "${DB_FILE}" ".tables" | grep -q "property_media"; then
        echo "   ✅ property_media 表已创建"
        
        # 统计媒体数量
        MEDIA_COUNT=$(sqlite3 "${DB_FILE}" "SELECT COUNT(*) FROM property_media;")
        echo "   📊 媒体文件数量：$MEDIA_COUNT"
    else
        echo "   ⚠️  property_media 表不存在（需要运行迁移）"
    fi
else
    echo "   ⚠️  数据库文件不存在"
fi

# 检查日志
echo ""
echo "9️⃣  检查最近日志..."
if [ -f "${LOG_FILE}" ]; then
    echo "   📄 最新日志："
    tail -3 "${LOG_FILE}" | sed 's/^/      /'
else
    echo "   ⚠️  日志文件不存在"
fi

echo ""
echo "======================================"
echo "  健康检查完成！"
echo "======================================"
echo ""
echo "📍 访问地址："
echo "   首页：http://localhost:8200/"
echo "   管理后台：http://localhost:8200/admin/dashboard"
echo "   API 文档：http://localhost:8200/docs"
echo ""
echo "📚 文档位置："
echo "   ${BASE_DIR}/docs/guides/UPLOAD_GUIDE.md"
echo "   ${BASE_DIR}/docs/guides/OSS_CONFIG.md"
echo "   ${BASE_DIR}/docs/guides/TEMPLATE_STRUCTURE.md"
echo ""
