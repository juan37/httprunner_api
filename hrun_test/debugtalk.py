# coding:utf-8
import configparser
import os
import pymysql
import hashlib


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


def get_baseurl(key):
    """
    得到接口测试域名
    :return:
    """
    return get_config('common', key)


def get_login_info(key):
    return get_config('login', key)


def exe_sql(query, operate='get'):
    """
    操作数据库
    :param query:sql
    :param operate:get表示查询语句，非get表示操作语句，包括update,insert,delete
    :return:
    """
    # 获取数据库信息
    # query = get_config('sql',query)
    db_info = get_config(section='db')
    conn = pymysql.Connect(host=db_info['host'], user=db_info['user'], password=db_info['password'],
                           database=db_info['database'], port=int(db_info['port']), charset=db_info['charset'])
    # 获取游标
    try:
        cur = conn.cursor()
        cur.execute(query)
        if operate.strip().lower() == 'get':
            result = cur.fetchall()
            print(result)
            # 没有考虑多行数据的问题，因为在校验数据时，1.可能验证某一数据具体值 2.数据长度 ，所以用不到多行数据本身的验证
            if len(result[0]) > 1:
                return result[0]
            else:
                return result[0][0]
        else:
            conn.commit()
    except Exception as e:
        conn.rollback()  # commit出错时回滚
        print(e)
    finally:
        cur.close()
        conn.close()


def hook_print(value):
    print("变量值是:{}".format(value))


def hook_print_response(response):
    print(response.text)


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
    #print('添加参数前:{}'.format(request))
    __request_params(request)['verifyCode'] = generation_verifycode(request)
    print('添加参数后:{}'.format(request))


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
    game_id = exe_sql(sql)
    return game_id


def __md5__():
    """
    加密，测试用
    :return:
    """
    string = 6147
    result = __hash_string(string)
    print(result)


if __name__ == '__main__':
    # print (exe_sql(getConfig('sql', 'select_user_id').format(username='tgbuyer')))
    #get_game()
    __md5__()