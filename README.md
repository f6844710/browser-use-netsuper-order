# AIチャット対応ネットスーパー自動買い物アシスタント

音声認識とAIチャットで対話しながら、イオンネットスーパーでの買い物を自動化するGUIアプリケーションです。

## 概要

このプロジェクトは、AIチャットアシスタント、音声認識（STT）、音声合成（TTS）、ブラウザ自動化技術を組み合わせて、イオンネットスーパーでの商品検索、カート追加、注文までのプロセスを自動化します。音声で「牛乳が欲しい」と話しかけるだけで、AIが商品をリストに追加し、自動的に注文処理を行います。

## 主な機能

- 🎤 **音声入力対応**: OpenAI Whisper APIを使用した高精度な音声認識
- 🔊 **音声読み上げ**: TTSサーバーを使用してAIの応答を音声で確認
- 🤖 **AIチャットアシスタント**: Groq API（GPT-oss-120b）による自然な対話
- 🛠️ **ツール機能**: 商品追加・削除、買い物開始などの関数呼び出し
- 🛒 **自動ブラウザ操作**: browser-useを使用した商品検索とカート追加
- 💬 **チャット履歴の活用**: 会話から商品の詳細情報を抽出してタスクに反映
- 📝 **リアルタイムログ**: 処理状況をリアルタイムで確認可能
- 🖥️ **使いやすいGUI**: Tkinterベースの直感的なインターフェース

## 必要な環境

- Python 3.12以上
- Groq APIキー
- イオンネットスーパーのアカウント
- 音声認識用のマイク
- （オプション）TTSサーバー（音声読み上げを使用する場合）

## インストール

```bash
# 必要なパッケージをインストール
pip install -r requirements.txt
```

requirements.txtには以下のパッケージが含まれます：
```
browser-use
openai
groq
pydantic
python-dotenv
pydub
pyaudio
numpy
```

### ffmpegのインストール

音声処理にはffmpegが必要です。

**Windows環境の場合:**
- [こちらの記事](https://qiita.com/Tadataka_Takahashi/items/9dcb0cf308db6f5dc31b)を参考にしてインストールしてください

**Linux環境の場合:**
```bash
sudo apt install ffmpeg
```

## セットアップ

### 1. 環境変数の設定

`.env`ファイルを作成して、必要なAPIキーを設定します：

```env
GROQ_API_KEY=your_groq_api_key_here
```

### 2. 設定のカスタマイズ

`main.py`の以下の設定を必要に応じて変更してください：

```python
NET_SUPER_ID = "your_aeon_id"  # イオンネットスーパーのID
NET_SUPER_PASSWORD = "your_password"  # イオンネットスーパーのパスワード
TTS_SERVER_URL = "http://your-tts-server:10101"  # TTSサーバーのURL（オプション）
```

## 使用方法

### GUIアプリケーションの起動

```bash
python main.py
```

### 基本的な使い方

1. **音声入力で商品を追加**
   - 🎤ボタンをクリック（または音声入力を開始ボタン）
   - 「牛乳が欲しい」「卵を買いたい」などと話す
   - AIが商品をリストに追加

2. **テキスト入力で商品を追加**
   - チャット欄に「パンが欲しい」と入力
   - AIが商品をリストに追加するか確認

3. **レシピから商品を提案**
   - 「カレーライスを作りたい」と入力
   - AIが必要な材料を提案してリストに追加

4. **買い物を開始**
   - 「買い物を開始」ボタンをクリック
   - または「注文してください」とAIに依頼
   - 自動的にブラウザが起動して商品を検索・カートに追加

### 音声合成の有効化

- 「音声合成を有効にする」にチェックを入れると、AIの応答が音声で読み上げられます
- TTSサーバーが必要です（設定を確認してください）

### プログラムからの使用例

```python
from shopping_session import ShoppingThread

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
    task_prompt=None
)

# スレッドを開始
thread.start()
thread.join()
```

## ファイル構成

- `main.py`: GUIアプリケーションのメインファイル（Tkinterベース）
- `shopping_session.py`: ブラウザ自動化ロジック（browser-use）
- `models.py`: データモデル定義（Pydantic）
- `requirements.txt`: 必要なPythonパッケージ
- `.env`: 環境変数（APIキーなど）

## 技術スタック

- **GUI**: Tkinter
- **AI**: Groq API (GPT-oss-120b)
- **STT**: OpenAI Whisper API (whisper-large-v3)
- **TTS**: AivisSpeech (ローカル版)
- **ブラウザ自動化**: browser-use
- **音声処理**: PyAudio, pydub, numpy

## AIアシスタントの機能

AIアシスタントは以下のツールを使用できます：

1. **add_product_to_list**: 商品を買い物リストに追加
2. **remove_product_from_list**: 商品を買い物リストから削除
3. **start_shopping_order**: 買い物リストを使って注文処理を開始

これらの関数は会話の流れに応じて自動的に呼び出されます。

## トラブルシューティング

### 音声入力がうまく動作しない

- マイクが正しく接続されているか確認してください
- Windowsのプライバシー設定でマイクへのアクセスが許可されているか確認してください
- 音量が適切に設定されているか確認してください

### TTSが動作しない

- TTSサーバーが起動しているか確認してください
- `TTS_SERVER_URL`が正しく設定されているか確認してください
- 音声合成を使用しない場合は、チェックボックスをオフにしてください

### APIキーのエラー

- `.env`ファイルに`GROQ_API_KEY`が正しく設定されているか確認してください
- GUIの「AI設定」セクションでAPIキーを更新することもできます

## 注意事項

- Groq APIの利用には料金が発生する場合があります
- OpenAI Whisper APIの利用には料金が発生します
- ブラウザは自動的に閉じられません（手動での確認が可能）
- 実際の注文前に動作を十分に確認してください
- 音声入力は録音ボタンを押してから約5秒間録音されます

## ライセンス

MIT License

## 貢献

プルリクエストを歓迎します！

