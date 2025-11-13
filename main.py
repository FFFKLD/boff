from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig

from buff163_unofficial_api import Buff163API
from buff163_unofficial_api.rest_adapter import RestAdapter, Result
from typing import Dict
import requests


class CustomRestAdapter(RestAdapter):
    def _do(
        self, http_method: str, endpoint: str, ep_params: Dict = None, data: Dict = None
    ) -> Result:
        """重写 _do 方法以添加 Accept-Language 请求头"""
        full_url = self.url + endpoint
        headers = {
            "Cookie": self._session_cookie,
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        log_line_pre = f"method={http_method}, url={full_url}, params={ep_params}"
        self._logger.debug(msg=log_line_pre)

        # 直接调用父类的 _do 方法逻辑，但使用我们自己的 headers
        # 为了避免重复代码，这里我们直接复制并修改父类方法的核心逻辑
        try:
            response = requests.request(
                method=http_method,
                url=full_url,
                verify=self._ssl_verify,
                headers=headers,
                params=ep_params,
                json=data,
            )
        except Exception as e:
            self._logger.error(msg=f"Request failed: {e}")
            raise

        try:
            data_out = response.json()
        except ValueError as e:
            self._logger.error(msg=f"Bad JSON in response: {e}")
            raise

        if data_out.get("code") != "OK":
            self._logger.error(msg=f"Error response code: {data_out.get('code')}")
            raise Exception(f"Error from API: {data_out.get('error', 'Unknown error')}")

        return Result(response.status_code, message=response.reason, data=data_out)


@register("buff163", "Cline", "一个简单的 Buff163 查询插件", "1.0.0")
class Buff163Plugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.buff_api = None
        session_cookie = self.config.get("session_cookie")
        if session_cookie:
            # 创建官方 API 实例
            self.buff_api = Buff163API(session_cookie=session_cookie)
            # 创建我们自定义的 adapter
            custom_adapter = CustomRestAdapter(session_cookie=session_cookie)
            # 通过 Monkey Patching 替换掉原来的 adapter
            self.buff_api._rest_adapter = custom_adapter
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
