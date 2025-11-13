from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig

from buff163_unofficial_api import Buff163API
from buff163_unofficial_api.models import Item, SpecificItem
from buff163_unofficial_api.cs_enums import *
from typing import List, Union
from enum import Enum


class CustomBuff163API(Buff163API):
    """
    继承官方 API 类，并重写部分方法以支持中文。
    """
    def get_featured_market(self, pageNum: int = 1) -> List[Item]:
        """重写方法，在请求中加入 lang=zh-CN 参数"""
        ep_params = {
            "game": "csgo",
            "lang": "zh-CN",
            "page_num": str(pageNum)
        }
        result = self._rest_adapter.get(
            endpoint="/market/goods", ep_params=ep_params
        )
        market = [Item(**item) for item in result.data["data"]["items"]]
        return market

    def get_item_market(
        self,
        category: Union[Knife, Gun, Glove, Agent, Sticker, OtherItem],
        pageNum: int = 1,
    ) -> List[Item]:
        """重写方法，在请求中加入 lang=zh-CN 参数"""
        if not isinstance(category, Enum):
            raise TypeError("Category must be an instance of an Enum.")
        
        ep_params = {
            "game": "csgo",
            "lang": "zh-CN",
            "page_num": str(pageNum),
            "category": category.value
        }
        result = self._rest_adapter.get(
            endpoint="/market/goods", ep_params=ep_params
        )

        market = [Item(**item) for item in result.data["data"]["items"]]
        return market

    def get_item(self, item_id: int) -> SpecificItem:
        """重写方法，在请求中加入 lang=zh-CN 参数"""
        ep_params = {
            "game": "csgo",
            "lang": "zh-CN",
            "goods_id": str(item_id)
        }
        result = self._rest_adapter.get(
            endpoint="/market/goods/info", ep_params=ep_params
        )

        return SpecificItem(**result.data["data"])


@register("buff163", "Cline", "一个简单的 Buff163 查询插件", "1.0.1")
class Buff163Plugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.buff_api = None
        session_cookie = self.config.get("session_cookie")
        if session_cookie:
            # 使用我们自定义的 API 类
            self.buff_api = CustomBuff163API(session_cookie=session_cookie)
        else:
            logger.warning("Buff163插件未配置 session_cookie，部分功能可能无法使用")

    @filter.command("查价格")
    async def search_price(self, event: AstrMessageEvent, item_name: str):
        """
        查询指定饰品的价格
        """
        if not self.buff_api:
            yield event.plain_result("插件未配置 session_cookie，无法查询。")
            return

        if not item_name:
            yield event.plain_result("请输入要查询的饰品名称，例如：/查价格 AK-47 | 红线 (久经沙场)")
            return

        try:
            yield event.plain_result(f"正在搜索包含 '{item_name}' 的饰品，请稍候...")
            
            # 使用 get_featured_market 作为数据源进行搜索
            market_items = self.buff_api.get_featured_market()
            
            found_items = []
            for item in market_items:
                if item_name.lower() in item.market_hash_name.lower():
                    found_items.append(item)

            if not found_items:
                yield event.plain_result(f"未在推荐市场中找到与 '{item_name}' 相关的饰品。")
                return

            # 格式化并返回结果
            response = f"找到以下与 '{item_name}' 相关的饰品：\n"
            response += "--------------------\n"
            for item in found_items[:5]: # 最多显示5个结果
                response += f"名称: {item.market_hash_name}\n"
                response += f"价格: ¥ {item.sell_min_price}\n"
                response += "--------------------\n"
            
            yield event.plain_result(response)

        except Exception as e:
            logger.error(f"查询 Buff163 饰品价格失败: {e}")
            yield event.plain_result(f"查询失败，可能是网络问题或API配置错误。")
