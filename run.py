#!/usr/bin/env python
import os
import json
import re
import sys

import lpunpack
import mkdtboimg
import utils
from api import cls, dir_has, cat, dirsize
import time
import platform as plat
import shutil
from utils import gettype, simg2img
import requests
import ofp_qc_decrypt
import ofp_mtk_decrypt
import ozipdecrypt
import zipfile
import imgextractor
import contextpatch
import fspatch
import extract_dtb
from argparse import Namespace

LOCALDIR = os.getcwd()
binner = LOCALDIR + os.sep + "bin"
setfile = LOCALDIR + os.sep + "bin" + os.sep + "settings.json"
tempdir = LOCALDIR + os.sep + 'TEMP'
tiklog = LOCALDIR + os.sep + f'TIK4_{time.strftime("%Y%m%d")}.log'
AIK = binner + os.sep + 'AIK'
MBK = binner + os.sep + 'AIK'
platform = plat.machine()
ostype = plat.system()
PIP_MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple/"
ebinner = binner + os.sep + ostype + os.sep + platform + os.sep
dtc = ebinner + os.sep + "dtc"
mkdtimg_tool = binner + os.sep + "mkdtboimg.py"


def yecho(info): print(f"\033[36m[{time.strftime('%H:%M:%S')}]{info}\033[0m")


def ywarn(info): print(f"\033[31m{info}\033[0m")


def ysuc(info): print(f"\033[32m[{time.strftime('%H:%M:%S')}]{info}\033[0m")


def rmdire(path):
    if os.path.exists(path):
        shutil.rmtree(path)


def call(command):
    return os.system(ebinner + command)


def getsize(file):
    return os.path.getsize(file)


def cleantemp():
    rmdire(tempdir)
    os.mkdir(tempdir)


if os.name == 'posix':
    os.system(f'chmod -R 777 {binner}')


def getprop(name, path):
    with open(path, 'r') as prop:
        for s in prop.readlines():
            if s[:1] == '#':
                continue
            if name in s:
                return s.strip().split('=')[1]


class set_utils:
    def __init__(self, path):
        self.path = path

    def load_set(self):
        with open(self.path, 'r') as ss:
            data = json.load(ss)
            for v in data:
                setattr(self, v, data[v])

    def change(self, name, value):
        with open(self.path, 'r') as ss:
            data = json.load(ss)
        with open(self.path, 'w', encoding='utf-8') as ss:
            data[name] = value
            json.dump(data, ss, ensure_ascii=False, indent=4)
        self.load_set()


settings = set_utils(setfile)
settings.load_set()


