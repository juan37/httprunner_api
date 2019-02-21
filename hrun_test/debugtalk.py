# coding:utf-8
import configparser
import os
import pymysql
import hashlib
import requests
import json
import time
import random
from elasticsearch import Elasticsearch
from urllib.parse import unquote


def get_config(section, option=None):
    """
    读取配置文件
    :param section:
    :param option:具体的key
    :return:
    """
    # 获取当前路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 拿到配置文件
    config_file = os.path.join(current_dir, 'config', 'config.ini')
    # 实例化configParser对象
    cf = configparser.ConfigParser()
    # 读取配置文件
    cf.read(config_file, encoding='utf-8')
    # 如果提供具体key，则返回对应value
    if option:
        return cf.get(section, option)
    # 如果只提供section,则返回该section下的所有key,value,并以字典形式返回
    else:
        section_val = {}
        for option in cf.options(section):
            section_val[option] = cf.get(section, option)
        return section_val


def db_conn():
    db_info = get_config(section='db')
    try:
        conn = pymysql.Connect(host=db_info['host'], user=db_info['user'], password=db_info['password'],
                               database=db_info['database'], port=int(db_info['port']), charset=db_info['charset'])
        return conn
    except Exception as e:
        print(e)


def es_conn():
    """连接ES"""
    es_info = get_config(section='es')
    try:
        es = Elasticsearch(es_info['host'], port=es_info['port'])
        return es
    except Exception as e:
        print(e)


def get_baseurl(key):
    """
    得到接口测试域名
    :return:
    """
    return get_config('common', key)


def get_login_info(key):
    return get_config('login', key)


def es_delete(index, doc_tpye, body):
    """删除ES"""
    es = es_conn()
    # 取出查询关键词里的key和value
    # print (body)
    es.delete_by_query(index=index, doc_type=doc_tpye, body=body)


def es_search(index, doc_tpye, body):
    """搜索ES"""
    es = es_conn()
    # 取出查询关键词里的key和value
    # print (body)
    result = es.search(index=index, doc_type=doc_tpye, body=body)
    return result


def select_sql_fetchone(sql_query):
    """查询一行数据"""
    conn = db_conn()
    cur = conn.cursor()
    try:
        cur.execute(sql_query)
        result = cur.fetchone()
        # print(result[0])
        return result[0]
    except Exception as e:
        print(e)
    finally:
        cur.close()
        conn.close()


def select_sql_fetchall(sql_query):
    """查询多行行数据"""
    conn = db_conn()
    cur = conn.cursor()
    try:
        cur.execute(sql_query)
        result = cur.fetchall()
        return result
    except Exception as e:
        print(e)
    finally:
        cur.close()
        conn.close()


def delete_sql(sql_query):
    """查询多行行数据"""
    conn = db_conn()
    cur = conn.cursor()
    try:

        cur.execute(sql_query)
        conn.commit()
    except Exception as e:
        print(e)
    finally:
        cur.close()
        conn.close()


def hook_print(value):
    print("变量值是:{}".format(value))


def hook_print_response(response):
    result = response.content.decode('unicode_escape')
    print(result)


def get_response(response, expect_key=None):
    """
    从响应结果中拿到期望的key的值
    :param response: 框架自动支持的参数，可以拿到响应
    :param expect_key: 期望的key
    :return:
    """
    print(response.content)
    result = response.content.decode('unicode_escape')
    result = json.loads(result)
    return result[expect_key]


def delete_trade(response):
    """发布商品后，删除商品，清理数据,这里不仅清理了数据库，还清理了ES里的数据"""
    trade_id = get_response(response, "data")["tradeid"]
    # 删除数据库里的商品信息
    sql_query = (get_config('sql', 'delete_trade')).format(trade_id)
    # print("发布的商品ID：{}".format(trade_id))
    time.sleep(3)
    delete_sql(sql_query)
    # 删除ES里的商品信息
    es_body = get_config('es_body', 'select_trade')
    es_body = es_body.replace("$tradeid", str(trade_id))
    es_delete(index='tsy_trade', doc_tpye='trades', body=es_body)
    print("数据清理结束")


def get_goodsid(response):
    """
    得到当前游戏支持的商品类型，并分别发布每一个类型，注意APP前端手动去掉了首充号，所以代码里也需要去掉
    :param response:
    :return:
    """
    result = response.content.decode('unicode_escape')
    # 接口返回的是json格式，要转成dict
    result = json.loads(result)
    goodsids = result['data']['list']
    for goodsid in goodsids:
        if goodsid['parentid'] == "0":
            print(goodsid['id'], goodsid['name'], goodsid['sellmode'])


