"""
低余额提醒
当余额低于30元时，发送提醒
"""

import logging


class BalanceAlertManager:
    def __init__(self, balance):
        # 阈值
        self.threshold = 30
        self.balance = balance

    def check_balance(self):
        if self.balance < self.threshold:
            logging.info(f"余额低于{self.threshold}元，发送提醒")
            return True
        return False