class setting:
    def settings4(self):
        cls()
        print('''
		\033[33m  > 打包设置 \033[0m
		   1>Brotli 压缩等级\n
		   2>[EXT4] Size处理\n
		   3>[EXT4] 打包工具\n
		   4>[EXT4]打包RO/RW\n
		   5>[Erofs]压缩方式\n
		   6>[EXT4]UTC时间戳\n
		   7>[EXT4]InodeSize\n
		   8>[Img]创建sparse\n
		   9>[~4]Img文件系统\n
		   12>返回上一级菜单
		   --------------------------
		''')
        op_pro = input("   请输入编号: ")
        if op_pro == "12":
            return 1
        try:
            getattr(self, 'packset%s' % op_pro)()
            self.settings5()
        except AttributeError:
            print("Input error!")
            self.settings4()

    def settings5(self):
        cls()
        print('''
		\033[33m  > 动态分区设置 \033[0m
		   1> dynamic_partitions簇名\n
		   2> [Metadata]元数据插槽数\n
		   3> [Metadata]最大保留Size\n
		   4> [分区] 默认扇区/块大小\n
		   5> [Super] 指定/block大小\n
		   6> [Super] 更改物理分区名\n
		   7> [Super] 更改逻辑分区表\n
		   8> [Super]强制烧写完整Img\n
		   9> [Super] 标记分区槽后缀\n
		   10>[Payload]靶定HeaderVer\n
		   11>返回上一级菜单
		   --------------------------
		''')
        op_pro = input("   请输入编号: ")
        if op_pro == "11":
            return 1
        elif op_pro == '10':
            input('维护中。。。')
        try:
            getattr(self, 'dyset%s' % op_pro)()
            self.settings5()
        except AttributeError:
            print("Input error!")
            self.settings5()

    def settings2(self):
        print(f"修改安卓端在内置存储识别ROM的路径。当前为/sdcard/{settings.mydir}")
        mydir = input('   请输入文件夹名称(英文):')
        if mydir:
            settings.change('mydir', mydir)

    def settings3(self):
        if os.name == "posix":
            for age in ['python3', 'simg2img', 'img2simg', 'cpio', 'sed', 'libnss3-tools', 'python3-pip', 'brotli',
                        'curl', 'bc', 'cpio', 'default-jre', 'android-sdk-libsparse-utils', 'openjdk-11-jre', 'aria2',
                        'p7zip-full']:
                print(f"\033[31m  修复安装{age}\033[0m")
                os.system(f"apt-get install {age} -y")
                print(f"\033[36m  {age}已安装\033[0m")
        else:
            print("非LINUX，无法修复")

    def settings6(self):
        print(f"  打包时ROM作者为：{settings.Romer}")
        Romer = input("  请输入（无特殊字符）: ")
        if Romer:
            settings.change('Romer', Romer)

    def settings7(self):
        print("  首页banner: [1]TIK3 [2]爷 [3]电摇嘲讽 [4]镰刀斧头 [5]镰刀斧头(大) [6]TIK2旧 ")
        banner = input("  请输入序号: ")
        if banner.isdigit():
            if 0 < int(banner) < 7:
                settings.change('banner', banner)

    def settings8(self):
        plugromlit = input("  设置区分ROM/Plug的Size界限[1]125829120 [2]自定义: ")
        if plugromlit == '2':
            plugromlit = input("  请输入：")
            if plugromlit.isdigit():
                settings.change('plugromlit', plugromlit)
        else:
            settings.change('plugromlit', '125829120')

    def packset1(self):
        print(f"  调整brotli压缩等级（整数1-9，级别越高，压缩率越大，耗时越长），当前为：{settings.brcom}级")
        brcom = input("  请输入（1-9）: ")
        if brcom.isdigit():
            if 0 < int(brcom) < 10:
                settings.change('brcom', brcom)

    def packset2(self):
        sizediy = input("  打包Ext镜像大小[1]动态最小 [2]手动改: ")
        if sizediy == '2':
            settings.change('diysize', '1')
        else:
            settings.change('diysize', '')

    def packset3(self):
        print("  ext4打包方案: [1]make_ext4fs [2]mke2fs+e2fsdroid ")
        pack_op = input("  请输入序号: ")
        if pack_op == '1':
            settings.change('pack_e2', '0')
        else:
            settings.change('pack_e2', '1')

    def packset4(self):
        extrw = input("  打包EXT是否可读[1]RW [2]RO: ")
        if extrw == '2':
            settings.change('ext4rw', '')
        else:
            settings.change('ext4rw', '-s')

    def packset5(self):
        erofslim = input("  选择erofs压缩方式[1]是 [2]否: ")
        if erofslim == '1':
            erofslim = input("  选择erofs压缩方式：lz4/lz4hc和压缩等级[1-9](数字越大耗时更长体积更小) 例如 lz4hc,8: ")
            if erofslim:
                settings.change("erofslim", erofslim)
        else:
            settings.change("erofslim", '')

    def packset6(self):
        utcstamp = input("  设置打包UTC时间戳[1]live [2]自定义: ")
        if utcstamp == "2":
            utcstamp = input("  请输入: ")
            if utcstamp.isdigit():
                settings.change('utcstamp', utcstamp)
        else:
            settings.change('utcstamp', '')

    def packset8(self):
        print("  Img是否打包为sparse(压缩体积)[1/0]")
        ifpsparse = input("  请输入序号: ")
        if ifpsparse == '1':
            settings.change('pack_sparse', '1')
        elif ifpsparse == '0':
            settings.change('pack_sparse', '0')

    def packset7(self):
        inodesize = input("  设置EXT分区inode-size: ")
        if inodesize:
            settings.change('inodesize', inodesize)

    def packset9(self):
        typediy = input("  打包镜像格式[1]同解包格式 [2]可选择: ")
        if typediy == '2':
            settings.change('diyimgtype', '1')
        else:
            settings.change('diyimgtype', '')

    def dyset1(self):
        super_group = input(f"  当前动态分区簇名/GROUPNAME：{settings.super_group}\n  请输入（无特殊字符）: ")
        if super_group:
            settings.change('super_group', super_group)

    def dyset2(self):
        slotnumber = input("  强制Metadata插槽数：[2] [3]: ")
        if slotnumber == '3':
            settings.change('slotnumber', '3')
        else:
            settings.change('slotnumber', '2')

    def dyset3(self):
        metadatasize = input("  设置metadata最大保留size(默认为65536，至少512) ")
        if metadatasize:
            settings.change('metadatasize', metadatasize)

    def dyset4(self):
        BLOCKSIZE = input(f"  分区打包扇区/块大小：{settings.BLOCKSIZE}\n  请输入: ")
        if BLOCKSIZE:
            settings.change('BLOCKSIZE', BLOCKSIZE)

    def dyset5(self):
        SBLOCKSIZE = input(f"  分区打包扇区/块大小：{settings.SBLOCKSIZE}\n  请输入: ")
        if SBLOCKSIZE:
            settings.change('SBLOCKSIZE', SBLOCKSIZE)

    def dyset6(self):
        supername = input(f'  当前动态分区物理分区名(默认super)：{settings.supername}\n  请输入（无特殊字符）: ')
        if supername:
            settings.change('supername', supername)

    def dyset7(self):
        superpart_list = input(f'  当前动态分区内逻辑分区表：{settings.superpart_list}\n  请输入（无特殊字符）: ')
        if superpart_list:
            settings.change('superpart_list', superpart_list)

    def dyset8(self):
        iffullsuper = input("  是否创建强制刷入的Full镜像？[1/0]")
        if not iffullsuper == '1':
            settings.change('fullsuper', '')
        else:
            settings.change('fullsuper', '-F')

    def dyset9(self):
        autoslotsuffix = input("  是否标记需要Slot后缀的分区？[1/0]")
        if not autoslotsuffix == '1':
            settings.change('autoslotsuffixing', '')
        else:
            settings.change('autoslotsuffixing', '-x')

    def __init__(self):
        cls()
        print('''
	\033[33m  > 设置 \033[0m
	   1> 待定
	   2>[Droid]存储ROM目录
	   3>[修复]工具部分依赖
	   4>[打包]相关细则设置
	   5>[动态分区]相关设置
	   6>自定义 ROM作者信息
	   7>自定义 首页Banner
	   8>修改Plug/ROM限Size
	   9>返回主页
	   --------------------------
	''')
        op_pro = input("   请输入编号: ")
        if op_pro == "9":
            return
        try:
            getattr(self, 'settings%s' % op_pro)()
            self.__init__()
        except AttributeError as e:
            print(f"Input error!{e}")
            self.__init__()


