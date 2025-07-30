import asyncio
import threading
from browser_use.controller.service import Controller
from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use import ChatOpenAI
from langchain_core.runnables import RunnableConfig
from browser_use.agent.views import ActionResult
from models import WebpageInfo, ProductInfo
import re

class ShoppingThread(threading.Thread):
    def __init__(self, products, link, aeon_id, pass_word, callback, error_callback, task_prompt):
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
        self.task_prompt = task_prompt
        self.messages = []

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

    def generate_task_prompt(self):
        """チャット履歴と商品リストからタスクプロンプトを生成"""
        # 基本的なプロンプト
        prompt = f"""以下の手順を順番に実行してください：
        1. {self.link} にアクセスしてログインしてください（ID: {self.aeon_id}, Password: {self.pass_word}）
        """

        # 商品リストの詳細情報を追加
        for i, product in enumerate(self.products, 2):
            # チャット履歴から関連する情報を抽出
            context = self.get_product_context(product)
            line = f"{i}. 「{product}」を検索してカートに追加してください。"

            # 関連情報があれば追加
            if context:
                line += f" 補足情報：{context}"

            prompt += line + "\n"

        # 最後のステップ
        prompt += f"{len(self.products) + 2}. 注文画面に進み、注文手続きを完了してください。"

        self.task_prompt = prompt
        self.log("タスクプロンプトを生成しました")
        return prompt

    def get_product_context(self, product):
        """商品に関連するチャット履歴のコンテキストを抽出"""
        context = []
        product_keywords = product.lower().split()

        # チャット履歴から関連するメッセージを抽出
        for msg in self.messages:
            if msg["role"] in ["user", "assistant"]:
                content = msg["content"].lower()
                # 商品名に関連する会話を検出
                if any(keyword in content for keyword in product_keywords):
                    # 簡潔な情報を抽出（「〜がいい」「〜を希望」などの表現）
                    relevant_info = re.findall(r'(.*' + product + r'.*(?:がいい|希望|欲しい|推奨|特徴|ブランド).*)',
                                                  msg["content"], re.IGNORECASE)
                    if relevant_info:
                        context.extend(relevant_info)

        # 長すぎる場合は短縮
        combined = "; ".join(context)
        if len(combined) > 100:
            combined = combined[:97] + "..."

        return combined

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
                model="gpt-4.1-mini",
                temperature=0.2,
            )

            task_prompt = self.generate_task_prompt()

            self.log("イオンネットスーパーにログインして商品を追加します...")

            try:
                # 最新バージョンに対応するエージェント初期化
                self.agent = Agent(
                    task=task_prompt,
                    llm=llm,
                    browser=self.browser,
                    use_vision=False,
                    generate_gif=False,
                    controller=self.controller,
                )
                self.log("エージェント初期化成功")
            except Exception as agent_error:
                self.log(f"標準初期化エラー: {str(agent_error)}。別の方法を試します...")
                try:
                    # 別のinitシグネチャを試す（新しいバージョン用）
                    self.agent = Agent(
                        task=task_prompt,
                        llm=llm,
                        browser=self.browser,
                        use_vision=False,
                        generate_gif=False,
                        controller=self.controller,
                        invoke_config=RunnableConfig(callbacks=None)
                    )
                    self.log("代替初期化方法で成功")
                except Exception as alt_error:
                    # 最終的なフォールバック（パラメータを最小限に）
                    self.log(f"代替初期化エラー: {str(alt_error)}。基本初期化を試みます...")
                    self.agent = Agent(
                        task=task_prompt,
                        llm=llm,
                        browser=self.browser
                    )
                    self.log("基本初期化で成功")

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
        try:
            if hasattr(self, 'browser') and self.browser:
                self.log("ブラウザを終了しています...")
                self.browser.close()
        except Exception as e:
            self.log(f"ブラウザ終了中にエラー: {str(e)}")

        try:
            if hasattr(self, 'controller') and self.controller:
                self.log("コントローラーをクリーンアップしています...")
                self.controller = None
        except Exception as e:
            self.log(f"コントローラークリーンアップ中にエラー: {str(e)}")

    async def close_browser(self):
        if self.browser:
            try:
                await self.browser.close()
                self.log("ブラウザを閉じました")
            except Exception as e:
                self.log(f"ブラウザを閉じる際にエラー: {str(e)}")