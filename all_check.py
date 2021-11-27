# _*_ coding : UTF-8 _*_
# 开发人员 : Peter Lee
# 开发时间 : 2021/10/25 14:47
# 文件名称 : all_check.py

import os
import paramiko
import decimal
from pathlib import Path
import xlwt
import xlrd
from xlutils.copy import copy


# 使用passwd登录服务器，将巡检结果输出到特定的目录中
def login_by_passwd(server_host, server_port, username, password):
    ssh_client = paramiko.SSHClient()
    # 设置默认接收主机信任的策略，但是可能报告“不信任主机的”异常
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    with open('check.log', 'a', encoding="utf-8") as file_log:
        file_log.write('Connecting host: ' + server_host + '......' + '\n', )
    print('Connecting host: ' + server_host + '......')
    ssh_client.connect(hostname=server_host, port=server_port, username=username, password=password)
    print('Connect host: ' + server_host + ' success')
    with open('check.log', 'a', encoding="utf-8") as file_log:
        file_log.write('Connect host: ' + server_host + ' success' + '\n')
    paramiko.util.log_to_file('syslogin.log')
    server_target = []
    # 主机名
    shell_command_hostname = "hostname | awk '{print $1}'"
    # 逻辑CPU数
    shell_command_cpu_total = "cat /proc/cpuinfo| grep processor | wc -l"
    # 总内存
    shell_command_mem_total = "free -h | grep Mem| awk -F " + '" ' + '"' + " '{print $2}'"
    # 剩余内存
    shell_command_mem_free = "free -h | grep Mem | awk '{print $4}'"
    # 使用内存
    shell_command_mem_use = "free -h | grep Mem| awk -F " + '" ' + '"' + " '{print $3}'"
    # 15分钟负载
    shell_command_load_15 = "top -n 1 -b | grep average | awk -F " + "'" + ":" + "'" + " '{print $5}' | sed -e " + "'" + "s/" + "\\" + "," + "/" + "/" + 'g' + "'" + " |" + " awk -F " + '" ' + '"' + " '{print $3}'"
    # 磁盘信息
    shell_command_disk = "df -PBG | awk '{OFS=" + '","' + "}{if(+$2>10 && +$5>0 )  print $6, $2, $3, $4, $5}'"

    stdin_hostname, stdout_hostname, stderr_hostname = ssh_client.exec_command(shell_command_hostname)
    stdin_cpu_total, stdout_cpu_total, stderr_cpu_total = ssh_client.exec_command(shell_command_cpu_total)
    stdin_mem_total, stdout_mem_total, stderr_mem_total = ssh_client.exec_command(shell_command_mem_total)
    stdin_mem_free, stdout_mem_free, stderr_mem_free = ssh_client.exec_command(shell_command_mem_free)
    stdin_mem_use, stdout_mem_use, stderr_mem_use = ssh_client.exec_command(shell_command_mem_use)
    stdin_load_15, stdout_load_15, stderr_load_15 = ssh_client.exec_command(shell_command_load_15)
    stdin_disk, stdout_disk, stderr_disk = ssh_client.exec_command(shell_command_disk)

    stdout_disk_info = stdout_disk.read().decode('utf8').replace('\n', ',').split(',')
    stdout_disk_info.pop()
    stdout_disk_info_list = stdout_disk_info
    
    server_target.append(server_host)
    server_target.append(stdout_hostname.read().decode('utf8'))
    server_target.append(stdout_cpu_total.read().decode('utf8'))
    server_target.append(stdout_mem_total.read().decode('utf8'))
    server_target.append(stdout_mem_free.read().decode('utf8'))
    server_target.append(stdout_mem_use.read().decode('utf8'))
    server_target.append(stdout_load_15.read().decode('utf8'))

    # 写入xlsx
    title = ['IP', '主机名', 'CPU核数', '总内存', '剩余内存', '使用内存', '15分钟负载', '磁盘挂载目录', '磁盘容量', '磁盘使用大小',
             '磁盘可用大小', '磁盘使用率', ]
    if not os.path.exists('check.xls'):
        # 创建一个workbook 设置编码
        workbook = xlwt.Workbook(encoding='utf-8')
        # 创建一个worksheet
        worksheet = workbook.add_sheet('sheet1')
        # 设置字体格式
        title_style = xlwt.easyxf(
            'font: height 260, name DejaVu Sans Mono, colour_index black ; align: wrap on, vert centre, '
            'horiz center;')
        for i1, val in enumerate(title):
            worksheet.write(0, i1, label=val, style=title_style)
            workbook.save('check.xls')
    else:
        with open('check.log', 'a', encoding="utf-8") as file_log:
            file_log.write('文件存在' + '\n')

    # 读取Execl
    read_workbook = xlrd.open_workbook('check.xls', formatting_info=True)
    # 获取sheet名
    sheet_name = read_workbook.sheet_by_index(0)
    # 获取行
    rows = sheet_name.nrows
    # 获取列
    cols = sheet_name.ncols
    # 复制到新的工作簿
    new_workbook = copy(read_workbook)
    # 获取新表的sheet名
    new_worksheet = new_workbook.get_sheet(0)

    for num in range(len(server_target)):
        new_worksheet.write(rows, num, server_target[num])
        new_workbook.save('check.xls')


    while len(stdout_disk_info_list):
        for disk_list in range(0, 4):
            stdout_disk_info_tmp = stdout_disk_info_list[disk_list]
            stdout_disk_info_list.remove(stdout_disk_info_list[disk_list])
            # 读取Execl
            read_workbook = xlrd.open_workbook('check.xls', formatting_info=True)
            # 获取sheet名
            sheet_name = read_workbook.sheet_by_index(0)
            # 获取行
            rows = sheet_name.nrows
            # 获取列
            cols = sheet_name.ncols
            # 复制到新的工作簿
            new_workbook = copy(read_workbook)
            # 获取新表的sheet名
            new_worksheet = new_workbook.get_sheet(0)
            match_disk = ['/', '/data']
            if stdout_disk_info_list[0] in match_disk:
                for num in range(len(stdout_disk_info_tmp)):
                    new_worksheet.write(rows, num+4, stdout_disk_info_tmp[num])
                    new_workbook.save('check.xls')
            

    # 关闭文件和ssh连接
    ssh_client.close()
    with open('check.log', 'a', encoding="utf-8") as file_log:
        file_log.write('goodbye to host ' + server_host + '\n')
    print('goodbye to host ' + server_host)


if __name__ == '__main__':
    read_ip_workbook = xlrd.open_workbook('ip.xls', formatting_info=True)
    sheet_ip_name = read_ip_workbook.sheet_by_index(0)
    nRows = sheet_ip_name.nrows
    for i in range(1, nRows):
        data = str(sheet_ip_name.row_values(i))
        data_1 = (data.replace('.0', '').replace(' ', '').replace('[', '').replace(']', '').replace("'", ''))
        host, port, user, path = data_1.split(',')
        if host != "" or port != "" or user != "" or path != "":
            login_by_passwd(host, int(port), user, path)
        else:
            with open('check.log', 'a', encoding="utf-8") as file_log:
                file_log.write('ERROR ' + '\n')
            print('ERROR, 请检查Excel')