def promenu():
    gs = 1
    projects = {}
    cls()
    try:
        content = json.loads(requests.get('https://v1.jinrishici.com/all.json').content.decode())
        shiju = content['content']
        fr = content['origin']
        another = content['author']
    except:
        gs = 0
    with open(binner + os.sep + 'banners' + os.sep + settings.banner, 'r') as banner:
        print(f'\033[31m {banner.read()} \033[0m')
    print("\033[92;44m Beta Edition \033[0m")
    if gs == 1:
        print(f"\033[36m “{shiju}”")
        print(f"\033[36m---{another}《{fr}》\033[0m\n")
    print(" >\033[33m 项目列表 \033[0m\n")
    print("\033[31m   [00]  删除项目\033[0m\n")
    print("   [0]  新建项目\n")
    pro = 0
    del_ = 0
    if os.listdir(LOCALDIR + os.sep):
        for pros in os.listdir(LOCALDIR + os.sep):
            if pros.startswith('TI_') and os.path.isdir(LOCALDIR + os.sep + pros):
                pro += 1
                print(f"   [{pro}]  {pros}\n")
                projects['%s' % pro] = pros
    print("  --------------------------------------")
    print("\033[33m  [55] 解压  [66] 退出  [77] 设置  [88] TIK实验室\033[0m")
    print("")
    print(" \n")
    op_pro = input("  请输入序号：")
    if op_pro == '55':
        unpackrom()
    elif op_pro == '88':
        print('\n"维护中..."\n')
    elif op_pro == '00':
        op_pro = input("  请输入你要删除的项目序号：")
        if op_pro in projects.keys():
            delr = input(f"  确认删除{projects[op_pro]}？[1/0]")
            if delr == '1':
                rmdire(LOCALDIR + os.sep + projects[op_pro])
                ysuc("  删除成功！")
            else:
                print(" 取消删除")
        time.sleep(2)
    elif op_pro == '0':
        projec = input("请输入项目名称(非中文)：TI_")
        if not projec:
            ywarn("Input Error!")
            time.sleep(2)
        else:
            project = 'TI_%s' % projec
            if os.path.exists(LOCALDIR + os.sep + project):
                project = f'{project}_{time.strftime("%m%d%H%M%S")}'
                ywarn(f"项目已存在！自动命名为：{project}")
                time.sleep(2)
            os.makedirs(LOCALDIR + os.sep + project + os.sep + "config")
            menu(project)
    elif op_pro == '66':
        cls()
        sys.exit(0)
    elif op_pro == '77':
        setting()
    elif op_pro.isdigit():
        if op_pro in projects.keys():
            menu(projects[op_pro])
        else:
            ywarn("  Input error!")
    else:
        ywarn("  Input error!")
        time.sleep(2)
    promenu()


def menu(project):
    PROJECT_DIR0 = LOCALDIR + os.sep + project
    PROJECT_DIR = PROJECT_DIR0
    cls()
    os.chdir(PROJECT_DIR)
    if not os.path.exists(os.path.abspath('config')):
        ywarn("项目已损坏！")
    if not os.path.exists(PROJECT_DIR + os.sep + 'TI_out'):
        os.makedirs(PROJECT_DIR + os.sep + 'TI_out')
    print('\n')
    print(" \033[31m>ROM菜单 \033[0m\n")
    print(f"  项目：{project}")
    print('')
    print('\033[33m    1> 项目主页     2> 解包菜单\033[0m\n')
    print('\033[36m    3> 打包菜单     4> 插件菜单\033[0m\n')
    print('\033[32m    5> 一键封装\033[0m\n')
    print()
    op_menu = input("    请输入编号: ")
    if op_menu == '1':
        os.chdir(LOCALDIR)
        return
    elif op_menu == '2':
        unpackChoo(PROJECT_DIR)
    elif op_menu == '3':
        packChoo(PROJECT_DIR)
    elif op_menu == '4':
        pass
    # subbed
    elif op_menu == '5':
        ywarn("维护中...")
        time.sleep(2)
    else:
        ywarn('   Input error!"')
        time.sleep(2)
    menu(project)


