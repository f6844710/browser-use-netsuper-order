# イオンネットスーパー自動注文システム

`browser-use`を使用して、イオンネットスーパーでの買い物を自動化するアプリケーションです。

## 概要

このプロジェクトは、AIエージェント（GPT-4o-mini）とブラウザ自動化技術を組み合わせて、イオンネットスーパーでの商品検索、カート追加、注文までのプロセスを自動化します。

## 主な機能

- 🤖 **AIエージェントによる自動操作**: GPT-4o-miniを使用したインテリジェントなブラウザ操作
- 🛒 **商品検索とカート追加**: 商品リストから自動的に検索してカートに追加
- 💬 **チャット履歴の活用**: 会話から商品の詳細情報を抽出してタスクに反映
- 🔄 **エラーハンドリング**: 複数の初期化方法でフォールバック対応
- 📝 **リアルタイムログ**: 処理状況をリアルタイムで確認可能

## 必要な環境

- Python 3.12以上
- OpenAI APIキー
- イオンネットスーパーのアカウント

## インストール

```bash
# 必要なパッケージをインストール
pip install browser-use langchain-openai pydantic
```

## 使用方法

### 基本的な使用例

```python
from shopping_session import ShoppingThread
from models import ProductInfo

# 商品リスト
products = ["牛乳", "卵", "パン"]

# ショッピングスレッドを作成
thread = ShoppingThread(
    products=products,
    link="https://shop.aeon.com/netsuper/",
    aeon_id="your_id",
    pass_word="your_password",
    callback=lambda msg: print(f"[LOG] {msg}"),
    error_callback=lambda msg: print(f"[ERROR] {msg}"),
    task_prompt=""
)

# スレッドを開始
thread.start()
thread.join()
```

## ファイル構成

- `shopping_session.py`: メインのショッピング自動化ロジック
- `models.py`: データモデル定義（Pydantic）
- `main.py`: アプリケーションのエントリーポイント

## 注意事項

- OpenAI APIの利用には料金が発生します
- ブラウザは自動的に閉じられません（手動での確認が可能）
- 実際の注文前に動作を十分に確認してください

## ライセンス

MIT License

## 貢献

プルリクエストを歓迎します！

