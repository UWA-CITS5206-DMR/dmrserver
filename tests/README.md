# DMR Login Integration Tests

## 概述

这个目录包含了DMR系统登录功能的完整集成测试套件。测试覆盖了会话认证、API访问控制、用户数据隔离等关键功能。

## 测试文件结构

```
tests/
├── README.md                    # 本文件 - 测试说明文档
├── __init__.py                  # Python包初始化文件
├── test_config.py              # 测试配置和数据管理
├── test_login_integration.py   # Django集成测试套件
├── test_login_manual.py        # 手动测试工具
└── quick_login_test.py         # 快速测试脚本
```

## 快速开始

### 1. 最简单的测试方式

```bash
# 快速检查登录功能（需要服务器已运行）
python tests/quick_login_test.py

# 或者使用自定义凭据测试
python tests/quick_login_test.py custom
```

### 2. 运行完整测试套件

```bash
# 运行所有登录相关测试（自动启动服务器）
./run_login_tests.sh

# 或者运行特定类型的测试
./run_login_tests.sh django      # Django集成测试
./run_login_tests.sh manual      # 手动测试场景
./run_login_tests.sh api         # API端点测试
./run_login_tests.sh performance # 性能测试
```

### 3. 运行Django测试

```bash
# 使用Django测试框架
./start.sh test tests.test_login_integration

# 或者直接使用manage.py
uv run python manage.py test tests.test_login_integration --verbosity=2
```

## 测试详细说明

### 1. 快速测试脚本 (`quick_login_test.py`)

**用途**: 快速验证基本登录功能是否正常

**特点**:
- 🚀 启动快速，无需额外设置
- 🔍 自动检测服务器状态
- 🔒 测试基本认证流程
- 📊 提供清晰的测试结果

**使用方法**:
```bash
# 基本测试
python tests/quick_login_test.py

# 自定义凭据测试
python tests/quick_login_test.py custom

# 查看帮助
python tests/quick_login_test.py --help
```

**测试内容**:
- ✅ 服务器可用性检查
- ✅ 登录页面访问
- ✅ 未认证API访问拒绝
- ✅ Django管理界面访问
- ✅ API文档访问
- ✅ 基本登录功能测试

### 2. Django集成测试 (`test_login_integration.py`)

**用途**: 全面的Django框架集成测试

**特点**:
- 🧪 使用Django测试框架
- 🔄 自动创建和清理测试数据
- 📝 详细的测试报告
- 🛡️ 安全性测试

**测试类别**:

#### `SessionAuthenticationTests`
- 有效凭据登录测试
- 无效凭据登录测试
- 注销会话清理测试

#### `APIAccessControlTests`
- 未认证访问拒绝测试
- 认证访问允许测试
- 会话持久性测试

#### `AuthenticationWorkflowTests`
- 完整登录到API使用流程
- 多用户会话测试

#### `SecurityTests`
- 会话超时行为测试
- CSRF保护测试
- 登录频率限制模拟

#### `AdminAccessTests`
- 管理员登录和访问测试
- 非管理员访问限制测试

#### `DataIsolationTests`
- 用户数据关联测试
- 数据访问隔离测试

### 3. 手动测试工具 (`test_login_manual.py`)

**用途**: 提供编程方式的手动测试工具

**特点**:
- 🔧 可编程的测试场景
- 📡 真实HTTP请求测试
- 🎯 灵活的测试配置
- 📊 详细的响应分析

**主要类**:

#### `DMRLoginTester`
```python
# 创建测试器实例
tester = DMRLoginTester()

# 检查服务器状态
tester.test_server_availability()

# 登录测试
tester.login('username', 'password')

# API端点测试
tester.test_api_endpoints()

# 创建测试数据
tester.create_test_data()

# 注销测试
tester.logout()

# 运行完整测试场景
tester.run_complete_test_scenario('username', 'password')
```

### 4. 测试配置 (`test_config.py`)