def unpackChoo(project):
    cls()
    os.chdir(project)
    print(" \033[31m >分解 \033[0m\n")
    filen = 0
    files = {}
    infos = {}
    ywarn(f"  请将文件放于{project}根目录下！")
    print()
    print(" [0]- 分解所有文件\n")
    if dir_has(project, '.br'):
        print("\033[33m [Br]文件\033[0m\n")
        for br0 in os.listdir(project):
            if br0.endswith('.br'):
                if os.path.isfile(os.path.abspath(br0)):
                    filen += 1
                    print(f"   [{filen}]- {br0}\n")
                    files[filen] = br0
                    infos[filen] = 'br'
    if dir_has(project, '.new.dat'):
        print("\033[33m [Dat]文件\033[0m\n")
        for dat0 in os.listdir(project):
            if dat0.endswith('.new.dat'):
                if os.path.isfile(os.path.abspath(dat0)):
                    filen += 1
                    print(f"   [{filen}]- {dat0}\n")
                    files[filen] = dat0
                    infos[filen] = 'dat'
    if dir_has(project, '.new.dat.1'):
        for dat10 in os.listdir(project):
            if dat10.endswith('.dat.1'):
                if os.path.isfile(os.path.abspath(dat10)):
                    filen += 1
                    print(f"   [{filen}]- {dat10} <分段DAT>\n")
                    files[filen] = dat10
                    infos[filen] = 'dat.1'
    if dir_has(project, '.img'):
        print("\033[33m [Img]文件\033[0m\n")
        for img0 in os.listdir(project):
            if img0.endswith('.img'):
                if os.path.isfile(os.path.abspath(img0)):
                    filen += 1
                    info = gettype(os.path.abspath(img0))
                    if info == "unknow":
                        ywarn(f"   [{filen}]- {img0} <UNKNOWN>\n")
                    else:
                        print(f'   [{filen}]- {img0} <{info.upper()}>\n')
                    files[filen] = img0
                    if info != 'sparse':
                        infos[filen] = 'img'
                    else:
                        infos[filen] = 'sparse'
    if dir_has(project, '.bin'):
        for bin0 in os.listdir(project):
            if bin0.endswith('.bin'):
                if os.path.isfile(os.path.abspath(bin0)) and gettype(os.path.abspath(bin0)) == 'payload':
                    filen += 1
                    print(f"   [{filen}]- {bin0} <BIN>\n")
                    files[filen] = bin0
                    infos[filen] = 'payload'
    if dir_has(project, '.ozip'):
        print("\033[33m [Ozip]文件\033[0m\n")
        for ozip0 in os.listdir(project):
            if ozip0.endswith('.ozip'):
                if os.path.isfile(os.path.abspath(ozip0)) and gettype(os.path.abspath(ozip0)) == 'ozip':
                    filen += 1
                    print(f"   [{filen}]- {ozip0}\n")
                    files[filen] = ozip0
                    infos[filen] = 'ozip'
    if dir_has(project, '.ofp'):
        print("\033[33m [Ofp]文件\033[0m\n")
        for ofp0 in os.listdir(project):
            if ofp0.endswith('.ofp'):
                if os.path.isfile(os.path.abspath(ofp0)):
                    filen += 1
                    print(f"   [{filen}]- {ofp0}\n")
                    files[filen] = ofp0
                    infos[filen] = 'ofp'
    if dir_has(project, '.ops'):
        print("\033[33m [Ops]文件\033[0m\n")
        for ops0 in os.listdir(project):
            if ops0.endswith('.ops'):
                if os.path.isfile(os.path.abspath(ops0)):
                    filen += 1
                    print(f'   [{filen}]- {ops0}\n')
                    files[filen] = ops0
                    infos[filen] = 'ops'
    if dir_has(project, '.win'):
        print("\033[33m [Win]文件\033[0m\n")
        for win0 in os.listdir(project):
            if win0.endswith('.win'):
                if os.path.isfile(os.path.abspath(win0)):
                    filen += 1
                    print(f"   [{filen}]- {win0} <WIN> \n")
                    files[filen] = win0
                    infos[filen] = 'win'
    if dir_has(project, '.win000'):
        for win0000 in os.listdir(project):
            if win0000.endswith('.win000'):
                if os.path.isfile(os.path.abspath(win0000)):
                    filen += 1
                    print(f"   [{filen}]- {win0000} <分段WIN> \n")
                    files[filen] = win0000
                    infos[filen] = 'win000'
    if dir_has(project, '.dtb'):
        print("\033[33m [Dtb]文件\033[0m\n")
        for dtb0 in os.listdir(project):
            if dtb0.endswith('.dtb'):
                if os.path.isfile(os.path.abspath(dtb0)) and gettype(os.path.abspath(dtb0)) == 'dtb':
                    filen += 1
                    print(f'   [{filen}]- {dtb0}\n')
                    files[filen] = dtb0
                    infos[filen] = 'dtb'
    print()
    print("\033[33m  [77] 菜单  [88] 循环解包  \033[0m")
    print("  --------------------------------------")
    filed = input("  请输入对应序号：")
    if filed == '0':
        print()
        for v in files.keys():
            unpack(files[v], infos[v], project)
    elif filed == '88':
        print()
        imgcheck = 0
        upacall = input("  是否解包所有文件？ [1/0]	")
        for v in files.keys():
            if upacall != '1':
                imgcheck = input(f"  是否解包{files[v]}?[1/0]	")
            if upacall == "1" or imgcheck != "0":
                unpack(files[v], infos[v], project)
    elif filed == '77':
        return
    elif filed.isdigit():
        if int(filed) in files.keys():
            unpack(files[int(filed)], infos[int(filed)], project)
        else:
            ywarn("Input error!")
            time.sleep(2)
    else:
        ywarn("Input error!")
        time.sleep(2)
    unpackChoo(project)


def packChoo(project):
    cls()
    print(" \033[31m >打包 \033[0m\n")
    partn = 0
    parts = {}
    types = {}
    if not os.path.exists(project + os.sep + "config"):
        os.makedirs(project + os.sep + "config")
    if project:
        print("   [0]- 打包所有镜像\n")
        for packs in os.listdir(project):
            if os.path.isdir(project + os.sep + packs):
                if os.path.exists(project + os.sep + "config" + os.sep + packs + "_fs_config"):
                    partn += 1
                    parts[partn] = packs
                    if os.path.exists(project + os.sep + "config" + os.sep + packs + "_erofs"):
                        typeo = 'erofs'
                    else:
                        typeo = 'ext'
                    types[partn] = typeo
                    print(f"   [{partn}]- {packs} <{typeo}>\n")
                elif os.path.exists(project + os.sep + packs + os.sep + "comp"):
                    partn += 1
                    parts[partn] = packs
                    types[partn] = 'bootimg'
                    print(f"   [{partn}]- {packs} <bootimg>\n")
                elif os.path.exists(project + os.sep + "config" + os.sep + "dtbinfo_" + packs):
                    partn += 1
                    parts[partn] = packs
                    types[partn] = 'dtb'
                    print(f"   [{partn}]- {packs} <dtb>\n")
                elif os.path.exists(project + os.sep + "config" + os.sep + "dtboinfo_" + packs):
                    partn += 1
                    parts[partn] = packs
                    types[partn] = 'dtbo'
                    print(f"   [{partn}]- {packs} <dtbo>\n")
        print()
        print("\033[33m [55] 循环打包 [66] 打包Super [77] 打包Payload [88]菜单\033[0m")
        print("  --------------------------------------")
        filed = input("  请输入对应序号：")
        if filed == '0':
            op_menu = input("  输出文件格式[1]br [2]dat [3]img:")
            if op_menu == '1':
                form = 'br'
            elif op_menu == '2':
                form = 'dat'
            else:
                form = 'img'
            if settings.diyimgtype == '1':
                syscheck = input("手动打包所有分区格式为：[1]ext4 [2]erofs")
                if syscheck == '2':
                    imgtype = "erofs"
                else:
                    imgtype = "ext"
            else:
                imgtype = 'ext'
            for f in parts.keys():
                yecho(f"打包{parts[f]}...")
                if types[f] == 'bootimg':
                    dboot(project + os.sep + parts[f], project + os.sep + parts[f] + ".img")
                elif types[f] == 'dtb':
                    makedtb(project + os.sep + parts[f], project)
                elif types[f] == 'dtbo':
                    # makedtbo $partname
                    pass
                else:
                    inpacker(parts[f], project, form, imgtype)
        elif filed == '55':
            print()
            pacall = input("  是否打包所有镜像？ [1/0]	")
            op_menu = input("  输出所有文件格式[1]br [2]dat [3]img:")
            if op_menu == '1':
                form = 'br'
            elif op_menu == '2':
                form = 'dat'
            else:
                form = 'img'
            if settings.diyimgtype == '1':
                syscheck = input("手动打包所有分区格式为：[1]ext4 [2]erofs")
                if syscheck == '2':
                    imgtype = "erofs"
                else:
                    imgtype = "ext"
            else:
                imgtype = 'ext'
            for f in parts.keys():
                if pacall != '1':
                    imgcheck = input(f"  是否打包{parts[f]}?[1/0]	")
                else:
                    imgcheck = '1'
                if not imgcheck == '1':
                    continue
                yecho(f"打包{parts[f]}...")
                if types[f] == 'bootimg':
                    dboot(project + os.sep + parts[f], project + os.sep + parts[f] + ".img")
                elif types[f] == 'dtb':
                    makedtb(project + os.sep + parts[f], project)
                    pass
                elif types[f] == 'dtbo':
                    # makedtbo $partname
                    pass
                else:
                    pass
                    inpacker(parts[f], project, form, imgtype)
        elif filed == '66':
            pass
        # packsuper
        elif filed == '77':
            pass
        # packpayload
        elif filed == '88':
            return
        elif filed.isdigit():
            if int(filed) in parts.keys():
                if not settings.diyimgtype == '1' and types[int(filed)] not in ['bootimg', 'dtb', 'dtbo']:
                    op_menu = input("  输出所有文件格式[1]br [2]dat [3]img:")
                    if op_menu == '1':
                        form = 'br'
                    elif op_menu == '2':
                        form = "dat"
                    else:
                        form = 'img'
                else:
                    form = 'img'
                if settings.diyimgtype == '1' and types[int(filed)] not in ['bootimg', 'dtb', 'dtbo']:
                    syscheck = input("手动打包所有分区格式为：[1]ext4 [2]erofs")
                    if syscheck == '2':
                        imgtype = "erofs"
                    else:
                        imgtype = "ext"
                else:
                    imgtype = 'ext'
                yecho(f"打包{parts[int(filed)]}")
                if types[int(filed)] == 'bootimg':
                    dboot(project + os.sep + parts[int(filed)], project + os.sep + parts[int(filed)] + ".img")
                elif types[int(filed)] == 'dtb':
                    makedtb(project + os.sep + parts[int(filed)], project)
                    pass
                elif types[int(filed)] == 'dtbo':
                    # makedtbo $partname
                    pass
                else:
                    inpacker(parts[int(filed)], project, form, imgtype)
            else:
                ywarn("Input error!")
                time.sleep(2)
        else:
            ywarn("Input error!")
            time.sleep(2)
        packChoo(project)


