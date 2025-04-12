import asyncio
import threading
from browser_use.controller.service import Controller
from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig
from langchain_openai import ChatOpenAI
from browser_use.agent.views import ActionResult
from models import WebpageInfo, ProductInfo

class ShoppingThread(threading.Thread):
    def __init__(self, products, link, aeon_id, pass_word, callback, error_callback):
        threading.Thread.__init__(self)
        self.products = products
        self.link = link
        self.aeon_id = aeon_id
        self.pass_word = pass_word
        self.browser = None
        self.agent = None
        self.controller = Controller()
        self.callback = callback
        self.error_callback = error_callback
        self.daemon = True
        self.running = True
        self.setup_controller()

    def setup_controller(self):
        # コントローラーのアクションを設定
        @self.controller.action('Go to the webpage', param_model=WebpageInfo)
        def go_to_webpage(webpage_info: WebpageInfo):
            self.log(f"ウェブページ {webpage_info.link} へアクセスしています...")
            return ActionResult(
                extracted_content=f"ウェブページ {webpage_info.link} へアクセスします。",
                include_in_memory=True
            )

        @self.controller.action('Search for a product', param_model=ProductInfo)
        def search_product(product_info: ProductInfo):
            self.log(f"{product_info.name}を検索しています...")
            return ActionResult(
                extracted_content=f"{product_info.name}を検索します",
                include_in_memory=True
            )

        @self.controller.action('Add product to cart', param_model=ProductInfo)
        def add_to_cart(product_info: ProductInfo):
            self.log(f"{product_info.name}をカートに追加しています...")
            return ActionResult(
                extracted_content=f"{product_info.name}をカートに追加します",
                include_in_memory=True
            )

    def log(self, message):
        if self.callback:
            self.callback(message)

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # ブラウザのライフタイムをスレッドと同じにする
            loop.run_until_complete(self.shopping_task())
        except Exception as e:
            if self.error_callback:
                self.error_callback(f"エラーが発生しました: {str(e)}")
        finally:
            # 明示的にブラウザを閉じないことを強調
            if self.callback:
                self.callback("処理が完了しました。ブラウザは開いたままにしています。")
            # ブラウザを閉じないようにする
            if hasattr(self, 'browser') and self.browser:
                # 参照を保持し続ける
                self._browser_reference = self.browser
            loop.close()

    async def shopping_task(self):
        self.log("ブラウザを起動中...")
        try:
            # ブラウザインスタンス作成
            self.browser = Browser(
                config=BrowserConfig(
                    disable_security=True,
                    headless=False,
                )
            )

            # LLM設定
            llm = ChatOpenAI(
                model="deepseek-chat",
                openai_api_key="sk-19be6dacc5214a48849908ce166343a6", # deepseek api key
                base_url="https://api.deepseek.com",
            )

            # 全タスクを一度に指示するプロンプトを作成
            task_prompt = f"以下の手順を順番に実行してください：\n"
            task_prompt += f"1. イオンネットスーパーのウェブサイト{self.link}にアクセスしてください。\n"
            task_prompt += f"2. {self.aeon_id}と{self.pass_word}でログインしてください。\n"

            # 商品リストがある場合、各商品の検索と追加のタスクを追加
            for i, product in enumerate(self.products):
                task_prompt += f"{i + 3}. 「{product}」を検索してカートに追加してください。\n"

            task_prompt += "すべての操作が完了したら、そのまま待機してください。"

            self.log("イオンネットスーパーにログインして商品を追加します...")
            self.agent = Agent(
                task=task_prompt,
                llm=llm,
                browser=self.browser,
                use_vision=False,
                generate_gif=False,
                controller=self.controller
            )

            # 一度のrun()呼び出しで全タスクを実行
            await self.agent.run()
            self.log("すべての処理が完了しました")

            # ブラウザを閉じないように参照を保持
            self._browser_ref = self.browser
            self._agent_ref = self.agent

            # ブラウザを開いたままにする
            self.log("ブラウザは開いたままにしています。アプリケーションを終了するまで処理を維持します。")

            # 実行中はブラウザを閉じないように待機
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            self.log(f"エラーが発生しました: {str(e)}")
            raise

    def stop(self):
        self.running = False

    async def close_browser(self):
        if self.browser:
            try:
                await self.browser.close()
                self.log("ブラウザを閉じました")
            except Exception as e:
                self.log(f"ブラウザを閉じる際にエラー: {str(e)}")