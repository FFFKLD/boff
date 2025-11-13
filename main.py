import requests
import urllib.parse
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig

@register("buff163", "Cline", "一个通过网页抓取查询 Buff163 价格的插件", "2.0.0")
class Buff163Plugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.session_cookie = self.config.get("session_cookie")
        if not self.session_cookie:
            logger.warning("Buff163插件未配置 session_cookie，无法查询。")

    @filter.command("查价格")
    async def search_price(self, event: AstrMessageEvent, item_name: str):
        """
        通过抓取网页查询指定饰品的价格
        """
        if not self.session_cookie:
            yield event.plain_result("插件未配置 session_cookie，无法查询。")
            return

        if not item_name:
            yield event.plain_result("请输入要查询的饰品名称，例如：/查价格 AK-47 | 红线 (久经沙场)")
            return

        try:
            yield event.plain_result(f"正在网页上搜索 '{item_name}'，请稍候...")
            
            encoded_item_name = urllib.parse.quote(item_name)
            search_url = f"https://buff.163.com/market/goods?search={encoded_item_name}"
            
            headers = {
                "Cookie": self.session_cookie,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.get(search_url, headers=headers)
            response.raise_for_status()  # 如果请求失败则抛出异常
            
            html_content = response.text

            # --- 开始简易 HTML 解析 ---
            # 这是一个非常脆弱的解析方式，如果 buff.163.com 网站结构改变，这里可能就会失效
            
            # 1. 查找第一个商品项
            item_card_start = html_content.find('<li class="card"')
            if item_card_start == -1:
                yield event.plain_result(f"未在 Buff163 网站上找到与 '{item_name}' 相关的饰品。")
                return

            # 2. 在商品项中查找名称
            name_tag_start = html_content.find('<h3 class="c_Gray">', item_card_start)
            if name_tag_start == -1:
                raise ValueError("无法解析商品名称")
            name_start = name_tag_start + len('<h3 class="c_Gray">')
            name_end = html_content.find('</h3>', name_start)
            found_name = html_content[name_start:name_end].strip()

            # 3. 在商品项中查找价格
            price_tag_start = html_content.find('<strong class="f_Strong">', item_card_start)
            if price_tag_start == -1:
                raise ValueError("无法解析商品价格")
            price_start = html_content.find('¥ ', price_tag_start) + 2
            price_end = html_content.find('</strong>', price_start)
            found_price = html_content[price_start:price_end].strip()

            # 格式化并返回结果
            response_text = (
                f"找到最匹配的饰品：\n"
                f"--------------------\n"
                f"名称: {found_name}\n"
                f"价格: ¥ {found_price}\n"
                f"--------------------"
            )
            
            yield event.plain_result(response_text)

        except requests.exceptions.RequestException as e:
            logger.error(f"访问 Buff163 网站失败: {e}")
            yield event.plain_result(f"查询失败，访问 Buff163 网站时遇到网络问题。")
        except Exception as e:
            logger.error(f"解析 Buff163 网页或处理时出错: {e}")
            yield event.plain_result(f"查询失败，处理数据时发生内部错误。")