def dboot(infile, orig):
    flag = ''
    if not os.path.exists(infile):
        print(f"Cannot Find {infile}...")
        return
    try:
        os.chdir(infile + os.sep + "ramdisk")
    except Exception as e:
        print("Ramdisk Not Found.. %s" % e)
        return
    cpio = ebinner + os.sep + "cpio"
    call("busybox find . | %s -H newc -R 0:0 -o -F ../ramdisk-new.cpio" % cpio)
    os.chdir(infile + os.sep)
    with open(infile + os.sep + "comp", "r", encoding='utf-8') as compf:
        comp = compf.read()
    print("Compressing:%s" % comp)
    if comp != "unknow":
        if call("magiskboot compress=%s ramdisk-new.cpio" % comp) != 0:
            print("Pack Ramdisk Fail...")
            os.remove("ramdisk-new.cpio")
            return
        else:
            print("Pack Ramdisk Successful..")
            try:
                os.remove("ramdisk.cpio")
            except:
                pass
            os.rename("ramdisk-new.cpio.%s" % comp, "ramdisk.cpio")
    else:
        print("Pack Ramdisk Successful..")
        os.remove("ramdisk.cpio")
        os.rename("ramdisk-new.cpio", "ramdisk.cpio")
    if comp == "cpio":
        flag = "-n"
    if call("magiskboot repack %s %s" % (flag, orig)) != 0:
        print("Pack boot Fail...")
        return
    else:
        os.remove(orig)
        os.rename(infile + os.sep + "new-boot.img", orig)
        os.chdir(LOCALDIR)
        try:
            rmdire(infile)
        except:
            print("删除错误...")
        print("Pack Successful...")


def unpackboot(file, project):
    name = os.path.basename(file).replace('.img', '')
    rmdire(project + os.sep + name)
    os.makedirs(project + os.sep + name)
    os.chdir(project + os.sep + name)
    if call("magiskboot unpack -h %s" % file) != 0:
        print("Unpack %s Fail..." % file)
        os.chdir(LOCALDIR)
        shutil.rmtree(project + os.sep + name)
        return
    if os.access(project + os.sep + name + os.sep + "ramdisk.cpio", os.F_OK):
        comp = gettype(project + os.sep + name + os.sep + "ramdisk.cpio")
        print("Ramdisk is %s" % comp)
        with open(project + os.sep + name + os.sep + "comp", "w") as f:
            f.write(comp)
        if comp != "unknow":
            os.rename(project + os.sep + name + os.sep + "ramdisk.cpio",
                      project + os.sep + name + os.sep + "ramdisk.cpio.comp")
            if call("magiskboot decompress %s %s" % (
                    project + os.sep + name + os.sep + "ramdisk.cpio.comp",
                    project + os.sep + name + os.sep + "ramdisk.cpio")) != 0:
                print("Decompress Ramdisk Fail...")
                return
        if not os.path.exists(project + os.sep + name + os.sep + "ramdisk"):
            os.mkdir(project + os.sep + name + os.sep + "ramdisk")
        os.chdir(project + os.sep + name + os.sep)
        print("Unpacking Ramdisk...")
        call("cpio -d --no-absolute-filenames -F %s -i -D %s" % ("ramdisk.cpio", "ramdisk"))
        os.chdir(LOCALDIR)
    else:
        print("Unpack Done!")
    os.chdir(LOCALDIR)


