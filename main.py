from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig

# 我们将再次使用我们创建的、基于官方 API 的新库
# 这个库需要用户手动安装
from buff_api_cn import BuffApiCn
from buff_api_cn.models import Item


@register("buff163", "Cline", "一个通过 API 查询 Buff163 价格的插件", "2.1.0")
class Buff163Plugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.buff_api = None
        session_cookie = self.config.get("session_cookie")
        if session_cookie:
            try:
                # 使用我们自定义的、支持中文的 API 类
                self.buff_api = BuffApiCn(session_cookie=session_cookie)
            except ImportError:
                logger.error("未能导入 buff_api_cn 库。请确保您已按照 requirements.txt 中的说明进行安装。")
                self.buff_api = None
        else:
            logger.warning("Buff163插件未配置 session_cookie，部分功能可能无法使用")

    @filter.command("查价格")
    async def search_price(self, event: AstrMessageEvent, item_name: str):
        """
        通过 API 查询指定饰品的价格
        """
        if not self.buff_api:
            yield event.plain_result("插件初始化失败或未配置 session_cookie，无法查询。")
            return

        if not item_name:
            yield event.plain_result("请输入要查询的饰品名称，例如：/查价格 AK-47 | 红线 (久经沙场)")
            return

        try:
            yield event.plain_result(f"正在通过 API 搜索 '{item_name}' 的饰品，请稍候...")
            
            # 使用新的 search_item 方法进行搜索
            found_items = self.buff_api.search_item(text=item_name)

            if not found_items:
                yield event.plain_result(f"未找到与 '{item_name}' 相关的饰品。")
                return

            # 格式化并返回结果
            response = f"找到以下与 '{item_name}' 相关的饰品：\n"
            response += "--------------------\n"
            for item in found_items[:5]: # 最多显示5个结果
                response += f"名称: {item.name}\n" # 注意：search_item 返回的可能是简化的 Item 模型
                response += f"价格: ¥ {item.sell_min_price}\n"
                response += "--------------------\n"
            
            yield event.plain_result(response)

        except Exception as e:
            logger.error(f"查询 Buff163 饰品价格失败: {e}")
            yield event.plain_result(f"查询失败，可能是网络问题或API配置错误。")