**用途**: 统一的测试配置和数据管理

**主要功能**:
- 🔧 测试配置管理
- 👥 测试用户创建
- 🏥 测试患者数据管理
- 🧹 测试数据清理

**配置项**:
```python
TEST_CONFIG = {
    'BASE_URL': 'http://127.0.0.1:8000',
    'TEST_USERS': {
        'doctor': {...},
        'nurse': {...},
        'admin': {...}
    },
    'ENDPOINTS': {...},
    'TEST_PATIENT': {...},
    'TEST_OBSERVATIONS': {...}
}
```

### 5. 测试运行脚本 (`run_login_tests.sh`)

**用途**: 自动化测试运行和环境管理

**特点**:
- 🚀 自动启动/停止服务器
- 👥 自动创建测试用户
- 📊 多种测试模式
- 🧹 自动清理环境

**使用方法**:
```bash
# 查看帮助
./run_login_tests.sh help

# 运行所有测试
./run_login_tests.sh all

# 运行特定测试类型
./run_login_tests.sh django
./run_login_tests.sh manual  
./run_login_tests.sh api
./run_login_tests.sh performance
```

## 测试数据

### 默认测试用户

测试脚本会自动创建以下测试用户：

| 用户名 | 密码 | 角色 | 权限 |
|--------|------|------|------|
| `test_doctor` | `doctor_password_123` | 医生 | 普通用户 |
| `test_nurse` | `nurse_password_123` | 护士 | 普通用户 |
| `test_admin` | `admin_password_123` | 管理员 | 超级用户 |

### 测试患者数据

```json
{
    "first_name": "John",
    "last_name": "TestPatient",
    "date_of_birth": "1990-01-01",
    "email": "test_patient@dmr-test.com",
    "phone_number": "+1234567890"
}
```

## 测试场景

### 1. 基本认证流程

```
1. 用户访问登录页面
2. 输入有效凭据
3. 系统创建会话
4. 用户可以访问受保护的API
5. 用户注销
6. 会话被清除，无法访问受保护资源
```

### 2. API访问控制

```
1. 未认证用户访问API → 401 Unauthorized
2. 用户登录 → 获得会话
3. 认证用户访问API → 200 OK
4. 用户注销 → 会话清除
5. 再次访问API → 401 Unauthorized
```

### 3. 数据创建和关联

```
1. 用户登录
2. 创建患者记录
3. 添加患者备注 → 自动关联到当前用户
4. 记录生命体征 → 自动关联到当前用户
5. 验证数据正确关联
```

### 4. 多用户会话

```
1. 医生用户登录（会话A）
2. 护士用户登录（会话B）
3. 两个用户并行操作，互不干扰
4. 验证数据正确关联到各自用户
```

## 故障排除

### 常见问题

#### 1. 服务器连接失败
```
❌ Cannot connect to DMR server
```
**解决方案**:
```bash
# 启动服务器
./start.sh dev

# 或后台启动
./start.sh dev-bg

# 检查状态
./start.sh status
```

#### 2. 测试用户不存在
```
❌ Login failed with username/password
```
**解决方案**:
```bash
# 运行测试设置脚本
python tests/test_config.py

# 或者手动创建用户
./start.sh shell
>>> from django.contrib.auth.models import User
>>> User.objects.create_user('testuser', 'test@test.com', 'testpass')
```

#### 3. 数据库迁移问题
```
❌ No such table: patients_patient
```
**解决方案**:
```bash
# 运行数据库迁移
./start.sh migrate
```

#### 4. 权限错误
```
❌ Permission denied
```
**解决方案**:
```bash
# 给脚本添加执行权限
chmod +x run_login_tests.sh
chmod +x tests/quick_login_test.py
```

### 调试技巧

#### 1. 启用详细输出
```bash
# Django测试详细输出
uv run python manage.py test tests.test_login_integration --verbosity=2

# 测试脚本详细输出
./run_login_tests.sh django  # 已包含详细输出
```