def undtb(project, infile):
    dtbdir = project + os.sep + os.path.basename(infile).split(".")[0] + "_dtbs"
    rmdire(dtbdir)
    if not os.path.exists(dtbdir):
        os.makedirs(dtbdir)
    extract_dtb.extract_dtb.split(Namespace(filename=infile, output_dir=dtbdir + os.sep + "dtb_files"))
    yecho("正在反编译dtb...")
    for i in os.listdir(dtbdir + os.sep + "dtb_files"):
        if i.endswith('.dtb'):
            name = i.split('.')[0]
            call(
                f'dtc -@ -I dtb -O dts {dtbdir + os.sep + "dtb_files" + os.sep + name + ".dtb"} -o {dtbdir + os.sep + "dtb_files" + os.sep + name + ".dts"}')
    open(project + os.sep + os.sep + "config" + os.sep + "dtbinfo_" + os.path.basename(infile).split(".")[0]).close()
    ysuc("反编译完成!")
    time.sleep(1)


def makedtb(sf, project):
    dtbdir = project + os.sep + sf + "_dtbs"
    rmdire(dtbdir + os.sep + "new_dtb_files")
    os.makedirs(dtbdir + os.sep + "new_dtb_files")
    for dts_files in os.listdir(dtbdir + os.sep + "dts_files"):
        new_dtb_files = dts_files.split('.')[0]
        yecho(f"正在回编译{dts_files}为{new_dtb_files}.dtb")
        if call(f'dtc -@ -I "dts" -O "dtb" "{dtbdir + os.sep + "dts_files" + os.sep + dts_files}" -o "$dtbdir/new_dtb_files/$new_dtb_files.dtb"') != 0:
            ywarn("回编译dtb失败")
    with open(project + os.sep + "TI_out" + os.sep + sf, 'wb') as sff:
        for dtb in os.listdir(dtbdir + os.sep + "new_dtb_files"):
            if dtb.endswith('.dtb'):
                with open(os.path.abspath(dtb), 'rb') as f:
                    sff.write(f.read())
    ysuc("回编译完成！")
    time.sleep(2)


def undtbo(project, infile):
    dtbodir = project + os.sep + os.path.basename(infile).split('.')[0]
    open(project + os.sep + "config" + os.sep + "dtboinfo_" + os.path.basename(infile).split('.')[0], 'w').close()
    rmdire(dtbodir)
    if not os.path.exists(dtbodir + os.sep + "dtbo_files"):
        os.makedirs(dtbodir + os.sep + "dtbo_files")
        try:
            os.makedirs(dtbodir + os.sep + "dts_files")
        except:
            pass
    yecho("正在解压dtbo.img")
    mkdtboimg.dump_dtbo(infile, dtbodir + os.sep + "dtbo_files" + os.sep + "dtbo")
    for dtbo_files in os.listdir(dtbodir + os.sep + "dtbo_files"):
        if dtbo_files.startswith('dtbo.'):
            dts_files = dtbo_files.replace("dtbo", 'dts')
            yecho(f"正在反编译{dtbo_files}为{dts_files}")
            if call(f'dtc -@ -I "dtb" -O "dts" {dtbodir + os.sep + "dtbo_files" + os.sep + dtbo_files} -o "{dtbodir + os.sep + "dts_files" + os.sep + dts_files}"') != 0:
                ywarn(f"反编译{dtbo_files}失败！")
    ysuc("完成！")
    time.sleep(1)


def makedtbo(sf, project):
    dtbodir = project + os.sep + os.path.basename(sf).split('.')[0]
    rmdire(dtbodir + os.sep + 'new_dtbo_files')
    if os.path.exists(project + os.sep + os.path.basename(sf).split('.')[0] + '.img'): os.remove(
        project + os.sep + os.path.basename(sf).split('.')[0] + '.img')
    os.makedirs(dtbodir + os.sep + 'new_dtbo_files')
    for dts_files in os.listdir(dtbodir + os.sep + 'dts_files'):
        new_dtbo_files = dts_files.replace('dts', 'dtbo')
        yecho(f"正在回编译{dts_files}为{new_dtbo_files}")
        call(
            f'dtc -@ -I "dts" -O "dtb" {dtbodir + os.sep + "dts_files" + dts_files} -o {dtbodir + os.sep + "new_dtbo_files" + os.sep + new_dtbo_files}')
    yecho("正在生成dtbo.img...")
    list_ = []
    for b in os.listdir(dtbodir + os.sep + "new_dtbo_files"):
        if b.startswith('dtbo.'):
            list_.append(dtbodir + os.sep + "new_dtbo_files"+os.sep+b)
    list_ = sorted(list_, key=lambda x: int(x.rsplit('.')[1]))
    try:
        mkdtboimg.create_dtbo(project + os.sep + os.path.basename(sf).split('.')[0] + '.img', list_, 4096)
    except:
        ywarn(f"{os.path.basename(sf).split('.')[0]}.img生成失败!")
    else:
        ysuc(f"{os.path.basename(sf).split('.')[0]}.img生成完毕!")
    time.sleep(2)


