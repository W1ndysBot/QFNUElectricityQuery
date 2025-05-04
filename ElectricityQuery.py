import requests
import os
from dotenv import load_dotenv

load_dotenv()


class ElectricityQuery:
    def __init__(self, openID):
        self.openID = openID

    def get_query(self):
        url = "http://wechat.sdkdch.cn/wx/api/user/get?openId=" + self.openID
        return self.get_data(url)

    def get_data(self, url):
        response = requests.get(url)
        return response.json()

    def parse_result(self, result=None):
        """解析查询结果并返回格式化的信息"""
        if result is None:
            result = self.get_query()

        if result.get("code") != 200:
            return f"查询失败: {result.get('msg', '未知错误')}"

        if result.get("total") == 0 or not result.get("rows"):
            return "未找到电费信息"

        user_info = result["rows"][0]
        formatted_info = {
            "用户编号": user_info.get("userNumber", "无"),
            "用户名": user_info.get("userName", "无"),
            "余额": user_info.get("balance", "0"),
            "地址": user_info.get("address", "无"),
            "客户名称": user_info.get("customerName", "无"),
        }

        return formatted_info

    def get_balance(self):
        """获取电费余额"""
        result = self.get_query()
        if result.get("code") == 200 and result.get("rows"):
            return result["rows"][0].get("balance", "0")
        return "0"

    def get_user_info(self):
        """获取用户基本信息"""
        result = self.get_query()
        if result.get("code") == 200 and result.get("rows"):
            info = result["rows"][0]
            return {
                "姓名": info.get("userName", "无"),
                "地址": info.get("address", "无"),
            }
        return {"姓名": "无", "地址": "无"}

    def print_result(self):
        result = self.get_query()
        print(self.parse_result(result))


if __name__ == "__main__":

    if not os.getenv("OPEN_ID"):
        # 创建.env文件
        with open(".env", "w") as f:
            f.write("OPEN_ID=")
        print("已创建.env文件，请在文件中填写openID")
        raise ValueError("没有获取到openID，请确保环境变量中存在OPEN_ID")

    query = ElectricityQuery(os.getenv("OPEN_ID"))
    query.print_result()
