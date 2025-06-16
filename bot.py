import logging
import json
import uuid
from datetime import datetime, timedelta
import os
import asyncio
from zoneinfo import ZoneInfo

from telegram import Update, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Bot

from telegram.error import Forbidden
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)

# --- 基本配置 ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 文件名常量 ---
USER_DATA_FILE = "user_data.json"
TOKEN_FILE = "token.txt"
DATA_SOURCE_FILE = "HaxDataCenter.txt" # 数据源文件

# --- 主机类型和续期周期 ---
HOST_TYPES = {
    "hax": {"name": "Hax主机", "days": 5},
    "woiden": {"name": "Woiden主机", "days": 3},
}

# --- Conversation Handler 状态定义 ---
ASK_REMARK, ASK_HOST_TYPE, ASK_CREATION_DATE = range(3)
DEL_AWAIT_NUMBER = range(3, 4)


# --- 数据持久化函数 ---
def load_user_data() -> dict:
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_user_data(data: dict) -> None:
    try:
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"保存用户数据失败: {e}")

user_data = load_user_data()


# --- 用户屏蔽处理 ---
def unblock_user(user_id: str):
    if user_data.get(user_id, {}).get("is_blocked"):
        user_data[user_id]["is_blocked"] = False
        save_user_data(user_data)
        logger.info(f"用户 {user_id} 已重新互动，移除屏蔽标记。")

def block_user(user_id: str):
    user_data.setdefault(user_id, {})["is_blocked"] = True
    save_user_data(user_data)
    logger.info(f"用户 {user_id} 已屏蔽机器人，标记为'blocked'。")


# --- Token 管理 ---
def save_token_to_file(token: str) -> None:
    try:
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(token)
        logger.info("Token 已成功保存到文件。")
    except Exception as e:
        logger.error(f"保存 Token 失败: {e}")

def get_bot_token() -> str | None:
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            token = f.read().strip()
        if token and ':' in token:
            logger.info("从文件加载Token。")
            return token

    while True:
        try:
            token_input = input("请输入您的Telegram机器人Token(格式：722xxxxxx:AAGvxxxxxx): ")
            if ':' in token_input:
                save_token_to_file(token_input)
                logger.info("新Token已保存。")
                return token_input
            else:
                 logger.error("Token格式不正确，请重试。")
        except KeyboardInterrupt:
            return None


# --- 辅助计算函数 ---
def calculate_expiration_time(machine_info: dict) -> datetime:
    tz = ZoneInfo("Asia/Bangkok")  # GMT+7
    event_date = datetime.strptime(machine_info["last_event_date"], "%Y-%m-%d")
    event_date = event_date.replace(tzinfo=tz)
    expire_date = event_date + timedelta(days=machine_info["renewal_days"])
    return expire_date.replace(hour=0, minute=0, second=0, microsecond=0)


def format_timedelta(delta: timedelta) -> str:
    if delta.total_seconds() < 0: return "已过期"
    return f"{delta.days}天{delta.seconds // 3600}小时"