def inpacker(name, project, form, ftype):
    mount_path = f"/{name}"
    file_contexts = project + os.sep + "config" + os.sep + name + "_file_contexts"
    fs_config = project + os.sep + "config" + os.sep + name + "_fs_config"
    if not settings.utcstamp:
        UTC = int(time.time())
    else:
        UTC = settings.utcstamp
    out_img = project + os.sep + name + ".img"
    in_files = project + os.sep + name
    if os.path.exists(project + os.sep + "config" + os.sep + name + "_size.txt"):
        img_size0 = int(cat(project + os.sep + "config" + os.sep + name + "_size.txt"))
    else:
        img_size0 = 0
    img_size1 = dirsize(in_files, 1, 1).rsize_v
    if settings.diysize == '1' and img_size0 < img_size1:
        ywarn("您设置的size过小,将动态调整size!")
        img_size0 = dirsize(in_files, 1, 3, project + os.sep + "dynamic_partitions_op_list").rsize_v
    elif settings.diysize == '1':
        img_size0 = dirsize(in_files, 1, 3, project + os.sep + "dynamic_partitions_op_list").rsize_v
    else:
        img_size0 = dirsize(in_files, 1, 1, project + os.sep + "dynamic_partitions_op_list").rsize_v
    fspatch.main(in_files, fs_config)
    contextpatch.main(in_files, file_contexts)
    utils.qc(fs_config)
    utils.qc(file_contexts)
    size = img_size0 / int(settings.BLOCKSIZE)
    size = int(size)
    if ftype == 'erofs':
        call(
            f'mkfs.erofs {settings.erofslim} --mount-point {mount_path} --fs-config-file {fs_config} --file-contexts {file_contexts} {out_img} {in_files}')
    else:
        if settings.pack_e2 == '0':
            call(
                f'make_ext4fs -J -T {UTC} -S {file_contexts} -l {img_size0} -C {fs_config} -L {name} -a {name} {out_img} {in_files}')
        else:
            call(
                f'mke2fs -O ^has_journal -L {name} -I 256 -i {settings.inodesize} -M {mount_path} -m 0 -t ext4 -b {settings.BLOCKSIZE} {out_img} {size}')
            call(
                f'e2fsdroid -e -T {UTC} {settings.extrw} -C {fs_config} -S {file_contexts} -f {in_files} -a {mount_path} {out_img}')
    if settings.diysize == '':
        yecho("压缩img中...")
        if form == 'erofs':
            yecho("Erofs镜像，跳过压缩...")
        else:
            call(f'resize2fs - f - M {out_img}')
    if settings.pack_sparse == '1' or form == 'dat':
        call(f"img2simg {out_img} {out_img}.s")
        os.remove(out_img)
        os.rename(out_img + ".s", out_img)
    if form == 'br':
        try:
            os.remove(project + os.sep + "TI_out" + os.sep + name + ".new.dat.br")
            os.remove(project + os.sep + "TI_out" + os.sep + name + ".patch.dat")
            os.remove(project + os.sep + "TI_out" + os.sep + name + ".transfer.list")
        except:
            pass
    elif form == 'dat':
        try:
            os.remove(project + os.sep + "TI_out" + os.sep + name + ".new.dat")
            os.remove(project + os.sep + "TI_out" + os.sep + name + ".patch.dat")
            os.remove(project + os.sep + "TI_out" + os.sep + name + ".transfer.list")
        except:
            pass
    else:
        try:
            os.rename(out_img, project + os.sep + "TI_out" + os.sep + name + ".img")
        except:
            pass
    if form == 'dat':
        try:
            os.remove(project + os.sep + "TI_out" + os.sep + name + ".new.dat")
            os.remove(project + os.sep + "TI_out" + os.sep + name + ".new.dat.br")
            os.remove(project + os.sep + "TI_out" + os.sep + name + ".patch.dat")
            os.remove(project + os.sep + "TI_out" + os.sep + name + ".transfer.list")
        except:
            pass
        utils.img2sdat(out_img, project + os.sep + "TI_out", 4, name)
        try:
            os.remove(out_img)
        except:
            pass
    if form == 'br':
        call(
            f'brotli -q {settings.brcom} -j -w 24 {project + os.sep + "TI_out" + os.sep + name + ".new.dat"} -o {project + os.sep + "TI_out" + os.sep + name + ".new.dat.br"}')


