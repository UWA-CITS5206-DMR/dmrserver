#!/bin/bash

# DMR API 快速测试启动脚本

set -e

echo "🚀 DMR API 快速测试工具"
echo "========================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3"
    exit 1
fi

# 检查是否安装了requests库
if ! python3 -c "import requests" &> /dev/null; then
    echo "⚠️ 警告: 未安装requests库，正在安装..."
    pip3 install requests
fi

# 检查服务器是否运行
echo "🔍 检查服务器状态..."
if curl -s "http://localhost:8000/schema/" > /dev/null; then
    echo "✅ 服务器运行正常"
else
    echo "❌ 服务器未运行或无法访问"
    echo "请先启动Django服务器: python manage.py runserver"
    exit 1
fi

# 获取用户凭据
echo ""
echo "🔐 认证信息 (可选，直接回车跳过):"
read -p "用户名: " USERNAME
if [ ! -z "$USERNAME" ]; then
    read -s -p "密码: " PASSWORD
    echo ""
else
    PASSWORD=""
fi

echo ""
echo "📋 选择测试模式:"
echo "1. 快速完整测试"
echo "2. 交互式测试"
echo "3. 仅测试文档端点"
echo "4. 生成curl命令示例"

read -p "请选择 (1-4): " CHOICE

case $CHOICE in
    1)
        echo "🏃 运行快速完整测试..."
        python3 quick_api_test.py --username "$USERNAME" --password "$PASSWORD"
        ;;
    2)
        echo "🎮 启动交互式测试..."
        python3 quick_api_test.py --username "$USERNAME" --password "$PASSWORD" --interactive
        ;;
    3)
        echo "📚 测试文档端点..."
        echo "🌐 Swagger UI: http://localhost:8000/schema/swagger-ui/"
        echo "📄 OpenAPI Schema: http://localhost:8000/schema/"
        
        if command -v open &> /dev/null; then
            read -p "是否打开Swagger UI? (y/n): " OPEN_SWAGGER
            if [ "$OPEN_SWAGGER" = "y" ] || [ "$OPEN_SWAGGER" = "Y" ]; then
                open "http://localhost:8000/schema/swagger-ui/"
            fi
        fi
        ;;
    4)
        echo "📝 生成curl命令示例..."
        cat << 'EOF'

# 基本curl命令示例

# 1. 获取API Schema
curl -X GET http://localhost:8000/schema/ \
  -H "Accept: application/json"

# 2. 如果需要认证，先获取token
curl -X POST http://localhost:8000/api-auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# 3. 获取患者列表 (需要token)
curl -X GET http://localhost:8000/api/patients/patients/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. 创建患者
curl -X POST http://localhost:8000/api/patients/patients/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "first_name": "张",
    "last_name": "三",
    "date_of_birth": "1990-01-01", 
    "email": "zhangsan@example.com",
    "phone_number": "13800138000"
  }'

# 5. 创建观察记录
curl -X POST http://localhost:8000/api/student-groups/observations/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "blood_pressure": {
      "patient": 1,
      "user": 1,
      "systolic": 120,
      "diastolic": 80
    },
    "heart_rate": {
      "patient": 1,
      "user": 1,
      "heart_rate": 72
    }
  }'

# 6. 获取特定用户和患者的观察记录
curl -X GET "http://localhost:8000/api/student-groups/observations/?user=1&patient=1" \
  -H "Authorization: Bearer YOUR_TOKEN"

EOF
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "✨ 测试完成!"
echo ""
echo "📁 相关文件:"
echo "   - Postman集合: postman_collection.json"
echo "   - Postman环境: postman_environment.json" 
echo "   - 测试指南: api_test_guide.md"
echo "   - Python测试脚本: quick_api_test.py"
