import hashlib
import json
import os
import re
import time

import uuid
import requests

class Pan123:
    def __init__(
            self,
            readfile=True,
            user_name="",
            pass_word="",
            authorization="",
            input_pwd=True,
    ):
        self.cookies = None
        self.recycle_list = None
        self.list = []
        if readfile:
            self.read_ini(user_name, pass_word, input_pwd, authorization)
        else:
            if user_name == "" or pass_word == "":
                print("读取已禁用，用户名或密码为空")
                if input_pwd:
                    user_name = input("请输入用户名:")
                    pass_word = input("请输入密码:")
                else:
                    raise Exception("用户名或密码为空：读取禁用时，用户名和密码不能为空")
            self.user_name = user_name
            self.password = pass_word
            self.authorization = authorization
        self.header_logined = {
            "user-agent": "123pan/v2.4.0(Android_7.1.2;Xiaomi)",
            "authorization": self.authorization,
            "accept-encoding": "gzip",
            "content-type": "application/json",
            "osversion": "Android_7.1.2",
            "loginuuid": str(uuid.uuid4().hex),
            "platform": "android",
            "devicetype": "M2101K9C",
            "x-channel": "1004",
            "devicename": "Xiaomi",
            "host": "www.123pan.com",
            "app-version": "61",
            "x-app-version": "2.4.0"
        }
        self.parent_file_id = 0
        self.parent_file_list = [0]

    def login(self, max_retries=3):
        data = {"type": 1, "passport": self.user_name, "password": self.password}
        url = "https://www.123pan.com/b/api/user/sign_in"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }

        retry_count = 0
        while retry_count < max_retries:
            try:
                login_res = requests.post(
                    url,
                    headers=headers,
                    data=data,
                    proxies={"http": None, "https": None},
                    timeout=10
                )

                res_sign = login_res.json()
                res_code_login = res_sign["code"]
                if res_code_login != 200:
                    print(res_sign["message"])
                    retry_count += 1
                    print(f"登录失败，正在尝试第 {retry_count} 次重试...")
                    continue  # 登录业务失败，重试

                set_cookies = login_res.headers.get("Set-Cookie", "")
                set_cookies_list = {}

                for cookie in set_cookies.split(";"):
                    if "=" in cookie:
                        key, value = cookie.strip().split("=", 1)
                        set_cookies_list[key] = value
                    else:
                        set_cookies_list[cookie.strip()] = None

                self.cookies = set_cookies_list

                token = res_sign["data"]["token"]
                self.authorization = "Bearer " + token
                self.header_logined["authorization"] = self.authorization
                self.save_file()

                return res_code_login  # 成功返回原始 code（200）

            except requests.exceptions.ProxyError:
                print("连接失败：代理错误，请检查网络设置")
            except requests.exceptions.ConnectionError:
                print("连接失败：无法连接到服务器，请检查网络")
            except requests.exceptions.Timeout:
                print("连接失败：请求超时，请重试")
            except ValueError:
                print("登录失败：响应不是合法的 JSON 数据")
            except Exception as e:
                print(f"登录失败: {e}")

            retry_count += 1
            if retry_count < max_retries:
                print(f"发生异常，正在尝试第 {retry_count} 次重试...")

        return -1  # 所有重试失败后返回 -1

    def save_file(self):
        with open("123pan.txt", "w", encoding="utf_8") as f:
            save_list = {
                "userName": self.user_name,
                "passWord": self.password,
                "authorization": self.authorization,
            }

            f.write(json.dumps(save_list))

    def get_dir(self):
        res_code_getdir = 0
        page = 1
        lists = []
        lenth_now = 0
        total = -1
        while lenth_now < total or total == -1:
            base_url = "https://www.123pan.com/b/api/file/list/new"
            # print(self.headerLogined)
            # sign = getSign("/b/api/file/list/new")
            # print(sign)
            params = {
                # sign[0]: sign[1],
                "driveId": 0,
                "limit": 100,
                "next": 0,
                "orderBy": "file_id",
                "orderDirection": "desc",
                "parentFileId": str(self.parent_file_id),
                "trashed": False,
                "SearchData": "",
                "Page": str(page),
                "OnlyLookAbnormalFile": 0,
            }
            try:
                a = requests.get(base_url, headers=self.header_logined, params=params, timeout=10)  # , verify=False)
            except:
                print("连接失败")
                return -1
            # print(a.text)
            # print(a.headers)
            text = a.json()
            res_code_getdir = text["code"]
            if res_code_getdir != 0:
                #print(a.text)
                #print(a.headers)
                print("code = 2 Error:" + str(res_code_getdir))
                return res_code_getdir
            lists_page = text["data"]["InfoList"]
            lists += lists_page
            total = text["data"]["Total"]
            lenth_now += len(lists_page)
            page += 1
        file_num = 0
        for i in lists:
            i["FileNum"] = file_num
            file_num += 1

        self.list = lists
        return res_code_getdir

    def show(self):
        for i in self.list:
            file_size = i["Size"]
            if file_size > 1048576:
                download_size_print = str(round(file_size / 1048576, 2)) + "M"
            else:
                download_size_print = str(round(file_size / 1024, 2)) + "K"


    # fileNumber 从0开始，0为第一个文件，传入时需要减一 ！！！
    def link(self, file_number, showlink=True):
        file_detail = self.list[file_number]
        type_detail = file_detail["Type"]
        if type_detail == 1:
            down_request_url = "https://www.123pan.com/a/api/file/batch_download_info"
            down_request_data = {"fileIdList": [{"fileId": int(file_detail["FileId"])}]}

        else:
            down_request_url = "https://www.123pan.com/a/api/file/download_info"
            down_request_data = {
                "driveId": 0,
                "etag": file_detail["Etag"],
                "fileId": file_detail["FileId"],
                "s3keyFlag": file_detail["S3KeyFlag"],
                "type": file_detail["Type"],
                "fileName": file_detail["FileName"],
                "size": file_detail["Size"],
            }
        # print(down_request_data)

        # sign = getSign("/a/api/file/download_info")

        link_res = requests.post(
            down_request_url,
            headers=self.header_logined,
            # params={sign[0]: sign[1]},
            data=json.dumps(down_request_data),
            timeout=10
        )
        # print(linkRes.text)
        res_code_download = link_res.json()["code"]
        if res_code_download != 0:
            print("code = 3 Error:" + str(res_code_download))
            # print(linkRes.json())
            return res_code_download
        down_load_url = link_res.json()["data"]["DownloadUrl"]
        next_to_get = requests.get(down_load_url, timeout=10, allow_redirects=False).text
        url_pattern = re.compile(r"href='(https?://[^']+)'")
        redirect_url = url_pattern.findall(next_to_get)[0]
        if showlink:
            print()

        return redirect_url

    def download(self, file_number,download_path="download/"):
        file_detail = self.list[file_number]
        if file_detail["Type"] == 1:
            print("打包下载")
            file_name = file_detail["FileName"] + ".zip"
        else:
            file_name = file_detail["FileName"]  # 文件名
        down_load_url = self.link(file_number, showlink=False)

        if os.path.exists(download_path+file_name):
            print("文件 " + file_name + " 已存在，是否要覆盖？")
            sure_download = input("输入1覆盖，2取消：")
            if sure_download != "1":
                return

        if not os.path.exists(download_path):
            print("文件夹不存在，创建文件夹")
            os.makedirs(download_path)
        down = requests.get(down_load_url, stream=True, timeout=10)

        file_size = int(down.headers["Content-Length"])  # 文件大小
        content_size = int(file_size)  # 文件总大小
        data_count = 0  # 当前已传输的大小
        if file_size > 1048576:
            size_print_download = str(round(file_size / 1048576, 2)) + "M"
        else:
            size_print_download = str(round(file_size / 1024, 2)) + "K"
        print(file_name + "    " + size_print_download)
        time1 = time.time()
        time_temp = time1
        data_count_temp = 0
        with open(download_path+file_name, "wb") as f:
            for i in down.iter_content(1024):
                f.write(i)
                done_block = int((data_count / content_size) * 50)
                data_count = data_count + len(i)
                # 实时进度条进度
                now_jd = (data_count / content_size) * 100
                # %% 表示%
                # 测速
                time1 = time.time()
                pass_time = time1 - time_temp
                if pass_time > 1:
                    time_temp = time1
                    pass_data = int(data_count) - int(data_count_temp)
                    data_count_temp = data_count
                    speed = pass_data / int(pass_time)
                    speed_m = speed / 1048576
                    if speed_m > 1:
                        speed_print = str(round(speed_m, 2)) + "M/S"
                    else:
                        speed_print = str(round(speed_m * 1024, 2)) + "K/S"
                    print(
                        "\r [%s%s] %d%%  %s"
                        % (
                            done_block * "█",
                            " " * (50 - 1 - done_block),
                            now_jd,
                            speed_print,
                        ),
                        end="",
                    )
                elif data_count == content_size:
                    print("\r [%s%s] %d%%  %s" % (50 * "█", "", 100, ""), end="")
            print("\nok")

    def recycle(self):
        recycle_id = 0
        url = (
                "https://www.123pan.com/a/api/file/list/new?driveId=0&limit=100&next=0"
                "&orderBy=fileId&orderDirection=desc&parentFileId="
                + str(recycle_id)
                + "&trashed=true&&Page=1"
        )
        recycle_res = requests.get(url, headers=self.header_logined, timeout=10)
        json_recycle = recycle_res.json()
        recycle_list = json_recycle["data"]["InfoList"]
        self.recycle_list = recycle_list

    # fileNumber 从0开始，0为第一个文件，传入时需要减一 ！！！
    def delete_file(self, file, by_num=True, operation=True):
        # operation = 'true' 删除 ， operation = 'false' 恢复
        if by_num:
            print(file)
            if not str(file).isdigit():
                print("请输入数字")
                return -1
            if 0 <= file < len(self.list):
                file_detail = self.list[file]
            else:
                print("不在合理范围内")
                return
        else:
            if file in self.list:
                file_detail = file
            else:
                print("文件不存在")
                return
        data_delete = {
            "driveId": 0,
            "fileTrashInfoList": file_detail,
            "operation": operation,
        }
        delete_res = requests.post(
            "https://www.123pan.com/a/api/file/trash",
            data=json.dumps(data_delete),
            headers=self.header_logined,
            timeout=10
        )
        dele_json = delete_res.json()
        print(dele_json)
        message = dele_json["message"]
        print(message)

    def share(self):
        file_id_list = ""
        share_name_list = []
        add = "1"
        while str(add) == "1":
            share_num = input("分享文件的编号：")
            num_test2 = share_num.isdigit()
            if num_test2:
                share_num = int(share_num)
                if 0 < share_num < len(self.list) + 1:
                    share_id = self.list[int(share_num) - 1]["FileId"]
                    share_name = self.list[int(share_num) - 1]["FileName"]
                    share_name_list.append(share_name)
                    print(share_name_list)
                    file_id_list = file_id_list + str(share_id) + ","
                    add = input("输入1添加文件，0发起分享，其他取消")
            else:
                print("请输入数字，，")
                add = "1"
        if str(add) == "0":
            share_pwd = input("提取码，不设留空：")
            file_id_list = file_id_list.strip(",")
            data = {
                "driveId": 0,
                "expiration": "2099-12-12T08:00:00+08:00",
                "fileIdList": file_id_list,
                "shareName": "My Share",
                "sharePwd": share_pwd,
                "event": "shareCreate"
            }
            share_res = requests.post(
                "https://www.123pan.com/a/api/share/create",
                headers=self.header_logined,
                data=json.dumps(data),
                timeout=10
            )
            share_res_json = share_res.json()
            if share_res_json["code"] != 0:
                print(share_res_json["message"])
                print("分享失败")
                return
            message = share_res_json["message"]
            print(message)
            share_key = share_res_json["data"]["ShareKey"]
            share_url = "https://www.123pan.com/s/" + share_key
            print("分享链接：\n" + share_url + "提取码：" + share_pwd)
        else:
            print("退出分享")

    def up_load(self, file_path):
        file_path = file_path.replace('"', "")
        file_path = file_path.replace("\\", "/")
        file_name = file_path.split("/")[-1]
        print("文件名:", file_name)
        if not os.path.exists(file_path):
            print("文件不存在，请检查路径是否正确")
            return
        if os.path.isdir(file_path):
            print("暂不支持文件夹上传")
            return
        fsize = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            md5 = hashlib.md5()
            while True:
                data = f.read(64 * 1024)
                if not data:
                    break
                md5.update(data)
            readable_hash = md5.hexdigest()

        list_up_request = {
            "driveId": 0,
            "etag": readable_hash,
            "fileName": file_name,
            "parentFileId": self.parent_file_id,
            "size": fsize,
            "type": 0,
            "duplicate": 0,
        }

        # sign = getSign("/b/api/file/upload_request")
        up_res = requests.post(
            "https://www.123pan.com/b/api/file/upload_request",
            headers=self.header_logined,
            # params={sign[0]: sign[1]},
            data=list_up_request,
            timeout=10
        )
        up_res_json = up_res.json()
        res_code_up = up_res_json["code"]
        if res_code_up == 5060:
            sure_upload = input("检测到1个同名文件,输入1覆盖，2保留两者，0取消：")
            if sure_upload == "1":
                list_up_request["duplicate"] = 1

            elif sure_upload == "2":
                list_up_request["duplicate"] = 2
            else:
                print("取消上传")
                return
            # sign = getSign("/b/api/file/upload_request")
            up_res = requests.post(
                "https://www.123pan.com/b/api/file/upload_request",
                headers=self.header_logined,
                # params={sign[0]: sign[1]},
                data=json.dumps(list_up_request),
                timeout=10
            )
            up_res_json = up_res.json()
        res_code_up = up_res_json["code"]
        if res_code_up == 0:
            # print(upResJson)
            # print("上传请求成功")
            reuse = up_res_json["data"]["Reuse"]
            if reuse:
                print("上传成功，文件已MD5复用")
                return
        else:
            print(up_res_json)
            print("上传请求失败")
            return

        bucket = up_res_json["data"]["Bucket"]
        storage_node = up_res_json["data"]["StorageNode"]
        upload_key = up_res_json["data"]["Key"]
        upload_id = up_res_json["data"]["UploadId"]
        up_file_id = up_res_json["data"]["FileId"]  # 上传文件的fileId,完成上传后需要用到
        print("上传文件的fileId:", up_file_id)

        # 获取已将上传的分块
        start_data = {
            "bucket": bucket,
            "key": upload_key,
            "uploadId": upload_id,
            "storageNode": storage_node,
        }
        start_res = requests.post(
            "https://www.123pan.com/b/api/file/s3_list_upload_parts",
            headers=self.header_logined,
            data=json.dumps(start_data),
            timeout=10
        )
        start_res_json = start_res.json()
        res_code_up = start_res_json["code"]
        if res_code_up == 0:
            # print(startResJson)
            pass
        else:
            print(start_data)
            print(start_res_json)

            print("获取传输列表失败")
            return

        # 分块，每一块取一次链接，依次上传
        block_size = 5242880
        with open(file_path, "rb") as f:
            part_number_start = 1
            put_size = 0
            while True:
                data = f.read(block_size)

                precent = round(put_size / fsize, 2)
                print("\r已上传：" + str(precent * 100) + "%", end="")
                put_size = put_size + len(data)

                if not data:
                    break
                get_link_data = {
                    "bucket": bucket,
                    "key": upload_key,
                    "partNumberEnd": part_number_start + 1,
                    "partNumberStart": part_number_start,
                    "uploadId": upload_id,
                    "StorageNode": storage_node,
                }

                get_link_url = (
                    "https://www.123pan.com/b/api/file/s3_repare_upload_parts_batch"
                )
                get_link_res = requests.post(
                    get_link_url,
                    headers=self.header_logined,
                    data=json.dumps(get_link_data),
                    timeout=10
                )
                get_link_res_json = get_link_res.json()
                res_code_up = get_link_res_json["code"]
                if res_code_up == 0:
                    # print("获取链接成功")
                    pass
                else:
                    # print(getLinkResJson)
                    return
                # print(getLinkResJson)
                upload_url = get_link_res_json["data"]["presignedUrls"][
                    str(part_number_start)
                ]
                # print("上传链接",uploadUrl)
                requests.put(upload_url, data=data, timeout=10)
                # print("put")

                part_number_start = part_number_start + 1

        print()
        # 完成标志
        # 1.获取已上传的块
        uploaded_list_url = "https://www.123pan.com/b/api/file/s3_list_upload_parts"
        uploaded_comp_data = {
            "bucket": bucket,
            "key": upload_key,
            "uploadId": upload_id,
            "storageNode": storage_node,
        }
        # print(uploadedCompData)
        requests.post(
            uploaded_list_url,
            headers=self.header_logined,
            data=json.dumps(uploaded_comp_data),
            timeout=10
        )
        compmultipart_up_url = (
            "https://www.123pan.com/b/api/file/s3_complete_multipart_upload"
        )
        requests.post(
            compmultipart_up_url,
            headers=self.header_logined,
            data=json.dumps(uploaded_comp_data),
            timeout=10
        )

        # 3.报告完成上传，关闭upload session
        if fsize > 64 * 1024 * 1024:
            time.sleep(3)
        close_up_session_url = "https://www.123pan.com/b/api/file/upload_complete"
        close_up_session_data = {"fileId": up_file_id}
        # print(closeUpSessionData)
        close_up_session_res = requests.post(
            close_up_session_url,
            headers=self.header_logined,
            data=json.dumps(close_up_session_data),
            timeout=10
        )
        close_res_json = close_up_session_res.json()
        # print(closeResJson)
        res_code_up = close_res_json["code"]
        if res_code_up == 0:
            print("上传成功")
        else:
            print("上传失败")
            print(close_res_json)
            return

    # dirId 就是 fileNumber，从0开始，0为第一个文件，传入时需要减一 ！！！（好像文件夹都排在前面）
    def cd(self, dir_num):
        if not dir_num.isdigit():
            if dir_num == "..":
                if len(self.parent_file_list) > 1:
                    self.parent_file_list.pop()
                    self.parent_file_id = self.parent_file_list[-1]
                    self.get_dir()
                    self.show()
                else:
                    print("已经是根目录")
                return
            if dir_num == "/":
                self.parent_file_id = 0
                self.parent_file_list = [0]
                self.get_dir()
                self.show()
                return
            print("输入错误")
            return
        dir_num = int(dir_num) - 1
        if dir_num >= (len(self.list) - 1) or dir_num < 0:
            print("输入错误")
            return
        if self.list[dir_num]["Type"] != 1:
            print("不是文件夹")
            return
        self.parent_file_id = self.list[dir_num]["FileId"]
        self.parent_file_list.append(self.parent_file_id)
        self.get_dir()
        self.show()

    def cdById(self, file_id):
        self.parent_file_id = file_id
        self.parent_file_list.append(self.parent_file_id)
        self.get_dir()
        self.get_dir()
        self.show()

    def read_ini(
            self,
            user_name,
            pass_word,
            input_pwd,
            authorization="",
    ):
        try:
            with open("123pan.txt", "r", encoding="utf-8") as f:
                text = f.read()
            text = json.loads(text)
            user_name = text["userName"]
            pass_word = text["passWord"]
            authorization = text["authorization"]

        except:  # FileNotFoundError or json.decoder.JSONDecodeError:

            if user_name == "" or pass_word == "":
                if input_pwd:
                    user_name = input("userName:")
                    pass_word = input("passWord:")
                    authorization = ""
                else:
                    raise Exception("禁止输入模式下，没有账号或密码")

        self.user_name = user_name
        self.password = pass_word
        self.authorization = authorization

    def mkdir(self, dirname, remakedir=False):
        if not remakedir:
            for i in self.list:
                if i["FileName"] == dirname:
                    print("文件夹已存在")
                    return i["FileId"]

        url = "https://www.123pan.com/a/api/file/upload_request"
        data_mk = {
            "driveId": 0,
            "etag": "",
            "fileName": dirname,
            "parentFileId": self.parent_file_id,
            "size": 0,
            "type": 1,
            "duplicate": 1,
            "NotReuse": True,
            "event": "newCreateFolder",
            "operateType": 1,
        }
        # sign = getSign("/a/api/file/upload_request")
        res_mk = requests.post(
            url,
            headers=self.header_logined,
            data=json.dumps(data_mk),
            # params={sign[0]: sign[1]},
            timeout=10
        )
        try:
            res_json = res_mk.json()
            # print(res_json)
        except json.decoder.JSONDecodeError:
            print("创建失败")
            print(res_mk.text)
            return
        code_mkdir = res_json["code"]

        if code_mkdir == 0:
            print("创建成功: ", res_json["data"]["FileId"])
            self.get_dir()
            return res_json["data"]["Info"]["FileId"]
        print(res_json)
        print("创建失败")
        return