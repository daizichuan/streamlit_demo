# -*- coding: utf-8 -*-
import configparser
import os
import re
import subprocess

import streamlit as st

'''
原理是：多个模块/系统的测试项目放在一个工程目录下。配置放在ip文件里统一管理。通过选择不同测试项目，找到testCase或test_case目录，然后查找/筛选所有
以test_开头的文件，找的文件就是测试用例。然后从allure装饰器@allure.feature中找到用例解释或用例中文名，组成一个字典。找到就用装饰器里的字符串名称
找不到就用用例文件名。最后通过pytest和allure命令执行测试和生成测试报告。
'''
# #左边侧边栏
# 工程目录
project_dir = os.path.abspath(os.path.dirname(__file__))
st.sidebar.text(f"工程目录:{project_dir}")


# 环境配置
class IniUtils:
    target_configfile = "ip"
    conf = configparser.ConfigParser()
    conf.read(target_configfile, encoding="utf-8")

    @classmethod
    def get_sections(cls):
        return cls.conf.sections()

    @classmethod
    def get_data(cls, section):
        return cls.conf.items(section)

    @classmethod
    def set_data(cls, s_k_v):
        for s_k, v in s_k_v.items():
            res = re.search(r"\[(.*?)\]\s(.*)", s_k)
            cls.conf.set(res[1], res[2], v)
        with open(cls.target_configfile, 'w') as f:
            cls.conf.write(f)


with st.sidebar.expander("环境配置"):
    section = st.selectbox(
        "选择分类",
        IniUtils.get_sections()
    )
    for k, v in IniUtils.get_data(section):
        st.text_input(k, v, key=f'[{section}] {k}')

    dict_tmp = {}
    for _ in st.session_state:
        if f'[{section}]' in _:
            dict_tmp.update({_: st.session_state[_]})

    IniUtils.set_data(dict_tmp)


# 系统目录
def get_system_dir(f_dir):
    lst = []
    dirs = os.listdir(f_dir)
    for _ in dirs:
        if os.path.isdir(_) and all(
                x != _ for x in
                ['.git', '.idea', '.pytest_cache', 'allure_report', 'allure_result', 'job', '__pycache__']):
            lst.append(_)
    return lst


system_dir = st.sidebar.selectbox(
    "系统目录",
    get_system_dir(project_dir)
)


# 测试套件目录
def get_case_dir(f_dir):
    dirs = os.listdir(os.path.join(project_dir, f_dir))
    lst = []
    for _ in dirs:
        if os.path.isdir(os.path.join(project_dir, f_dir, _)) and any(
                x == _.lower() for x in ['testcase', 'test_case']):
            case_dir = os.path.join(project_dir, f_dir, _)
            for root, dirs, files in os.walk(case_dir, topdown=False):
                if all(x not in root for x in ['.pytest_cache', '__pycache__']):
                    lst.append(root.split(project_dir)[1][1:])
    return lst


case_dirs = get_case_dir(system_dir)
case_dirs.sort()
chosen_case_dirs = st.sidebar.multiselect(
    "测试套件目录",
    case_dirs,
    default=case_dirs[0]
)


# 用例选择
def get_test_case_names(f_dir):
    dict_tmp = {}
    for root, dirs, files in os.walk(f_dir, topdown=False):
        for name in files:
            file_name = os.path.join(root, name)
            if '.pytest_cache' not in root and '__pycache__' not in root and 'test_' in name:
                # 打开文件
                with open(file_name, 'r', encoding='utf-8') as file:
                    # 读取文件内容
                    text = file.read()
                    # 使用正则表达式获取匹配到的文本内容
                    res = re.search(r"@allure.feature\('(.*?)'\)", text)
                    file_name_2 = file_name.split(root)[1][1:]
                    if res:
                        dict_tmp.update({res[1]: file_name})
                    else:
                        dict_tmp.update({file_name_2: file_name})
    return dict_tmp


case_names_dict = {}
chosen_case_values = []
for chosen_case_dir in chosen_case_dirs:
    case_names_dict.update(get_test_case_names(os.path.join(project_dir, chosen_case_dir)))
all_case_num = len(case_names_dict)
with st.sidebar.expander("选择测试用例", expanded=True):
    chosen_case_keys = st.multiselect('默认全选', case_names_dict, default=case_names_dict)
for key in chosen_case_keys:
    chosen_case_values.append(case_names_dict[key])

# #右边显示区域
st.subheader('执行脚本')
# 显示运行环境ip
st.text(f'脚本执行环境：{IniUtils.get_data("IP")[0][1]}')
# 打印选中的测试套件名称
for chosen_case_dir in chosen_case_dirs:
    st.text(f"选中测试套件：{chosen_case_dir}")
# 显示用例选择情况
st.text(f"共：{all_case_num}条用例，执行：{len(chosen_case_keys)}条")
# 选择执行方式
genre = st.radio(
    "选择测试执行方式",
    ('测试用例套件', '测试用例名称'))


# 执行脚本
def run_command(command):
    with st.expander("执行情况", expanded=True):
        # 使用subprocess模块执行命令并获取输出
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        while True:
            line = process.stdout.readline()
            if line:
                st.write(line.decode("gbk"))
            else:
                break


if st.button('执行脚本'):
    st.write("执行用例：")
    if genre == '测试用例套件':
        command = f'pytest {" ".join(chosen_case_dirs)} --clean-alluredir --alluredir=allure_result'
        st.write(command)
        run_command(command)
    elif genre == '测试用例名称':
        command = f'pytest {" ".join(chosen_case_values)} --clean-alluredir --alluredir=allure_result'
        st.write(command)
        run_command(command)
    st.write("生成测试报告：")
    run_command('allure generate allure_result -o allure_report --clean')
    st.write("查看测试报告：")
    run_command('allure serve allure_result')
