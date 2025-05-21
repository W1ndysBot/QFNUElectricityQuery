"""
低余额提醒
当余额低于30元时，发送提醒
"""

import logging
import os
import sys
import asyncio
from datetime import datetime, timedelta

# 添加项目根目录到sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.scripts.QFNUElectricityQuery.DataManager import DataManager
from app.scripts.QFNUElectricityQuery.ElectricityQuery import ElectricityQuery
from app.api import send_group_msg


class BalanceAlertManager:
    def __init__(self):
        # 阈值
        self.threshold = 30
        # 提醒间隔（小时）
        self.alert_interval = 24
        # 记录上次提醒时间 {group_id: {user_id: timestamp}}
        self.last_alert_time = {}
        self.electricity_query = ElectricityQuery()

        # 定义数据目录，与DataManager保持一致
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.DATA_DIR = os.path.join(base_dir, "data", "QFNUElectricityQuery")
        os.makedirs(self.DATA_DIR, exist_ok=True)

        # 从本地文件恢复各群组的提醒时间记录
        self._load_alert_times_from_disk()

    def _load_alert_times_from_disk(self):
        """从磁盘加载所有群组的提醒时间记录"""
        try:
            if not os.path.exists(self.DATA_DIR):
                return

            # 遍历数据目录下的所有群组数据文件
            for filename in os.listdir(self.DATA_DIR):
                if filename.endswith(".json"):
                    group_id = filename.split(".")[0]

                    # 加载该群组的提醒时间记录
                    data_manager = DataManager(group_id)
                    last_alert_times = data_manager.load_last_alert_time()
                    if last_alert_times:
                        self.last_alert_time[group_id] = last_alert_times
        except Exception as e:
            logging.error(f"加载提醒时间记录时出错: {e}")

    def _save_alert_time(self, group_id):
        """保存指定群组的提醒时间记录到磁盘"""
        try:
            if group_id in self.last_alert_time:
                data_manager = DataManager(group_id)
                data_manager.save_last_alert_time(self.last_alert_time[group_id])
        except Exception as e:
            logging.error(f"保存群组 {group_id} 的提醒时间记录时出错: {e}")

    def should_alert(self, group_id, user_id):
        """检查是否应该发送提醒（避免频繁提醒）"""
        now = datetime.now()
        if group_id not in self.last_alert_time:
            self.last_alert_time[group_id] = {}

        last_time = self.last_alert_time[group_id].get(user_id)
        if not last_time or now - last_time > timedelta(hours=self.alert_interval):
            self.last_alert_time[group_id][user_id] = now
            # 保存提醒时间到本地
            self._save_alert_time(group_id)
            return True
        return False

    async def check_balance_for_user(self, group_id, user_id, openid):
        """检查单个用户的电费余额"""
        try:
            result = await self.electricity_query.parse_result(openid)
            if result and "data" in result:
                balance = float(result["data"]["yue"])
                if balance < self.threshold and self.should_alert(group_id, user_id):
                    return user_id, balance
            return None, 0
        except Exception as e:
            logging.error(f"检查用户 {user_id} 余额时出错: {e}")
            return None, 0

    async def check_and_alert(self, websocket):
        """检查所有用户余额并发送提醒"""
        try:
            # 确保数据目录存在
            if not os.path.exists(self.DATA_DIR):
                return

            # 遍历数据目录下的所有群组数据文件
            for filename in os.listdir(self.DATA_DIR):
                if filename.endswith(".json"):
                    group_id = filename.split(".")[0]

                    # 获取该群组的所有绑定用户
                    data_manager = DataManager(group_id)
                    bindings = data_manager.get_all_bindings()

                    # 检查每个用户的电费余额
                    for user_id, openid in bindings.items():
                        alert_user_id, balance = await self.check_balance_for_user(
                            group_id, user_id, openid
                        )

                        # 如果需要提醒，发送消息
                        if alert_user_id:
                            alert_msg = (
                                f"[CQ:at,qq={user_id}] 电费余额提醒！\n"
                                f"您的电费余额仅剩 {balance:.2f} 元，已低于 {self.threshold} 元，"
                                f"请及时充值以避免断电！"
                            )
                            await send_group_msg(websocket, group_id, alert_msg)
                            logging.info(
                                f"已向群 {group_id} 的用户 {user_id} 发送电费余额提醒"
                            )

                            # 避免一次性发送太多消息导致风控
                            await asyncio.sleep(1)

        except Exception as e:
            logging.error(f"检查电费余额并发送提醒时出错: {e}")
