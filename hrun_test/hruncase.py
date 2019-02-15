# coding:utf-8
from httprunner.api import HttpRunner
if __name__ == '__main__':
    runner = HttpRunner()
    #runner.run('C:\\personal_git\\httprunner_api\\hrun_test\\testsuites\\测试登录接口.yaml')
    #runner.run('C:\\personal_git\\httprunner_api\\hrun_test\\testcases\\发布宝贝\\获取客户端信息.yaml')
    runner.run('C:\\personal_git\\httprunner_api\\hrun_test\\testcases\\发布宝贝\\获取商品类型.yaml')

    #runner.run('C:\personal_git\\httprunner_api\\hrun_test\\testsuites\\发布商品.yaml')