# coding:utf-8
import os
import re
import time
import comm
from httprunner.api import HttpRunner


def is_send_email(report_file):
    """
    报告中有失败或者error的用例时，才发送邮件
    :return:none
    """
    # 通过html内容确定是否有失败的用例
    with open(os.path.join(comm.REPORT_PATH, report_file), 'r', encoding='utf8') as f:
        html_content = f.read()
    # 去除所有空格
    content = html_content.replace(' ', '')
    # 通过正则得到fail和erro的值数量
    fail_error = re.findall(r'<tdcolspan="2">\d\(\d/(\d)/(\d)/\d\)</td>', content)[0]
    fail_num = int(fail_error[0])
    error_num = int(fail_error[1])
    # 如果有失败的或者错误的，都发送邮件
    if fail_num > 0 or error_num > 0:
        comm.send_email(report)
        return
    else:
        pass


if __name__ == '__main__':
    start_time = int(time.time())
    case_path = os.path.join(comm.P_PATH, 'testsuites', '发布商品.yaml')
    runner = HttpRunner(log_level='debug', save_tests=True, report_dir=comm.REPORT_PATH, log_file=comm.LOG_FILE)
    runner.run(case_path)
    end_time = int(time.time())
    for i in range(1, 5):  # 5次判断是否生成了新报告的机会
        for root, dirs, files in os.walk(comm.REPORT_PATH):  # 目录遍历器
            report = files[-1]  # 找出最新的报告
        report_name = int(report.split('.')[0])
        if start_time <= report_name < end_time:  # 有新报告生成的时候，才判断是否有失败用例
            is_send_email(report)
        else:
            time.sleep(1)
            continue