#### 2. 检查服务器日志
```bash
# 查看服务器日志
./start.sh logs

# 或者直接查看日志文件
tail -f dmr_server.log
```

#### 3. 手动验证
```bash
# 快速检查基本功能
python tests/quick_login_test.py

# 交互式测试
python tests/quick_login_test.py custom
```

#### 4. 数据库检查
```bash
# 进入Django shell检查数据
./start.sh shell

# 检查用户
>>> from django.contrib.auth.models import User
>>> User.objects.all()

# 检查患者
>>> from patients.models import Patient
>>> Patient.objects.all()
```

## 性能基准

### 预期性能指标

| 操作 | 预期时间 | 描述 |
|------|----------|------|
| 登录请求 | < 1秒 | 用户登录响应时间 |
| API响应 | < 500ms | 受保护端点响应时间 |
| 注销请求 | < 300ms | 用户注销响应时间 |
| 数据创建 | < 1秒 | 创建患者记录/备注 |

### 运行性能测试

```bash
# 运行性能测试
./run_login_tests.sh performance

# 输出示例：
# Login attempt 1: 0.234s
# Login attempt 2: 0.198s
# Login attempt 3: 0.245s
# Average login time: 0.226s
# ✅ Login performance is good
```

## 扩展测试

### 添加新的测试用例

1. **修改测试配置** (`test_config.py`)
```python
# 添加新的测试用户
TEST_CONFIG['TEST_USERS']['new_role'] = {
    'username': 'new_user',
    'password': 'new_password',
    # ...其他配置
}
```

2. **添加Django测试** (`test_login_integration.py`)
```python
class NewTestCase(LoginIntegrationTestCase):
    def test_new_functionality(self):
        # 新的测试逻辑
        pass
```

3. **添加手动测试场景** (`test_login_manual.py`)
```python
def test_new_scenario(self):
    # 新的测试场景
    pass
```

### 集成到CI/CD

```yaml
# GitHub Actions示例
- name: Run Login Tests
  run: |
    ./start.sh init
    ./run_login_tests.sh all
```

## 最佳实践

### 测试编写建议

1. **使用描述性的测试名称**
```python
def test_doctor_can_create_patient_note_after_login(self):
    # 清楚描述测试目的
```

2. **遵循AAA模式**
```python
def test_example(self):
    # Arrange - 准备测试数据
    user = self.create_test_user()
    
    # Act - 执行测试操作
    response = self.client.post('/login/', credentials)
    
    # Assert - 验证结果
    self.assertEqual(response.status_code, 200)
```

3. **使用有意义的断言消息**
```python
self.assertEqual(
    response.status_code, 
    200, 
    "Login should succeed with valid credentials"
)
```

4. **保持测试独立性**
```python
def setUp(self):
    # 每个测试都有干净的起始状态
    self.client = APIClient()
    self.user = User.objects.create_user(...)
```

### 测试维护

1. **定期运行测试**
```bash
# 每次代码变更后
./run_login_tests.sh

# 每日构建
./run_login_tests.sh all
```

2. **更新测试数据**
```python
# 当模型变更时，更新测试配置
TEST_CONFIG['TEST_PATIENT']['new_field'] = 'new_value'
```

3. **监控测试性能**
```bash
# 定期检查测试执行时间
time ./run_login_tests.sh performance
```

## 总结

这套登录集成测试提供了：

- ✅ **全面覆盖**: 从快速检查到深度集成测试
- ✅ **易于使用**: 简单的命令行界面
- ✅ **自动化**: 自动环境设置和清理
- ✅ **可扩展**: 容易添加新的测试场景
- ✅ **实用性**: 真实的HTTP请求测试
- ✅ **维护性**: 清晰的代码组织和文档

无论是开发过程中的快速验证，还是部署前的全面测试，这套工具都能满足您的需求。