def generation_signature(request):
    """
    生成签名，根据前端规则编写
    :return:
    """
    # print(request)
    # print('传的所有参数:{}'.format(request['data']))
    # 后端验证签名的时候去掉了一些参数，所以这里也需要去掉
    request['data'].pop('mk')
    request['data'].pop('AppToken')
    request['data'].pop('mt')
    request['data'].pop('versionCode')
    request['data'].pop('remember')
    request['data'].pop('channel')
    # print('处理后的值:{}'.format(request['data']))
    # 按key正序排序
    key_sort_list = sorted(request['data'].keys())
    # 取出排序后对应的值
    request_new = {}
    for item in key_sort_list:
        request_new[item] = request['data'][item]
    # 对新的key-value进行url编码
    string = ''
    for key, value in request_new.items():
        if string == '':
            string = key + '=' + value
        else:
            string = string + '&' + key + '=' + value
    # 对str进行md5加密
    sign = __hash_string(string)
    return sign


def generation_verifycode(request):
    """
    APP个别接口需要校验此值,verifycode前端是根据gameId的value计算
    :return:
    """
    # print("request:{}".format(request))
    gameid = __request_params(request)['gameId']
    # print("gameid:{}".format(gameid))
    result = __hash_string(gameid)
    # print("verifycode:{}".format(result))
    return result


def __request_params(request):
    """
    get,post分别使用的params,data,json，用的是哪一个，返回哪一个
    :return:
    """
    if 'params' in request.keys():
        return request['params']
    elif 'data' in request.keys():
        return request['data']
    elif 'json' in request.keys():
        return request['json']
    else:
        pass


def __hash_string(value):
    if isinstance(value, int):
        string = str(value)
    else:
        string = value.strip()
    md5_value = hashlib.md5(string.encode(encoding='utf-8')).hexdigest()
    # 已经md5加密的数据，再用sha1加密，得到最终的signature因为开发代码这么写的，所以测试要同步
    result = hashlib.sha1(md5_value.encode(encoding='utf-8')).hexdigest()
    return result


def url_decode(request, value):
    """apptoken返回的值自动被urlencode了，导致动态添加apptoken后发送其他请求，个别请求没有走解码流程时就会出错"""
    if request['method'].lower() == 'get':
        return unquote(value, 'utf-8')
    else:
        pass


def add_signature(request):
    """
    请求要求签名参数，所以需要动态添加签名参数
    :param request:自带的request对象
    :return: none
    """
    request['data']['signature'] = generation_signature(request)
    # print("添加签名后:{}".format(request))


def add_verify_code(request):
    """
    动态添加verifycode参数
    :param request:
    :return:
    """
    # print('添加参数前:{}'.format(request))
    __request_params(request)['verifyCode'] = generation_verifycode(request)
    # print('添加参数后:{}'.format(request))


def to_int(string):
    """
    将验证点里是字符串类型的数据转为int型
    :param string:
    :return:
    """
    return int(string)


def get_game():
    """
    获取一个有客户端的且是开启状态的游戏
    :return:
    """
    sql = get_config('sql', 'get_game')
    game_id = select_sql_fetchone(sql)
    return game_id


def get_random_game_client_id(game_id):
    """
    随机返回当前游戏的一个客户端
    :param game_id: 游戏id
    :return:
    """
    query = get_config('sql', 'select_game_clients').format(game_id)
    results = select_sql_fetchall(query)
    # print(results)
    result = []
    for val in results:
        result.append(val[0])
    # print(random.choice(result))
    return random.choice(result)


def add_attrkey(request, game_id):
    """
    动态添加身份证、手机号、邮箱的属性参数
    后端是否绑定身份证的属性名规则是,gameattr_[gameid+1]，
    是否绑定手机的属性名规则是,gameattr_[gameid+2]，
    是否绑定邮箱的属性名规则是,gameattr_[gameid+3]，所以接口请求动态添加参数时也得同样规则
    :param request:
    :param game_id:
    :return:
    """
    isbindcertificate = 'gameattr_'+str(int(game_id)+1)
    isbindmobile = 'gameattr_'+str(int(game_id)+2)
    isbindemail = 'gameattr_'+str(int(game_id)+3)
    # content是json字符串，所以这里需要先解码成python对象，添加参数后，再编码成json字符串，后端才可以正常返回数据
    content = request['data']['content']
    dict_content = json.loads(content)
    dict_content[isbindcertificate] = '已绑定'
    dict_content[isbindmobile] = '已绑定'
    dict_content[isbindemail] = '已绑定'
    request['data']['content'] = json.dumps(dict_content)


