# coding:utf-8
import configparser
import os
import time
import pymysql
from elasticsearch import Elasticsearch
# from DBUntils.

P_PATH = os.path.dirname(os.path.abspath(__file__))

name = time.strftime('%Y_%m_%d_%H%M%S', time.localtime())
LOG_FILE = os.path.join(P_PATH, 'log', '{}log'.format(name))

CONF_FILE = os.path.join(P_PATH, 'config', 'config.ini')

REPORT_PATH = os.path.join(P_PATH, 'reports')


def logger(log_level, content):
    from httprunner import logger
    logger.setup_logger(log_level=log_level, log_file=LOG_FILE)
    if log_level.lower() == 'info':
        logger.log_info(content)
    elif log_level.lower() == 'debug':
        logger.log_debug(content)
    elif log_level.lower() == 'warning':
        logger.log_warning(content)
    elif log_level.lower() == 'error':
        logger.log_error(content)
    elif log_level.lower() == 'critical':
        logger.log_critical(content)


def get_config(section, option=None):
    cf = configparser.ConfigParser()
    cf.read(CONF_FILE, encoding='utf-8')
    if option:
        return cf.get(section, option)
    # 如果只提供section,则返回该section下的所有key,value,并以字典形式返回
    else:
        section_val = {}
        for option in cf.options(section):
            section_val[option] = cf.get(section, option)
        return section_val


def __db_conn():
    db_info = get_config(section='db')
    try:
        conn = pymysql.Connect(host=db_info['host'], user=db_info['user'], password=db_info['password'],
                               database=db_info['database'], port=int(db_info['port']), charset=db_info['charset'])
        return conn
    except Exception as e:
        logger('error', e.__str__())  # logger只支持写入str


def select_sql_fetchone(sql_query):
    """查询一行数据"""
    conn = __db_conn()
    cur = conn.cursor()
    try:
        cur.execute(sql_query)
        result = cur.fetchone()
        return result[0]
    except Exception as e:
        logger('error', e.__str__())
    finally:
        cur.close()
        conn.close()


def select_sql_fetchall(sql_query):
    """查询多行行数据"""
    conn = __db_conn()
    cur = conn.cursor()
    try:
        cur.execute(sql_query)
        result = cur.fetchall()
        return result
    except Exception as e:
        logger('error', e.__str__())
    finally:
        cur.close()
        conn.close()


def exe_sql(sql_query):
    """查询多行行数据"""
    conn = __db_conn()
    cur = conn.cursor()
    try:

        cur.execute(sql_query)
        conn.commit()
    except Exception as e:
        logger('error', e.__str__())
    finally:
        cur.close()
        conn.close()


def __es_conn():
    """连接ES"""
    es_info = get_config(section='es')
    try:
        es = Elasticsearch(es_info['host'], port=es_info['port'])
        return es
    except Exception as e:
        logger('error', e.__str__())


def es_delete(index, doc_tpye, body):
    """删除ES"""
    es = __es_conn()
    # 取出查询关键词里的key和value
    # print (body)
    es.delete_by_query(index=index, doc_type=doc_tpye, body=body)


def es_search(index, doc_tpye, body):
    """搜索ES"""
    es = __es_conn()
    # 取出查询关键词里的key和value
    # print (body)
    result = es.search(index=index, doc_type=doc_tpye, body=body)
    return result


def send_email(report_name):
    """
    如果打开了发送邮件开关，才发送邮件
    :param report_name: 报告名称
    :return: none
    """
    import smtplib
    import os
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.header import Header
    # 读取邮件配置
    switch = get_config('email', 'switch')
    host = get_config('email', 'host')
    port = get_config('email', 'port')
    sender = get_config('email', 'sender')
    pw = get_config('email', 'pw')
    receive = get_config('email', 'receive_list')
    if switch.lower() == 'off' or switch.lower() != 'on':  # 打开开关才向下走
        return
    if str(receive).find(','):
        receive_list = receive.split(',')  # 如果是多个接收人，从config读出来的数据是str，需要转成list才可以发送给每个接收人
    else:
        receive_list = receive
    messeage = MIMEMultipart()
    messeage['From'] = Header(s="jenkins", charset='utf-8')  # 必须加上这个，不然发件人会是空
    messeage['To'] = Header(s=str(receive_list), charset='utf-8')  # 必须加上这个，不然收件人会是空
    messeage['Subject'] = Header(s=u'接口测试有失败用例', charset='utf-8')
    messeage.attach(MIMEText('接口测试有失败的用例，详情见附件报告', 'plain', 'utf-8'))
    # 构造附件
    att = MIMEText(open(os.path.join(REPORT_PATH, report_name), 'rb').read(), 'base64', 'utf-8')
    att['Content-Type'] = 'application/octet-stream'
    att['Content-Disposition'] = 'attachment;filename="{}"'.format(report_name)
    messeage.attach(att)
    try:
        smtp_obj = smtplib.SMTP()
        smtp_obj.connect(host=host, port=port)
        smtp_obj.login(sender, pw)
        smtp_obj.sendmail(from_addr=sender, to_addrs=receive_list, msg=messeage.as_string())
        logger("info", 'send email sucess')
    except smtplib.SMTPException as e:
        logger('error', e.__str__())
    finally:
        smtp_obj.close()


if __name__=='__main__':
    obj = __db_conn()
    obj.close()