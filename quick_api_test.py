#!/usr/bin/env python3
"""
DMR API 快速测试脚本
用于快速验证API功能是否正常
"""

import requests
import json
import sys
from datetime import datetime


class DMRAPITester:
    def __init__(self, base_url="http://localhost:8000", username="", password=""):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
        self.session = requests.Session()
    
    def log(self, message, level="INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def get_token(self):
        """获取认证token"""
        if not self.username or not self.password:
            self.log("未提供用户名和密码，跳过认证", "WARN")
            return False
        
        try:
            response = self.session.post(
                f"{self.base_url}/api-auth/login/",
                json={"username": self.username, "password": self.password}
            )
            
            if response.status_code == 200:
                self.token = response.json().get("token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                self.log(f"Token 获取成功: {self.token[:20]}...")
                return True
            else:
                self.log(f"Token 获取失败: {response.status_code} - {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Token 获取异常: {e}", "ERROR")
            return False
    
    def test_api_endpoint(self, method, endpoint, data=None, expected_status=200, description=""):
        """测试API端点"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=data)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            else:
                self.log(f"不支持的HTTP方法: {method}", "ERROR")
                return False
            
            success = response.status_code == expected_status
            status_icon = "✅" if success else "❌"
            
            self.log(f"{status_icon} {method.upper()} {endpoint} - {response.status_code} ({description})")
            
            if not success:
                self.log(f"   期望状态码: {expected_status}, 实际: {response.status_code}")
                self.log(f"   响应内容: {response.text[:200]}...")
            
            # 如果是JSON响应，尝试格式化输出
            if response.headers.get("content-type", "").startswith("application/json"):
                try:
                    json_data = response.json()
                    if success and len(str(json_data)) < 500:  # 只显示短响应
                        self.log(f"   响应数据: {json.dumps(json_data, ensure_ascii=False, indent=2)}")
                except:
                    pass
            
            return success, response
            
        except Exception as e:
            self.log(f"❌ {method.upper()} {endpoint} - 请求异常: {e}", "ERROR")
            return False, None
    
    def test_schema_endpoints(self):
        """测试文档和schema端点"""
        self.log("=== 测试API文档和Schema ===")
        
        # 测试OpenAPI schema
        self.test_api_endpoint("GET", "/schema/", expected_status=200, 
                             description="OpenAPI Schema")
        
        # 测试Swagger UI (返回HTML)
        success, response = self.test_api_endpoint("GET", "/schema/swagger-ui/", 
                                                 expected_status=200, 
                                                 description="Swagger UI")
        if success and response:
            is_html = "<!DOCTYPE html>" in response.text or "<html" in response.text
            if is_html:
                self.log("   ✅ Swagger UI 返回了HTML页面")
            else:
                self.log("   ⚠️ Swagger UI 响应格式异常")
    
    def test_patients_api(self):
        """测试患者API"""
        self.log("=== 测试患者API ===")
        
        # 测试获取患者列表
        success, response = self.test_api_endpoint("GET", "/api/patients/patients/", 
                                                 description="获取患者列表")
        
        # 测试创建患者
        patient_data = {
            "first_name": "测试",
            "last_name": "患者",
            "date_of_birth": "1990-01-01",
            "email": f"test.patient.{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com",
            "phone_number": "13800138000"
        }
        
        success, response = self.test_api_endpoint("POST", "/api/patients/patients/", 
                                                 data=patient_data, expected_status=201,
                                                 description="创建患者")
        
        patient_id = None
        if success and response:
            try:
                patient_id = response.json().get("id")
                self.log(f"   新创建的患者ID: {patient_id}")
            except:
                pass
        
        # 如果创建成功，测试获取患者详情
        if patient_id:
            self.test_api_endpoint("GET", f"/api/patients/patients/{patient_id}/", 
                                 description="获取患者详情")
            
            # 测试患者文件列表
            self.test_api_endpoint("GET", f"/api/patients/patients/{patient_id}/files/", 
                                 description="获取患者文件列表")
        
        return patient_id
    
    def test_student_groups_api(self, patient_id=1):
        """测试学生组API"""
        self.log("=== 测试学生组API ===")
        
        # 测试笔记API
        self.log("--- 测试笔记API ---")
        self.test_api_endpoint("GET", "/api/student-groups/notes/", 
                             description="获取笔记列表")
        
        note_data = {
            "patient": patient_id,
            "user": 1,  # 假设用户ID为1
            "content": f"测试笔记 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        
        success, response = self.test_api_endpoint("POST", "/api/student-groups/notes/", 
                                                 data=note_data, expected_status=201,
                                                 description="创建笔记")
        
        # 测试观察记录API
        self.log("--- 测试观察记录API ---")
        
        # 测试获取观察记录
        self.test_api_endpoint("GET", "/api/student-groups/observations/", 
                             data={"user": 1, "patient": patient_id},
                             description="获取观察记录")
        
        # 测试创建单一血压记录
        bp_data = {
            "blood_pressure": {
                "patient": patient_id,
                "user": 1,
                "systolic": 120,
                "diastolic": 80
            }
        }
        
        self.test_api_endpoint("POST", "/api/student-groups/observations/", 
                             data=bp_data, expected_status=201,
                             description="创建血压记录")
        
        # 测试创建多个观察记录
        multi_obs_data = {
            "blood_pressure": {
                "patient": patient_id,
                "user": 1,
                "systolic": 125,
                "diastolic": 82
            },
            "heart_rate": {
                "patient": patient_id,
                "user": 1,
                "heart_rate": 75
            },
            "body_temperature": {
                "patient": patient_id,
                "user": 1,
                "temperature": "36.8"
            }
        }
        
        self.test_api_endpoint("POST", "/api/student-groups/observations/", 
                             data=multi_obs_data, expected_status=201,
                             description="创建多个观察记录")
        
        # 测试各类型观察记录的单独端点
        self.log("--- 测试单独观察记录端点 ---")
        
        self.test_api_endpoint("GET", "/api/student-groups/observations/blood-pressures/", 
                             description="获取血压记录列表")
        
        self.test_api_endpoint("GET", "/api/student-groups/observations/heart-rates/", 
                             description="获取心率记录列表")
        
        self.test_api_endpoint("GET", "/api/student-groups/observations/body-temperatures/", 
                             description="获取体温记录列表")
    
    def run_full_test(self):
        """运行完整测试"""
        self.log("🚀 开始DMR API测试")
        self.log(f"测试服务器: {self.base_url}")
        
        # 获取认证token
        if self.username and self.password:
            if not self.get_token():
                self.log("认证失败，但继续进行无认证测试", "WARN")
        
        # 测试文档端点
        self.test_schema_endpoints()
        
        # 测试患者API
        patient_id = self.test_patients_api()
        
        # 测试学生组API
        self.test_student_groups_api(patient_id or 1)
        
        self.log("🏁 API测试完成")
    
    def interactive_test(self):
        """交互式测试"""
        print("\n=== DMR API 交互式测试 ===")
        print("请选择要测试的功能:")
        print("1. 完整测试")
        print("2. 仅测试文档端点")
        print("3. 仅测试患者API")
        print("4. 仅测试学生组API")
        print("5. 自定义端点测试")
        print("0. 退出")
        
        while True:
            choice = input("\n请输入选择 (0-5): ").strip()
            
            if choice == "0":
                print("退出测试")
                break
            elif choice == "1":
                self.run_full_test()
            elif choice == "2":
                self.test_schema_endpoints()
            elif choice == "3":
                patient_id = self.test_patients_api()
                print(f"创建的患者ID: {patient_id}")
            elif choice == "4":
                patient_id = input("请输入患者ID (默认1): ").strip() or "1"
                try:
                    patient_id = int(patient_id)
                    self.test_student_groups_api(patient_id)
                except ValueError:
                    print("无效的患者ID")
            elif choice == "5":
                method = input("请输入HTTP方法 (GET/POST/PUT/DELETE): ").strip().upper()
                endpoint = input("请输入端点路径 (如 /api/patients/patients/): ").strip()
                
                if method in ["POST", "PUT"]:
                    print("请输入JSON数据 (直接回车跳过):")
                    data_input = input().strip()
                    try:
                        data = json.loads(data_input) if data_input else None
                    except json.JSONDecodeError:
                        print("无效的JSON格式")
                        continue
                else:
                    data = None
                
                self.test_api_endpoint(method, endpoint, data=data, 
                                     description="自定义测试")
            else:
                print("无效选择，请重新输入")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="DMR API 快速测试工具")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="API服务器地址 (默认: http://localhost:8000)")
    parser.add_argument("--username", default="", help="用户名")
    parser.add_argument("--password", default="", help="密码")
    parser.add_argument("--interactive", "-i", action="store_true", 
                       help="交互式模式")
    
    args = parser.parse_args()
    
    tester = DMRAPITester(args.url, args.username, args.password)
    
    if args.interactive:
        tester.interactive_test()
    else:
        tester.run_full_test()


if __name__ == "__main__":
    main()
