# DMR API 快速调试指南

## 1. Postman 配置导入

### 导入集合和环境
1. 打开 Postman
2. 点击 "Import" 按钮
3. 导入 `postman_collection.json` (API集合)
4. 导入 `postman_environment.json` (环境变量)
5. 选择 "DMR Development Environment" 环境

### 设置认证
1. 首先运行 "Authentication" → "Login (Token Auth)" 请求
2. 修改请求体中的用户名和密码
3. 发送请求后，token 会自动保存到环境变量
4. 后续所有请求都会自动使用这个 token

## 2. 其他快速调试方法

### 使用 Django REST Framework 浏览器界面
访问: http://localhost:8000/api/patients/patients/
- 提供友好的 Web 界面
- 可以直接在浏览器中测试 API
- 支持表单提交和 JSON 数据

### 使用 Swagger UI 文档
访问: http://localhost:8000/schema/swagger-ui/
- 自动生成的 API 文档
- 可以直接在界面中测试 API
- 包含完整的请求/响应示例

### 使用 curl 命令行测试

#### 1. 获取 token (如果需要认证)
```bash
curl -X POST http://localhost:8000/api-auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

#### 2. 测试患者 API
```bash
# 获取患者列表
curl -X GET http://localhost:8000/api/patients/patients/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# 创建患者
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
```

#### 3. 测试观察记录 API
```bash
# 创建多个观察记录
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

# 获取用户和患者的观察记录
curl -X GET "http://localhost:8000/api/student-groups/observations/?user=1&patient=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 使用 Python requests 测试

创建测试脚本 `test_api.py`:

```python
import requests
import json

# 配置
BASE_URL = "http://localhost:8000"
USERNAME = "your_username"
PASSWORD = "your_password"

# 获取 token
def get_token():
    response = requests.post(f"{BASE_URL}/api-auth/login/", 
                           json={"username": USERNAME, "password": PASSWORD})
    if response.status_code == 200:
        return response.json().get("token")
    return None

# 测试患者 API
def test_patients_api(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    # 获取患者列表
    response = requests.get(f"{BASE_URL}/api/patients/patients/", headers=headers)
    print(f"患者列表: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    
    # 创建患者
    patient_data = {
        "first_name": "李",
        "last_name": "四",
        "date_of_birth": "1985-06-15",
        "email": "lisi@example.com",
        "phone_number": "13900139000"
    }
    response = requests.post(f"{BASE_URL}/api/patients/patients/", 
                           json=patient_data, headers=headers)
    print(f"创建患者: {response.status_code}")
    if response.status_code == 201:
        patient_id = response.json()["id"]
        print(f"新患者ID: {patient_id}")
        return patient_id
    return None

# 测试观察记录 API
def test_observations_api(token, patient_id=1, user_id=1):
    headers = {"Authorization": f"Bearer {token}"}
    
    # 创建观察记录
    observation_data = {
        "blood_pressure": {
            "patient": patient_id,
            "user": user_id,
            "systolic": 125,
            "diastolic": 82
        },
        "heart_rate": {
            "patient": patient_id,
            "user": user_id,
            "heart_rate": 75
        },
        "body_temperature": {
            "patient": patient_id,
            "user": user_id,
            "temperature": "36.8"
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/student-groups/observations/", 
                           json=observation_data, headers=headers)
    print(f"创建观察记录: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    
    # 获取观察记录
    response = requests.get(f"{BASE_URL}/api/student-groups/observations/",
                          params={"user": user_id, "patient": patient_id},
                          headers=headers)
    print(f"获取观察记录: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

# 主函数
if __name__ == "__main__":
    token = get_token()
    if token:
        print(f"Token 获取成功: {token[:20]}...")
        patient_id = test_patients_api(token)
        test_observations_api(token, patient_id or 1)
    else:
        print("无法获取 token，请检查用户名和密码")
```

## 3. 数据验证检查清单

### 患者数据验证
- [ ] 姓名字段不为空
- [ ] 邮箱格式正确且唯一
- [ ] 出生日期格式正确 (YYYY-MM-DD)
- [ ] 电话号码格式验证

### 观察记录验证
- [ ] 血压值在合理范围内 (收缩压: 90-200, 舒张压: 60-120)
- [ ] 心率在合理范围内 (40-200 bpm)
- [ ] 体温在合理范围内 (35.0-42.0°C)
- [ ] 患者和用户ID存在

### 文件上传验证
- [ ] 文件大小限制
- [ ] 文件类型检查
- [ ] 文件名称处理

## 4. 常见问题排查

### 认证问题
- 检查 token 是否正确
- 确认用户账户是否激活
- 验证权限设置

### 数据格式问题
- JSON 格式是否正确
- 日期时间格式是否符合要求
- 必填字段是否完整

### 服务器错误
- 检查服务器日志
- 验证数据库连接
- 确认模型验证规则

## 5. 性能测试

### 使用 Apache Bench (ab)
```bash
# 测试患者列表API性能
ab -n 100 -c 10 -H "Authorization: Bearer YOUR_TOKEN" \
   http://localhost:8000/api/patients/patients/
```

### 使用 wrk
```bash
# 安装 wrk 后测试
wrk -t12 -c400 -d30s -H "Authorization: Bearer YOUR_TOKEN" \
    http://localhost:8000/api/patients/patients/
```

这个指南提供了多种方式来快速调试和验证您的API，选择最适合您工作流程的方法即可。