def unpack(file, info, project):
    cleantemp()
    if not os.path.exists(project + os.sep + 'config'):
        os.makedirs(project + os.sep + 'config')
    yecho(f"[{info}]解包{os.path.basename(file)}中...")
    if info == 'sparse':
        simg2img(file)
        unpack(file, gettype(file), project)
    elif info == 'dtbo':
        undtbo(project, os.path.abspath(file))
    elif info == 'br':
        call(f'brotli -dj {file}')
        partname = os.path.basename(file).replace('.new.dat.br', '')
        filepath = os.path.dirname(file)
        unpack(os.path.join(filepath, partname + ".new.dat"), 'dat', project)
    elif info == 'dtb':
        undtb(project, os.path.abspath(file))
    elif info == 'dat':
        partname = os.path.basename(file).replace('.new.dat', '')
        filepath = os.path.dirname(file)
        utils.sdat2img(os.path.join(filepath, partname + '.transfer.list'),
                       os.path.join(filepath, partname + ".new.dat"), os.path.join(filepath, partname + ".img"))
        try:
            os.remove(os.path.join(filepath, partname + ".new.dat"))
            os.remove(os.path.join(filepath, partname + '.transfer.list'))
            os.remove(os.path.join(filepath, partname + '.patch.dat'))
        except:
            pass
        unpack(os.path.join(filepath, partname + ".img"), gettype(os.path.join(filepath, partname + ".img")), project)
    elif info == 'img':
        unpack(file, gettype(file), project)
    elif info == 'ofp':
        ofpm = input(" ROM机型处理器为？[1]高通 [2]MTK	")
        if ofpm == '1':
            ofp_qc_decrypt.main(file, project)
        elif ofpm == '2':
            ofp_mtk_decrypt.main(file, project)
    elif info == 'ozip':
        ozipdecrypt.main(file)
        try:
            os.remove(file)
        except Exception as e:
            print(f"错误！{e}")
        zipfile.ZipFile(file.replace('.ozip', '.zip')).extractall(project)
    elif info == 'ops':
        call(f'python3 opscrypto.py decrypt {file}')
    elif info == 'payload':
        yecho(f"{os.path.basename(file)}所含分区列表：")
        call(f'payload-dumper-go -l {file}')
        extp = input("请输入需要解压的分区名(空格隔开)/all[全部]	")
        if extp == 'all':
            call(f"payload-dumper-go -o {project} {file}")
        else:
            for p in extp.split():
                call(f'payload-dumper-go -p {p} -o {project} {file}')
    elif info == 'win000':
        for fd in [f for f in os.listdir(project) if re.search(r'\.win\d+', f)]:
            with open(project + os.path.basename(fd).rsplit('.', 1)[0], 'ab') as ofd:
                for fd1 in sorted(
                        [f for f in os.listdir(project) if f.startswith(os.path.basename(fd).rsplit('.', 1)[0] + ".")],
                        key=lambda x: int(x.rsplit('.')[3])):
                    print("合并%s到%s" % (fd1, os.path.basename(fd).rsplit('.', 1)[0]))
                    with open(project + os.sep + fd1, 'rb') as nfd:
                        ofd.write(nfd.read())
                    os.remove(project + os.sep + fd1)
        filepath = os.path.dirname(file)
        unpack(os.path.join(filepath, file), gettype(os.path.join(filepath, file)), project)
    elif info == 'win':
        filepath = os.path.dirname(file)
        unpack(os.path.join(filepath, file), gettype(os.path.join(filepath, file)), project)
    elif info == 'ext':
        imgextractor.Extractor().main(file, project + os.sep + os.path.basename(file.split('.')[0]), project)
        try:
            os.remove(file)
        except:
            pass
    elif info == 'dat.1':
        for fd in [f for f in os.listdir(project) if re.search(r'\.new\.dat\.\d+', f)]:
            with open(project + os.sep + os.path.basename(fd).rsplit('.', 1)[0], 'ab') as ofd:
                for fd1 in sorted(
                        [f for f in os.listdir(project) if f.startswith(os.path.basename(fd).rsplit('.', 1)[0] + ".")],
                        key=lambda x: int(x.rsplit('.')[3])):
                    print("合并%s到%s" % (fd1, os.path.basename(fd).rsplit('.', 1)[0]))
                    with open(project + os.sep + fd1, 'rb') as nfd:
                        ofd.write(nfd.read())
                    os.remove(project + os.sep + fd1)
        partname = os.path.basename(file).replace('.new.dat.1', '')
        filepath = os.path.dirname(file)
        utils.sdat2img(os.path.join(filepath, partname + '.transfer.list'),
                       os.path.join(filepath, partname + ".new.dat"), os.path.join(filepath, partname + ".img"))
        unpack(os.path.join(filepath, partname + ".img"), gettype(os.path.join(filepath, partname + ".img")), project)
    elif info == 'erofs':
        call(f'extract.erofs -i {os.path.abspath(file)} -o {project} -x ')
        open(project + os.sep + 'cpnfig' + os.sep + os.path.basename(file) + "_erofs", 'w').close()
    elif info == 'super':
        lpunpack.unpack(os.path.abspath(file), project)
    elif info in ['boot', 'vendor_boot']:
        unpackboot(os.path.abspath(file), project)
    else:
        ywarn("未知格式！")


def unpackrom():
    os.chdir(LOCALDIR)
    cls()
    zipn = 0
    zips = {}
    print(" \033[31m >ROM列表 \033[0m\n")
    ywarn(f"   请将ROM置于{LOCALDIR}下！")
    if dir_has(LOCALDIR, '.zip'):
        for zip0 in os.listdir(LOCALDIR):
            if zip0.endswith('.zip'):
                if os.path.isfile(os.path.abspath(zip0)):
                    if getsize(os.path.abspath(zip0)) >= int(settings.plugromlit):
                        zipn += 1
                        print(f"   [{zipn}]- {zip0}\n")
                        zips[zipn] = zip0
    else:
        ywarn("	没有ROM文件！")
    print("--------------------------------------------------\n")
    print()
    zipd = input("请输入对应序列号：")
    if int(zipd) in zips.keys():
        projec = input("请输入项目名称(可留空)：")
        if projec:
            project = "TI_%s" % projec
        else:
            project = "TI_%s" % os.path.basename(zips[int(zipd)]).replace('.zip', '')
        if os.path.exists(LOCALDIR + os.sep + project):
            project = project + time.strftime("%m%d%H%M%S")
            ywarn(f"项目已存在！自动命名为：{project}")
        os.makedirs(LOCALDIR + os.sep + project)
        print(f"创建{project}成功！")
        yecho("解压刷机包中...")
        zipfile.ZipFile(os.path.abspath(zips[int(zipd)])).extractall(LOCALDIR + os.sep + project)
        menu(project)
        yecho("分解ROM中...")
        autounpack(LOCALDIR + os.sep + project)
    else:
        ywarn("Input error!")


def autounpack(project):
    cleantemp()
    yecho("自动解包开始！")
    if os.path.exists(project + os.sep + "payload.bin"):
        yecho('读取机型为:动态VAB设备\n解包 payload.bin...')
        call(f"payload-dumper-go {project + os.sep + 'payload.bin'} -o {project}")
        yecho("payload.bin解包完成！")
        for waste in ['payload.bin', 'care_map.pb', 'apex_info.pb']:
            if os.path.exists(project + os.sep + waste):
                try:
                    os.remove(project + os.sep + waste)
                except:
                    pass
        os.makedirs(project + os.sep + "config")
        shutil.move(project + os.sep + "payload_properties.txt", project + os.sep + "config")
        shutil.move(project + os.sep + "META-INF" + os.sep + "com" + os.sep + "android" + os.sep + "metadata",
                    project + os.sep + "config")
        for infile in os.listdir(project):
            filetype = gettype(os.path.abspath(infile))
            unpack(os.path.abspath(infile), filetype, project)
            os.remove(os.path.abspath(infile))
    else:
        for infile in os.listdir(project):
            if infile.endswith('.new.dat.br'):
                unpack(os.path.abspath(infile), 'br', project)
            elif infile.endswith('.dat.1'):
                unpack(os.path.abspath(infile), 'dat.1', project)
            elif infile.endswith('.new.dat'):
                unpack(os.path.abspath(infile), 'dat', project)
            elif infile.endswith('.img'):
                unpack(os.path.abspath(infile), 'img', project)


promenu()
