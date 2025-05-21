"""
数据管理模块
"""

import os
import json
import logging
from datetime import datetime


class DataManager:
    def __init__(self, group_id):
        self.group_id = str(group_id)  # 确保group_id是字符串
        self.DATA_DIR = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "data",
            "QFNUElectricityQuery",
        )
        # 确保数据目录存在
        os.makedirs(self.DATA_DIR, exist_ok=True)
        self.GROUP_DATA_PATH = os.path.join(self.DATA_DIR, f"{self.group_id}.json")

    def _load_group_data(self):
        """加载群组数据文件，如果文件不存在或为空则返回空字典"""
        try:
            if os.path.exists(self.GROUP_DATA_PATH):
                with open(self.GROUP_DATA_PATH, "r", encoding="utf-8") as f:
                    content = f.read()
                    if not content:
                        return {}
                    return json.loads(content)
            else:
                return {}
        except json.JSONDecodeError:
            logging.error(f"Failed to decode JSON from {self.GROUP_DATA_PATH}")
            return {}  # 或者可以抛出异常，取决于错误处理策略
        except Exception as e:
            logging.error(f"Error loading group data {self.GROUP_DATA_PATH}: {e}")
            return {}  # 或者抛出异常

    def _save_group_data(self, data):
        """保存群组数据到文件"""
        try:
            with open(self.GROUP_DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"Error saving group data {self.GROUP_DATA_PATH}: {e}")

    def bind_openid(self, user_id, openid):
        """绑定用户ID和openID"""
        user_id = str(user_id)  # 确保证user_id是字符串
        data = self._load_group_data()
        if "bindings" not in data:
            data["bindings"] = {}
        data["bindings"][user_id] = openid
        self._save_group_data(data)
        return True

    def get_openid(self, user_id):
        """根据用户ID获取openID"""
        user_id = str(user_id)  # 确保证user_id是字符串
        data = self._load_group_data()
        return data.get("bindings", {}).get(user_id)

    def unbind_openid(self, user_id):
        """解除用户ID的openID绑定"""
        user_id = str(user_id)  # 确保证user_id是字符串
        data = self._load_group_data()
        if "bindings" in data and user_id in data["bindings"]:
            del data["bindings"][user_id]
            self._save_group_data(data)
            return True
        return False

    def get_all_bindings(self):
        """获取所有用户的绑定关系"""
        try:
            if os.path.exists(self.GROUP_DATA_PATH):
                with open(self.GROUP_DATA_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("bindings", {})
            return {}
        except Exception as e:
            logging.error(f"获取绑定关系时出错: {e}")
            return {}

    def save_last_alert_time(self, last_alert_time_dict):
        """保存上次提醒时间到本地文件

        Args:
            last_alert_time_dict: {user_id: datetime}
        """
        data = self._load_group_data()
        if "last_alert_time" not in data:
            data["last_alert_time"] = {}

        # 将datetime对象转为ISO格式字符串后保存
        serialized_dict = {}
        for user_id, timestamp in last_alert_time_dict.items():
            if isinstance(timestamp, datetime):
                serialized_dict[user_id] = timestamp.isoformat()
            else:
                serialized_dict[user_id] = timestamp

        data["last_alert_time"] = serialized_dict
        self._save_group_data(data)
        return True

    def load_last_alert_time(self):
        """从本地文件加载上次提醒时间

        Returns:
            dict: {user_id: datetime}
        """
        data = self._load_group_data()
        last_alert_time_dict = data.get("last_alert_time", {})

        # 将字符串转回datetime对象
        result = {}
        for user_id, timestamp_str in last_alert_time_dict.items():
            try:
                result[user_id] = datetime.fromisoformat(timestamp_str)
            except (TypeError, ValueError):
                # 如果转换失败，则跳过该记录
                logging.warning(f"无法解析时间戳: {timestamp_str}")

        return result
