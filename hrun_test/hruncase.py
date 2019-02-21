# coding:utf-8
from httprunner.api import HttpRunner
import os
if __name__ == '__main__':
    p_path = os.path.dirname(os.path.abspath(__file__))
    runner = HttpRunner()
    #runner.run(os.path.join(p_path, 'testsuites\\测试登录接口.yaml'))
    #runner.run(os.path.join(p_path, 'testcases\\发布宝贝\\获取客户端信息.yaml'))

    runner.run(os.path.join(p_path, 'testcases\\业务接口\\发布账号.yaml'))

    #runner.run(os.path.join(p_path, 'hrun_test\\testsuites\\发布商品.yaml'))