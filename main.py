# script/QFNUElectricityQuery/main.py

import logging
import os
import sys
import re

from urllib.parse import urlparse, parse_qs

# 添加项目根目录到sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.config import *
from app.api import send_group_msg, send_private_msg, delete_msg
from app.switch import load_switch, save_switch
from app.scripts.QFNUElectricityQuery.DataManager import DataManager
from app.scripts.QFNUElectricityQuery.ElectricityQuery import ElectricityQuery

query_message_id = []


# 查看功能开关状态
def load_function_status(group_id):
    return load_switch(group_id, "QFNUElectricityQuery")


# 保存功能开关状态
def save_function_status(group_id, status):
    save_switch(group_id, "QFNUElectricityQuery", status)


# 处理开关状态
async def toggle_function_status(websocket, group_id, message_id, authorized):
    if not authorized:
        await send_group_msg(
            websocket,
            group_id,
            f"[CQ:reply,id={message_id}]❌❌❌你没有权限对QFNUElectricityQuery功能进行操作,请联系管理员。",
        )
        return

    if load_function_status(group_id):
        save_function_status(group_id, False)
        await send_group_msg(
            websocket,
            group_id,
            f"[CQ:reply,id={message_id}]🚫🚫🚫QFNUElectricityQuery功能已关闭",
        )
    else:
        save_function_status(group_id, True)
        await send_group_msg(
            websocket,
            group_id,
            f"[CQ:reply,id={message_id}]✅✅✅QFNUElectricityQuery功能已开启",
        )


# 新增：发送帮助菜单
async def send_help_menu(websocket, group_id, message_id):
    """发送功能帮助菜单"""
    menu_text = (
        "--- QFNU 电费查询助手 ---\n"
        "qfnueq - 开启/关闭本群电费查询功能 (管理员权限)\n"
        "qfnueqmenu - 显示此帮助菜单\n"
        "电费绑定 <链接> - 绑定你的微信openID链接\n"
        "查询 / 查电费 - 查询已绑定账号的电费余额\n"
        "电费解绑 - 解除当前账号的绑定\n"
        "微信openID链接获取方法：1.搜索微信公众号“Qsd学生公寓” 2.点击下方菜单栏 3.进入页面之后 4.点击右上角，点击复制链接\n"
        "--------------------------"
    )
    await send_group_msg(websocket, group_id, f"[CQ:reply,id={message_id}]{menu_text}")


# 提取 openID 的函数
def extract_openid(link):
    """从链接中提取openID"""
    try:
        parsed_url = urlparse(link)
        # 尝试从查询参数中获取
        query_params = parse_qs(parsed_url.query)
        if "openId" in query_params:
            return query_params["openId"][0]
        # 尝试从片段标识符中获取（虽然示例中片段标识符也有，但优先用查询参数）
        fragment_params = parse_qs(parsed_url.fragment)
        if "openId" in fragment_params:
            return fragment_params["openId"][0]
        # 增加正则表达式匹配，作为备用方案
        match = re.search(r"openId=([^&/#?]+)", link)
        if match:
            return match.group(1)
    except Exception as e:
        logging.error(f"Error extracting openID from link {link}: {e}")
    return None