# --- 数据中心监控 (从文件读取) ---
async def fetch_datacenter_stats() -> tuple[dict | None, int | None]:
    """
    [重写] 根据用户提供的最新格式，从本地 HaxDataCenter.txt 文件读取数据。
    """
    try:
        with open(DATA_SOURCE_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if not lines: return {}, 0

        stats, total_vps = {}, 0
        for line in lines:
            line = line.strip()
            if not line.startswith("✅ 数据中心:") or "VPS 数量:" not in line:
                continue
            
            if "Number of VPS Online" in line:
                continue

            try:
                name_part = line.split("✅ 数据中心:")[1].split(",")[0].strip()
                count_part = line.split("VPS 数量:")[1].strip().split(" ")[0]
                
                name = name_part.replace("./", "")
                count = int(count_part)
                
                stats[name] = count
                total_vps += count
            except (IndexError, ValueError):
                logger.warning(f"无法解析行: '{line}' in {DATA_SOURCE_FILE}。已跳过。")
                continue
        
        return stats, total_vps
    except FileNotFoundError:
        logger.warning(f"数据文件 '{DATA_SOURCE_FILE}' 未找到。")
        return None, None
    except Exception as e:
        logger.error(f"读取或解析 '{DATA_SOURCE_FILE}' 时出错: {e}")
        return None, None

async def monitor_command(update: Update | CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 根据是 message 还是 query 判断用户和回复方式
    if isinstance(update, CallbackQuery):
        user_id = str(update.from_user.id)
        reply_func = update.message.reply_text
    else:
        user_id = str(update.effective_user.id)
        reply_func = update.message.reply_text

    unblock_user(user_id)
    u_data = user_data.setdefault(user_id, {"machines": []})
    is_enabled = u_data.get("dc_monitor_enabled", False)

    text = (
        f"📊 **数据中心数量监控**\n\n"
        f"当前状态: **{'✅ 已开启' if is_enabled else '❌ 已关闭'}**\n"
        f"上次记录的总服务器数: **{u_data.get('last_dc_total_count', 'N/A')}**"
    )
    keyboard = [
        [InlineKeyboardButton(f"{'❌ 关闭' if is_enabled else '✅ 开启'}监控", callback_data="toggle_dc_monitor")],
        [InlineKeyboardButton("🔄 手动刷新", callback_data="dc_manual_refresh")]
    ]
    await reply_func(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def toggle_dc_monitor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    unblock_user(user_id)
    u_data = user_data.setdefault(user_id, {"machines": []})
    is_enabled = u_data.get("dc_monitor_enabled", False)
    u_data["dc_monitor_enabled"] = not is_enabled
    save_user_data(user_data)
    await monitor_command(query, context)

async def manual_refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("正在刷新，请稍候...")
    user_id = str(query.from_user.id)
    unblock_user(user_id)
    
    stats, total_count = await fetch_datacenter_stats()
    
    if total_count is not None:
        user_data[user_id]["last_dc_total_count"] = total_count
        save_user_data(user_data)
        details = "\n".join([f"- {name}: **{count}**" for name, count in stats.items()]) if stats else "未能解析出任何数据中心的详情。"
        message = f"🔄 **手动刷新成功**\n\n当前服务器总数: **{total_count}**\n\n**详情:**\n{details}"
        await query.message.reply_text(text=message, parse_mode='Markdown')
    else:
        await query.message.reply_text(f"❌ 刷新失败，请检查服务器上是否存在 `{DATA_SOURCE_FILE}` 文件。")


# --- 后台任务 ---
async def check_datacenters_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    users_to_check = [ (uid, u_data) for uid, u_data in user_data.items() if u_data.get("dc_monitor_enabled") and not u_data.get("is_blocked")]
    if not users_to_check: return

    stats, total_count = await fetch_datacenter_stats()
    if total_count is None: return

    changed = False
    for user_id, u_data in users_to_check:
        last_count = u_data.get("last_dc_total_count")
        if last_count is None or last_count != total_count:
            if last_count is not None:
                details = "\n".join([f"- {name}: **{count}**" for name, count in stats.items()]) if stats else "未能解析出任何数据中心的详情。"
                message = (f"🚨 **数据中心数量变化提醒** 🚨\n\n"
                           f"服务器总数从 **{last_count}** 变为 **{total_count}**！\n\n**详情:**\n{details}")
                try:
                    await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
                except Forbidden: block_user(user_id)
                except Exception as e: logger.error(f"发送监控通知给 {user_id} 失败: {e}")
            u_data["last_dc_total_count"] = total_count
            changed = True
    if changed: save_user_data(user_data)

from zoneinfo import ZoneInfo

async def check_expirations_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now(ZoneInfo("Asia/Bangkok"))  # 当前时间基于服务器所在时区 GMT+7
    changed = False

    for uid, u_data in user_data.items():
        if u_data.get("is_blocked"):
            continue

        for machine in u_data.get("machines", []):
            exp_dt = calculate_expiration_time(machine)
            time_left = exp_dt - now

            # 在两天内即将过期
            if timedelta(0) < time_left <= timedelta(days=2):
                last_sent = machine.get("last_hourly_reminder_sent")
                if last_sent is None or (now - datetime.fromisoformat(last_sent) >= timedelta(hours=1)):
                    exp_dt_beijing = exp_dt.astimezone(ZoneInfo("Asia/Shanghai"))

                    # 获取续期链接
                    host_type = machine.get("host_type")
                    if host_type == "hax":
                        renew_url = "https://hax.co.id/vps-renew/"
                    elif host_type == "woiden":
                        renew_url = "https://woiden.id/vps-renew/"
                    else:
                        renew_url = None

                    msg = (
                        f"⏳ 您的机器「{machine['remark']}」还剩 {format_timedelta(time_left)} 过期。\n"
                        f"📅 到期时间: {exp_dt_beijing:%Y-%m-%d %H:%M}（北京时间）"
                    )

                    if renew_url:
                        msg += f"\n🔗 续期地址: [点击前往]({renew_url})"

                    btns = [[InlineKeyboardButton("✅ 我已续期", callback_data=f"renew_{machine['uuid']}")]]

                    try:
                        await context.bot.send_message(
                            int(uid),
                            msg,
                            reply_markup=InlineKeyboardMarkup(btns),
                            parse_mode='Markdown'
                        )
                        machine["last_hourly_reminder_sent"] = now.isoformat()
                        changed = True
                    except Forbidden:
                        block_user(uid)
                        break
                    except Exception as e:
                        logger.error(f"发送续期提醒给 {uid} 失败: {e}")

    if changed:
        save_user_data(user_data)



# --- 命令处理函数 ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    unblock_user(user_id)
    await update.message.reply_text(
        "欢迎使用续期提醒与监控机器人!\n"
        "使用 /new 添加新机器。\n"
        "使用 /info 查看机器列表。\n"
        "使用 /delmachine 删除机器。\n"
        "使用 /monitor 设置数据中心监控。\n"
        "使用 /cancel 取消当前操作。")

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    unblock_user(user_id)

    if not user_data.get(user_id, {}).get("machines"):
        await update.message.reply_text("您还没有机器。使用 /new 添加。")
        return

    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    lines = ["🗂️ 您的机器列表：\n"]

    for i, m in enumerate(user_data[user_id]["machines"]):
        exp_dt = calculate_expiration_time(m)
        time_left = exp_dt - now
        lines.append(
            f"{i+1}. 🖥️ 机器名称: 「{m['remark']}」\n"
            f"   ⏳ 剩余时间: {format_timedelta(time_left)}\n"
            f"   📅 到期时间: {exp_dt:%Y-%m-%d %H:%M}（GMT+7）\n"
        )

    await update.message.reply_text("\n".join(lines))



async def new_machine_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    unblock_user(user_id)
    user_data.setdefault(user_id, {"machines": []})
    await update.message.reply_text("请输入这台机器的备注:")
    return ASK_REMARK

async def received_remark(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['remark'] = update.message.text
    buttons = [[InlineKeyboardButton(H["name"], callback_data=ht)] for ht, H in HOST_TYPES.items()]
    await update.message.reply_text("请选择主机类型:", reply_markup=InlineKeyboardMarkup(buttons))
    return ASK_HOST_TYPE

async def received_host_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['host_type'] = query.data
    await query.edit_message_text(f"已选: {HOST_TYPES[query.data]['name']}\n请输入创建日期(MM-DD):")
    return ASK_CREATION_DATE

async def received_creation_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        month, day = map(int, update.message.text.split('-'))
        creation_date = datetime(datetime.now().year, month, day)
    except ValueError:
        await update.message.reply_text("日期格式错误，请重新输入 MM-DD 或 /cancel。"); return ASK_CREATION_DATE
    user_id = str(update.effective_user.id)
    host_type = context.user_data['host_type']
    new_machine = { "uuid": str(uuid.uuid4()), "remark": context.user_data['remark'],
                    "host_type": host_type, "renewal_days": HOST_TYPES[host_type]["days"],
                    "last_event_date": creation_date.strftime("%Y-%m-%d"), "last_hourly_reminder_sent": None }
    user_data[user_id]["machines"].append(new_machine)
    save_user_data(user_data)
    exp_dt = calculate_expiration_time(new_machine)
    await update.message.reply_text(f"✅ 机器「{new_machine['remark']}」添加成功！\n首次过期: {exp_dt:%Y-%m-%d %H:%M} \n到期时间(GMT+7)： {exp_dt:%Y-%m-%d %H:%M}\n\n您可以使用 /info 查看机器列表，或 /delmachine 删除机器。")
    context.user_data.clear()
    return ConversationHandler.END

async def delete_machine_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    unblock_user(user_id)
    machines = user_data.get(user_id, {}).get("machines", [])
    if not machines:
        await update.message.reply_text("您没有可删除的机器。"); return ConversationHandler.END
    lines = ["请选择要删除的机器序号：\n"] + [f"{i+1}. 「{m['remark']}」" for i, m in enumerate(machines)]
    await update.message.reply_text("\n".join(lines) + "\n\n请输入序号，或 /cancel 取消。")
    return DEL_AWAIT_NUMBER

async def received_delete_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    try:
        idx = int(update.message.text) - 1
        if 0 <= idx < len(user_data[user_id]["machines"]):
            deleted_m = user_data[user_id]["machines"].pop(idx)
            save_user_data(user_data)
            await update.message.reply_text(f"🗑️ 机器「{deleted_m['remark']}」已删除。")
            return ConversationHandler.END
        else: raise ValueError
    except (ValueError, IndexError):
        await update.message.reply_text("无效序号。请重新输入或 /cancel。"); return DEL_AWAIT_NUMBER

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("操作已取消。")
    return ConversationHandler.END

async def renew_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    unblock_user(user_id)
    _, machine_uuid = query.data.split("_", 1)

    for machine in user_data.get(user_id, {}).get("machines", []):
        if machine["uuid"] == machine_uuid:
            # 更新续期日期为当前时间（GMT+7）
            now = datetime.now(ZoneInfo("Asia/Bangkok"))
            machine["last_event_date"] = now.strftime("%Y-%m-%d")
            machine["last_hourly_reminder_sent"] = None
            save_user_data(user_data)

            # 计算新的过期时间（GMT+7）→ 转为北京时间展示
            exp_dt = calculate_expiration_time(machine)
            exp_dt_beijing = exp_dt.astimezone(ZoneInfo("Asia/Shanghai"))
            time_left = exp_dt - now

            msg = (
                f"✅ 机器「{machine['remark']}」已续期！\n\n"
                f"📅 新过期时间: {exp_dt_beijing:%Y-%m-%d %H:%M}（北京时间）\n"
                f"🕓 剩余时间: {format_timedelta(time_left)}"
            )
            await query.edit_message_text(msg)
            return

    await query.edit_message_text("❌ 未找到对应机器。")


# --- 主函数 (最终稳定版) ---
def main() -> None:
    """主函数，完全同步构建，最后启动，避免所有事件循环冲突。"""
    bot_token = get_bot_token()
    if not bot_token:
        logger.critical("未能获取Token，程序退出。"); return

    application = Application.builder().token(bot_token).build()

    # 注册所有处理器
    conv_new = ConversationHandler(
        entry_points=[CommandHandler("new", new_machine_command)],
        states={
            ASK_REMARK: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_remark)],
            ASK_HOST_TYPE: [CallbackQueryHandler(received_host_type)],
            ASK_CREATION_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_creation_date)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)])
    conv_del = ConversationHandler(
        entry_points=[CommandHandler("delmachine", delete_machine_command)],
        states={DEL_AWAIT_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_delete_number)]},
        fallbacks=[CommandHandler("cancel", cancel_conversation)])

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("monitor", monitor_command))
    application.add_handler(conv_new)
    application.add_handler(conv_del)
    application.add_handler(CallbackQueryHandler(renew_button_callback, pattern="^renew_.*"))
    application.add_handler(CallbackQueryHandler(toggle_dc_monitor_callback, pattern="^toggle_dc_monitor$"))
    application.add_handler(CallbackQueryHandler(manual_refresh_callback, pattern="^dc_manual_refresh$"))


    # 注册后台任务
    jq = application.job_queue
    jq.run_repeating(check_expirations_job, interval=60, first=10)
    jq.run_repeating(check_datacenters_job, interval=60, first=15)

    # 启动机器人！
    logger.info("机器人启动中，开始轮询... (按 Ctrl+C 停止)")
    application.run_polling(drop_pending_updates=True)


async def cleanup(application):
    logger.info("开始关闭程序...")
    if application.updater and application.updater.is_running:
        await application.updater.stop()
    if hasattr(application, 'running') and application.running:
        await application.stop()
    if hasattr(application, 'shutdown'):
        await application.shutdown()
    logger.info("机器人已关闭。")

# 主程序入口
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被用户中断 (Ctrl+C)。")
    except Exception as e:
        logger.critical(f"程序顶层致命错误: {e}", exc_info=True)