def add_cp_attr(request, game_id):
    """
    动态添加成品属性参数
    :param request:
    :param game_id:
    :return:
    """
    # 获取游戏可用的成品属性
    sql_query = get_config('sql', 'select_cp_attr').format(game_id)
    attrs = select_sql_fetchall(sql_query)
    if len(attrs) > 0:  # 如果有属性值，则动态添加成品属性
        # content是json字符串，所以这里需要先解码成python对象，添加参数后，再编码成json字符串，后端才可以正常返回数据
        content = request['data']['content']
        dict_content = json.loads(content)
        # 循环判断每一个属性，根据其类型，添加值,具体字段含义见数据库
        for attr in attrs:
            attr_id = attr[0]  # 属性id
            attr_type = attr[1]  # 客户端属性类型：1输入框，2单选框，3复选框，4下拉框，5多行文本
            text_type = attr[2]  # 客户端属性值类型:0默认，1数字，2英文，3汉字
            attr_key = 'gameattr_'+str(attr_id)
            if attr_type == 1:  # 输入框
                if text_type == 0 or text_type == 3:
                    val = '输入框的客户端属性值'
                elif text_type == 1:
                    val = 666
                elif text_type == 2:
                    val = 'inputtest'
            elif attr_type == 2:  # 单选框,随机选择选项
                sql_query = get_config('sql', 'select_cp_attr_val').format(attr_id)
                result = select_sql_fetchone(sql_query).split('\r\n')
                val = random.choice(result)
            elif attr_type == 3:  # 复选框
                sql_query = get_config('sql', 'select_cp_attr_val').format(attr_id)
                result = select_sql_fetchone(sql_query).split('\r\n')
                val = random.choice(result)
            elif attr_type == 4:  # 下拉框
                sql_query = get_config('sql', 'select_cp_attr_val').format(attr_id)
                result = select_sql_fetchone(sql_query).split('\r\n')
                val = random.choice(result)
            elif attr_type == 5:  # 多行文本
                val = '多行文本的客户端属性值'
            dict_content[attr_key] = val
        request['data']['content'] = json.dumps(dict_content)
    else:
        pass


def add_client_attr(request, clientid, sellmodeid):
    """
    动态添加客户端属性参数
    :param request:
    :param clientid:客户端
    :param sellmodeid:寄售1，担保2，约定3
    :return:
    """
    if sellmodeid != 1:  # 只有寄售商品，才需要填写客户端属性即密保属性
        return 0
    else:
        # 获取客户端属性
        sql_query = get_config('sql', 'select_client_attr').format(clientid)
        attrs = select_sql_fetchall(sql_query)
        if len(attrs) > 0:  # 如果有属性值，则动态添加属性
            # content是json字符串，所以这里需要先解码成python对象，添加参数后，再编码成json字符串，后端才可以正常返回数据
            content = request['data']['content']
            dict_content = json.loads(content)
            # 循环判断每一个属性，根据其类型，添加值,具体字段含义见数据库
            for attr in attrs:
                attr_id = attr[0]  # 属性id
                attr_type = attr[1]  # 客户端属性类型：1输入框，2单选框，3复选框，4下拉框，5多行文本
                attr_key = 'clientattr_'+str(attr_id)
                if attr_type == 1:  # 输入框,后台有7日密保重复的判断，加了随机值，7日重复几率降低
                    val = 'mibao{}'.format(str(random.randint(0, 100)))
                elif attr_type == 2:  # 单选框,随机选择选项
                    sql_query = get_config('sql', 'select_client_attr_val').format(attr_id)
                    result = select_sql_fetchone(sql_query).split('\r\n')
                    val = random.choice(result)
                elif attr_type == 3:  # 复选框
                    sql_query = get_config('sql', 'select_client_attr_val').format(attr_id)
                    result = select_sql_fetchone(sql_query).split('\r\n')
                    val = random.choice(result)
                elif attr_type == 4:  # 下拉框
                    sql_query = get_config('sql', 'select_client_attr_val').format(attr_id)
                    result = select_sql_fetchone(sql_query).split('\r\n')
                    val = random.choice(result)
                elif attr_type == 5:  # 多行文本
                    val = 'mibao{}'.format(str(random.randint(0, 100)))
                dict_content[attr_key] = val
            request['data']['content'] = json.dumps(dict_content)
        else:
            pass


def __md5__():
    """
    加密，测试用
    :return:
    """
    string = 6147
    result = __hash_string(string)
    print(result)


def __request():
    """只是用来测试请求能否正常响应"""
    url = 'http://cdt0-openapi.taoshouyou.com/api/games/gamegoods'
    params = {'AppToken': 'U2FsdGVkX1%2FXApZgf3Z%2FhOTv1RqRQjuhGiL8kgWFMKQ6VFsdNu%2BvKlbeX66gWLMxm8OOvoWNOXYQCGXKQvDPkIeXrEIRsJTLy5ePZCNY09w%3D',
              'gameId': 6157, 'verifyCode': '08e86fdc94e4b8964cf2f54fe72c7055c2ac5922'}
    response = requests.get(url=url, params=params)
    print(response.text)


if __name__ == '__main__':
    add_cp_attr(6157)