# 群消息处理函数
async def handle_group_message(websocket, msg):
    """处理群消息"""
    try:
        user_id = str(msg.get("user_id"))
        group_id = str(msg.get("group_id"))
        raw_message = str(msg.get("raw_message")).strip()  # 去除首尾空白
        message_id = str(msg.get("message_id"))
        authorized = user_id in owner_id

        # 新增：处理菜单命令 (优先处理，不受开关影响)
        if raw_message.lower() == "qfnueqmenu":
            await send_help_menu(websocket, group_id, message_id)
            return  # 处理完菜单命令后直接返回

        # 处理开关命令
        if raw_message.lower() == "qfnueq":
            await toggle_function_status(websocket, group_id, message_id, authorized)
            return

        # 检查功能是否开启
        if not load_function_status(group_id):
            # 如果功能未开启，且不是开关命令，则不处理
            if raw_message.lower() != "qfnueq":
                return
            # 如果是开关命令，则由上面的逻辑处理

        # --- 功能开启后的逻辑 ---
        data_manager = DataManager(group_id)
        electricity_query = ElectricityQuery()  # 不再需要传入 openID

        # 绑定命令: 电费绑定 <链接>
        bind_match = re.match(
            r"^(?:电费绑定)\s+(https?://\S+)$", raw_message, re.IGNORECASE
        )
        if bind_match:
            link = bind_match.group(1)
            openid = extract_openid(link)
            if openid:
                if data_manager.bind_openid(user_id, openid):
                    await send_group_msg(
                        websocket,
                        group_id,
                        f"[CQ:reply,id={message_id}]✅ 绑定成功！",
                    )
                else:
                    await send_group_msg(
                        websocket,
                        group_id,
                        f"[CQ:reply,id={message_id}]❌ 绑定失败，请稍后再试。",
                    )
            else:
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]❌ 无法从链接中提取openID，请检查链接格式。",
                )
            return

        # 查询命令: 查询 / 查电费
        if raw_message in ["查询", "查电费", "query"]:  # 支持更多命令
            openid = data_manager.get_openid(user_id)
            if not openid:
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]🤔 你还没有绑定openID，请使用【电费绑定 <链接>】命令进行绑定。",
                )
                return

            # 发送正在查询提示
            await send_group_msg(
                websocket, group_id, f"[CQ:reply,id={message_id}]🔍 正在查询电费信息..."
            )

            # 异步执行查询
            result = await electricity_query.parse_result(openid)
            reply_message = f"[CQ:reply,id={message_id}]{result.get('message', '查询时发生未知错误。')}"

            await send_group_msg(websocket, group_id, reply_message)
            # 如果全局变量query_message_id不为空，则执行撤回函数并清空全局变量
            global query_message_id
            if query_message_id:
                for message_id in query_message_id:
                    await delete_msg(websocket, message_id)
                query_message_id = []
            return

        # 解绑命令: 电费解绑
        if raw_message in ["电费解绑"]:
            if data_manager.unbind_openid(user_id):
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]✅ 解绑成功！",
                )
            else:
                # 可能用户本来就没绑定
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]🤔 你尚未绑定openID，无需解绑。",
                )
            return

        # 其他群消息处理逻辑 (如果需要的话)
        # pass

    except Exception as e:
        logging.error(f"处理QFNUElectricityQuery群消息失败: {e}")
        # 避免在异常处理中再次访问可能不存在的 group_id
        group_id_for_error = msg.get("group_id", "未知群组")
        await send_group_msg(
            websocket,
            group_id_for_error,
            f"处理QFNUElectricityQuery群消息时发生内部错误: {e}",
        )
        return


# 回应事件处理函数
async def handle_response(websocket, msg):
    """处理回调事件"""
    try:
        echo = msg.get("echo")
        if echo and "正在查询电费信息" in echo:
            # 存储消息id到全局变量
            global query_message_id
            query_message_id.append(msg.get("data").get("message_id"))
    except Exception as e:
        logging.error(f"处理QFNUElectricityQuery回调事件失败: {e}")
        return


# 请求事件处理函数
async def handle_request_event(websocket, msg):
    """处理请求事件"""
    try:
        request_type = msg.get("request_type")
        pass
    except Exception as e:
        logging.error(f"处理QFNUElectricityQuery请求事件失败: {e}")
        return


# 统一事件处理入口
async def handle_events(websocket, msg):
    """统一事件处理入口"""
    post_type = msg.get("post_type", "response")  # 添加默认值
    try:
        # 这里可以放一些定时任务，在函数内设置时间差检测即可

        # 处理回调事件，用于一些需要获取ws返回内容的事件
        if msg.get("status") == "ok":
            await handle_response(websocket, msg)
            return

        # 处理元事件，每次心跳时触发，用于一些定时任务
        if post_type == "meta_event":
            pass

        # 处理消息事件，用于处理群消息和私聊消息
        elif post_type == "message":
            message_type = msg.get("message_type")
            if message_type == "group":
                await handle_group_message(websocket, msg)
            elif message_type == "private":
                pass

        # 处理通知事件，用于处理群通知
        elif post_type == "notice":
            # await handle_group_notice(websocket, msg)
            pass

        # 处理请求事件，用于处理请求事件
        elif post_type == "request":
            await handle_request_event(websocket, msg)

    except Exception as e:
        error_type = {
            "message": "消息",
            "notice": "通知",
            "request": "请求",
            "meta_event": "元事件",
            "response": "回调",
        }.get(post_type, "未知")

        logging.error(f"处理QFNUElectricityQuery {error_type}事件失败: {e}")

        # 发送错误提示 (仅对消息事件发送)
        if post_type == "message":
            message_type = msg.get("message_type")
            if message_type == "group":
                group_id_for_error = msg.get("group_id", "未知群组")
                await send_group_msg(
                    websocket,
                    group_id_for_error,
                    f"处理QFNUElectricityQuery {error_type}事件时发生内部错误，请联系管理员。",
                )
            elif message_type == "private":
                user_id_for_error = msg.get("user_id", "未知用户")
                await send_private_msg(
                    websocket,
                    user_id_for_error,
                    f"处理QFNUElectricityQuery {error_type}事件时发生内部错误，请联系管理员。",
                )
