import asyncio
import threading
import re
from typing import List, Callable, Optional
from browser_use import Agent, Browser
from browser_use import ChatGroq

groq_api_key = "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"

class ShoppingThread(threading.Thread):
    """
    イオンネットスーパーでの買い物を自動化するスレッドクラス

    Attributes:
        products: 購入する商品のリスト
        link: ネットスーパーのURL
        aeon_id: ログインID
        pass_word: ログインパスワード
        callback: ログメッセージ用のコールバック関数
        error_callback: エラーメッセージ用のコールバック関数
        task_prompt: タスクプロンプト
        messages: チャット履歴
    """

    def __init__(
        self,
        products: List[str],
        link: str,
        aeon_id: str,
        pass_word: str,
        callback: Optional[Callable[[str], None]],
        error_callback: Optional[Callable[[str], None]],
        task_prompt: str = ""
    ):
        super().__init__(daemon=True)
        self.products = products
        self.link = link
        self.aeon_id = aeon_id
        self.pass_word = pass_word
        self.browser = None
        self.agent = None
        self.callback = callback
        self.error_callback = error_callback
        self.running = True
        self.task_prompt = task_prompt
        self.messages = []
        self._browser_reference = None

    def log(self, message: str) -> None:
        """ログメッセージをコールバック経由で送信"""
        if self.callback:
            self.callback(message)

    def run(self) -> None:
        """スレッドのメイン実行メソッド"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.shopping_task())
        except Exception as e:
            error_msg = f"エラーが発生しました: {str(e)}"
            self.log(error_msg)
            if self.error_callback:
                self.error_callback(error_msg)
        finally:
            # ブラウザを開いたままにする
            if self.browser:
                self._browser_reference = self.browser
                self.log("処理が完了しました。ブラウザは開いたままにしています。")
            loop.close()

    def generate_task_prompt(self) -> str:
        """
        チャット履歴と商品リストからタスクプロンプトを生成

        Returns:
            str: 生成されたタスクプロンプト
        """
        # ログイン手順
        prompt = f"""以下の手順を順番に実行してください：
1. {self.link} にアクセスしてログインしてください（ID: {self.aeon_id}, Password: {self.pass_word}）
"""

        # 商品リストの詳細情報を追加
        for i, product in enumerate(self.products, 2):
            context = self.get_product_context(product)
            line = f"{i}. 「{product}」を検索してカートに追加してください。"

            if context:
                line += f" 補足情報：{context}"

            prompt += line + "\n"

        # 注文手順
        prompt += f"{len(self.products) + 2}. 注文画面に進み、注文手続きを完了してください。"

        self.task_prompt = prompt
        self.log("タスクプロンプトを生成しました")
        return prompt

    def get_product_context(self, product: str) -> str:
        """
        商品に関連するチャット履歴のコンテキストを抽出

        Args:
            product: 商品名

        Returns:
            str: 抽出されたコンテキスト情報
        """
        context = []
        product_keywords = product.lower().split()

        for msg in self.messages:
            if msg.get("role") not in ["user", "assistant"]:
                continue

            content = msg.get("content", "").lower()

            # 商品名に関連する会話を検出
            if any(keyword in content for keyword in product_keywords):
                # 関連情報を抽出
                pattern = r'(.*' + re.escape(product) + r'.*(?:がいい|希望|欲しい|推奨|特徴|ブランド).*)'
                relevant_info = re.findall(pattern, msg["content"], re.IGNORECASE)
                if relevant_info:
                    context.extend(relevant_info)

        # 長すぎる場合は短縮
        combined = "; ".join(context)
        if len(combined) > 100:
            return combined[:97] + "..."

        return combined

    async def shopping_task(self) -> None:
        """
        メインのショッピングタスクを実行

        ブラウザを起動し、LLMエージェントを初期化して、
        商品の検索・カートへの追加・注文を自動実行します。
        """
        self.log("ブラウザを起動中...")

        try:
            # ブラウザインスタンス作成
            self.browser = Browser(
                disable_security=True,
                headless=False,
            )

            # LLM設定
            llm = ChatGroq(api_key=groq_api_key,
                model="openai/gpt-oss-120b",
                temperature=0.2,
            )

            # タスクプロンプト生成
            task_prompt = self.generate_task_prompt()
            self.log("イオンネットスーパーにログインして商品を追加します...")

            # エージェント初期化（フォールバック機能付き）
            self.agent = await self._initialize_agent(task_prompt, llm)

            # タスク実行
            await self.agent.run()
            self.log("すべての処理が完了しました")

            # ブラウザを閉じないように参照を保持
            self._browser_reference = self.browser

        except Exception as e:
            self.log(f"ショッピングタスク中にエラーが発生しました: {str(e)}")
            raise

    async def _initialize_agent(self, task_prompt: str, llm) -> Agent:
        """
        エージェントを初期化（複数の方法でフォールバック）

        Args:
            task_prompt: タスクプロンプト
            llm: 言語モデル

        Returns:
            Agent: 初期化されたエージェント
        """
        # 標準初期化を試行
        try:
            agent = Agent(
                task=task_prompt,
                llm=llm,
                browser=self.browser,
                use_vision=False,
            )
            self.log("エージェント初期化成功")
            return agent
        except Exception as e:
            self.log(f"標準初期化エラー: {str(e)}。基本初期化を試みます...")

        # 最小限のパラメータで初期化（フォールバック）
        try:
            agent = Agent(
                task=task_prompt,
                llm=llm,
                browser=self.browser
            )
            self.log("基本初期化で成功")
            return agent
        except Exception as e:
            self.log(f"基本初期化もエラー: {str(e)}")
            raise

    def stop(self) -> None:
        """
        ショッピングスレッドを停止

        ブラウザとエージェントをクリーンアップします。
        """
        self.running = False
        self.log("停止を要求されました...")

        try:
            if self.browser:
                self.log("ブラウザをクリーンアップしています...")
                self.browser = None
        except Exception as e:
            self.log(f"ブラウザクリーンアップ中にエラー: {str(e)}")

        try:
            if self.agent:
                self.log("エージェントをクリーンアップしています...")
                self.agent = None
        except Exception as e:
            self.log(f"エージェントクリーンアップ中にエラー: {str(e)}")

        self.log("クリーンアップが完了しました")
