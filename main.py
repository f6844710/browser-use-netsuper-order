import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from datetime import datetime
import openai
import io
import requests
from pydub import AudioSegment
from pydub.playback import play
import re
import os
import time
import json
import pyaudio
import wave
import numpy as np
# モジュールのインポート
from shopping_session import ShoppingThread
from pydantic import BaseModel
import traceback
from openai import OpenAI
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

NET_SUPER_ID = "00000000000"  # ネットスーパーのイオンID
NET_SUPER_PASSWORD = "******************"  # ネットスーパーのパスワード

# STT/TTSサーバー設定
STT_SERVER_URL = "http://100.119.75.44:3000/stt"
TTS_SERVER_URL = "http://192.168.1.5:10101"
TTS_SPEAKER_ID = 753902784  # sayo

class FunctionArgs(BaseModel):
    """商品追加用の引数定義"""
    product_name: str
    quantity: int = 1

class AINetSuperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIチャット対応ネットスーパー自動買い物アシスタント")
        self.root.geometry("1500x900")

        self.products = []
        self.worker = None
        self.task_prompt = None

        # 音声録音状態管理
        self.is_recording = False
        self.recording_thread = None

        # STT/TTS設定
        self.stt_url = STT_SERVER_URL
        self.tts_url = TTS_SERVER_URL
        self.tts_speaker = TTS_SPEAKER_ID

        # 接続情報設定
        self.link = 'https://shop.aeon.com/netsuper/'
        self.aeon_id = NET_SUPER_ID
        self.pass_word = NET_SUPER_PASSWORD

        # OpenAI API設定
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.messages = []
        self.client = OpenAI(api_key=self.api_key)
        self.system_content = """あなたは優れた買い物アシスタントです。
        お客様が欲しい商品をリストにまとめる手助けをしてください。
        お客様が「〜を買いたい」「〜が欲しい」と言ったら、その商品を抽出してください。
        料理のレシピを尋ねられたら、必要な材料も提案してください。
        商品を抽出したら「[商品]をリストに追加しますか？」と確認してください。"""
        self.st = ShoppingThread(
            self.products,
            self.link,
            self.aeon_id,
            self.pass_word,
            self.log_message,  # コールバック関数
            self.handle_error,  # エラーコールバック関数
            self.task_prompt  # この時点ではNoneだが後で設定される
        )
        self.create_widgets()
        self.initialize_openai()

    def initialize_openai(self):
        try:
            self.client = openai.OpenAI(api_key=self.api_key)
            self.messages.append({"role": "system", "content": self.system_content})
            self.log_message("AIアシスタントを初期化しました")
        except Exception as e:
            self.log_message(f"AIアシスタントの初期化に失敗しました: {str(e)}")

    def create_widgets(self):
        # メインフレーム
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左側：チャットエリア
        chat_frame = ttk.Frame(main_container)
        main_container.add(chat_frame, weight=1)

        # 右側：商品リスト・実行エリア
        shopping_frame = ttk.Frame(main_container)
        main_container.add(shopping_frame, weight=1)

        # チャットエリアの設定
        chat_label = ttk.Label(chat_frame, text="AIアシスタントとチャット")
        chat_label.pack(anchor=tk.W, pady=5)

        # チャット履歴表示
        self.chat_history = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, height=25)
        self.chat_history.pack(fill=tk.BOTH, expand=True, pady=5)
        self.chat_history.configure(state='disabled')

        # メッセージ入力
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X, pady=5)

        self.chat_entry = ttk.Entry(input_frame)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.chat_entry.bind("<Return>", lambda e: self.send_message())

        send_button = ttk.Button(input_frame, text="送信", command=self.send_message)
        send_button.pack(side=tk.RIGHT)

        # 音声合成オプション
        voice_frame = ttk.Frame(chat_frame)
        voice_frame.pack(fill=tk.X, pady=5)

        self.voice_enabled = tk.BooleanVar(value=False)
        voice_check = ttk.Checkbutton(voice_frame, text="音声合成を有効にする",
                                      variable=self.voice_enabled)
        voice_check.pack(anchor=tk.W)

        # 右側：音声入力ボタン（目立つ位置に配置）
        voice_input_frame = ttk.LabelFrame(shopping_frame, text="🎤 音声入力", padding="15")
        voice_input_frame.pack(fill=tk.X, pady=10)

        self.voice_input_button = ttk.Button(
            voice_input_frame,
            text="🎤 音声入力を開始",
            command=self.toggle_voice_input,
            width=30
        )
        self.voice_input_button.pack(fill=tk.X, ipady=10)

        # 録音状態表示ラベル
        self.recording_status_label = ttk.Label(
            voice_input_frame,
            text="準備完了",
            foreground="gray",
            font=("", 9)
        )
        self.recording_status_label.pack(pady=(5, 0))

        # 右側：認証情報設定
        auth_frame = ttk.LabelFrame(shopping_frame, text="認証情報", padding="10")
        auth_frame.pack(fill=tk.X, pady=5)

        ttk.Label(auth_frame, text="ウェブサイト:").grid(column=0, row=0, sticky=tk.W)
        self.link_entry = ttk.Entry(auth_frame, width=40)
        self.link_entry.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=5)
        self.link_entry.insert(0, self.link)

        ttk.Label(auth_frame, text="イオンID:").grid(column=0, row=1, sticky=tk.W)
        self.id_entry = ttk.Entry(auth_frame, width=40)
        self.id_entry.grid(column=1, row=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.id_entry.insert(0, self.aeon_id)

        ttk.Label(auth_frame, text="パスワード:").grid(column=0, row=2, sticky=tk.W)
        self.pass_entry = ttk.Entry(auth_frame, width=40, show="*")
        self.pass_entry.grid(column=1, row=2, sticky=(tk.W, tk.E), padx=5)
        self.pass_entry.insert(0, self.pass_word)

        # 商品リスト
        product_frame = ttk.LabelFrame(shopping_frame, text="商品リスト", padding="10")
        product_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        input_product_frame = ttk.Frame(product_frame)
        input_product_frame.pack(fill=tk.X)

        self.product_entry = ttk.Entry(input_product_frame)
        self.product_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.product_entry.bind("<Return>", lambda e: self.add_product_manual())

        add_button = ttk.Button(input_product_frame, text="追加", command=self.add_product_manual)
        add_button.pack(side=tk.RIGHT)

        # 商品リスト表示
        list_frame = ttk.Frame(product_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.product_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
        self.product_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.product_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.product_listbox.configure(yscrollcommand=scrollbar.set)

        # リスト操作ボタン
        button_frame = ttk.Frame(product_frame)
        button_frame.pack(fill=tk.X)

        delete_button = ttk.Button(button_frame, text="選択商品を削除", command=self.delete_selected)
        delete_button.pack(side=tk.LEFT, padx=5)

        clear_button = ttk.Button(button_frame, text="リスト全消去", command=self.clear_list)
        clear_button.pack(side=tk.LEFT)

        # 実行コントロール
        exec_frame = ttk.LabelFrame(shopping_frame, text="実行コントロール", padding="10")
        exec_frame.pack(fill=tk.X, pady=5)

        self.start_button = ttk.Button(exec_frame, text="買い物を開始", command=self.start_shopping)
        self.start_button.pack(fill=tk.X)

        self.stop_button = ttk.Button(exec_frame, text="処理を停止", command=self.stop_shopping, state=tk.DISABLED)
        self.stop_button.pack(fill=tk.X, pady=5)

        # ログ表示
        log_label = ttk.Label(exec_frame, text="ログ:")
        log_label.pack(anchor=tk.W, pady=2)

        self.log_text = scrolledtext.ScrolledText(exec_frame, height=8, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state='disabled')

        # APIキー設定
        api_frame = ttk.LabelFrame(shopping_frame, text="AI設定", padding="10")
        api_frame.pack(fill=tk.X, pady=5)

        ttk.Label(api_frame, text="OpenAI API Key:").pack(anchor=tk.W)
        self.api_key_entry = ttk.Entry(api_frame, width=50, show="*")
        self.api_key_entry.pack(fill=tk.X, pady=5)
        self.api_key_entry.insert(0, self.api_key)

        update_api_button = ttk.Button(api_frame, text="APIキーを更新", command=self.update_api_key)
        update_api_button.pack(anchor=tk.E)

        # 終了時の処理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # チャット初期メッセージ
        self.display_bot_message("こんにちは！買い物をお手伝いします。欲しい商品や料理名を教えてください。")

    def update_api_key(self):
        new_key = self.api_key_entry.get()
        if new_key != self.api_key:
            self.api_key = new_key
            self.initialize_openai()

    def send_message(self):
        user_message = self.chat_entry.get().strip()
        if not user_message:
            return

        self.chat_entry.delete(0, tk.END)
        self.display_user_message(user_message)

        # AIに送信
        self.messages.append({"role": "user", "content": user_message})

        # 別スレッドでAI応答を取得
        threading.Thread(target=self.get_ai_response).start()

    def get_ai_response(self):
        try:
            if not self.client:
                self.display_bot_message("エラー: AIクライアントが初期化されていません。APIキーを確認してください。")
                return

            # ツール定義 (変更なし)
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "add_product_to_list",
                        "description": "買い物リストに商品を追加する",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "product_name": {
                                    "type": "string",
                                    "description": "追加する商品名"
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "数量（デフォルト：1）"
                                }
                            },
                            "required": ["product_name"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "remove_product_from_list",
                        "description": "買い物リストから商品を削除する",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "product_name": {
                                    "type": "string",
                                    "description": "削除する商品名"
                                }
                            },
                            "required": ["product_name"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "start_shopping_order",
                        "description": "買い物リストの商品を使って注文処理を開始する",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=self.messages,
                temperature=0.5,
                tools=tools,
                tool_choice="auto",
            )

            # ツール呼び出しがあるか確認
            message = response.choices[0].message
            self.messages.append({"role": "assistant", "content": message.content or ""})

            # ツール呼び出しの処理
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.type == 'function':
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)

                        # 関数実行結果を格納する変数
                        function_result = ""

                        try:
                            # 関数の実行
                            if function_name == "add_product_to_list":
                                product_name = function_args.get("product_name", "")
                                function_result = self.add_product(product_name)
                            elif function_name == "remove_product_from_list":
                                product_name = function_args.get("product_name", "")
                                function_result = self.remove_product(product_name)
                            elif function_name == "start_shopping_order":
                                # 買い物処理は別スレッドで実行
                                self.root.after(0, self.start_shopping)
                                function_result = "買い物処理を開始します"
                            else:
                                function_result = f"不明な関数: {function_name}"

                        except Exception as func_error:
                            error_details = traceback.format_exc()
                            self.log_message(f"ツール関数実行エラー: {error_details}")
                            function_result = f"エラー: {str(func_error)}"

                        # 修正: roleを'tool'に変更
                        self.messages.append({
                            "role": "assistant",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": function_result
                        })

                # ツール呼び出し結果を元に再度AIに問い合わせ
                try:
                    second_response = self.client.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=self.messages,
                        temperature=0.5,
                    )

                    bot_message = second_response.choices[0].message.content
                    self.messages.append({"role": "assistant", "content": bot_message})

                    # UI更新
                    self.root.after(0, lambda: self.process_bot_response(bot_message))
                except Exception as second_error:
                    self.log_message(f"2回目の応答取得エラー: {str(second_error)}")
                    self.root.after(0, lambda: self.display_bot_message(f"エラーが発生しました: {str(second_error)}"))
            else:
                # 通常の応答処理
                bot_message = message.content
                # UI更新
                self.root.after(0, lambda: self.process_bot_response(bot_message))

        except Exception as e:
            error_details = traceback.format_exc()
            self.log_message(f"エラー詳細: {error_details}")
            self.root.after(0, lambda: self.display_bot_message(f"エラーが発生しました: {str(e)}"))

    def process_bot_response(self, message):
        self.display_bot_message(message)

        # 音声合成が有効なら実行
        if self.voice_enabled.get():
            threading.Thread(target=self.synthesize_speech, args=(message,)).start()

        # 商品提案を検出して追加確認ダイアログを表示
        product_match = re.search(r'\[(.+?)\]をリストに追加しますか？', message)
        if product_match:
            product = product_match.group(1)
            if messagebox.askyesno("商品追加確認", f"「{product}」を買い物リストに追加しますか？"):
                self.add_product(product)
                # AIに追加を通知して確認メッセージを表示
                self.messages.append({"role": "user", "content": f"{product}をリストに追加します"})
                threading.Thread(target=self.get_ai_response).start()

    def start_shopping(self):
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("警告", "すでに処理が実行中です")
            return

        if not self.products:
            messagebox.showwarning("警告", "商品リストが空です。商品を追加してください。")
            return

        self.link = self.link_entry.get()
        self.aeon_id = self.id_entry.get()
        self.pass_word = self.pass_entry.get()

        if not all([self.link, self.aeon_id, self.pass_word]):
            messagebox.showwarning("警告", "ウェブサイト、ID、パスワードのすべてを入力してください。")
            return

        self.start_button["state"] = "disabled"
        self.stop_button["state"] = "normal"
        self.log_message("買い物処理を開始します...")

        try:
            # 以前のワーカーが存在する場合は完全に終了させる
            if self.worker:
                try:
                    self.worker.stop()
                    self.worker = None
                except Exception as e:
                    self.log_message(f"前回のワーカー停止中にエラー: {str(e)}")

            # 新しいワーカーを作成
            self.worker = ShoppingThread(
                self.products.copy(),
                self.link,
                self.aeon_id,
                self.pass_word,
                self.log_message,
                self.handle_error,
                None  # 初期値はNone
            )

            # メッセージ履歴を設定
            self.worker.messages = self.messages.copy()

            # タスクプロンプトを生成
            try:
                self.task_prompt = self.worker.generate_task_prompt()
                self.log_message("タスクプロンプトを生成しました")
            except Exception as e:
                self.log_message(f"タスクプロンプト生成エラー: {str(e)}")
                raise

            # ワーカーにタスクプロンプトを設定
            self.worker.task_prompt = self.task_prompt

            # スレッド開始
            self.worker.start()

            # ステータス監視スレッド開始
            threading.Thread(target=self.monitor_thread_status, daemon=True).start()

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.log_message(f"買い物処理の開始中にエラー: {error_details}")
            self.start_button["state"] = "normal"
            self.stop_button["state"] = "disabled"
            messagebox.showerror("エラー", f"買い物処理の開始に失敗しました: {str(e)}")

    def synthesize_speech(self, text):
        """TTSサーバーを使用して音声合成を実行"""
        try:
            # 長すぎる場合は短縮
            if len(text) > 300:
                text = text[:297] + "..."

            # 音声合成用のクエリを作成
            params = {"text": text, "speaker": self.tts_speaker}
            query_response = requests.post(
                f"{self.tts_url}/audio_query",
                params=params,
                timeout=10
            ).json()

            # 音声合成を実行
            audio_response = requests.post(
                f"{self.tts_url}/synthesis",
                params={"speaker": self.tts_speaker},
                headers={"accept": "audio/wav", "Content-Type": "application/json"},
                data=json.dumps(query_response),
                timeout=30
            )

            # レスポンスから音声データを取得して再生
            audio_io = io.BytesIO(audio_response.content)
            audio = AudioSegment.from_file(audio_io, format="wav")
            play(audio)

        except Exception as e:
            self.log_message(f"音声合成エラー: {str(e)}")

    def toggle_voice_input(self):
        """音声入力のオン/オフを切り替え"""
        if self.is_recording:
            # 録音を停止
            self.is_recording = False
            self.voice_input_button.config(text="🎤 音声入力")
            self.log_message("録音を停止しました")
        else:
            # 録音を開始
            self.is_recording = True
            self.voice_input_button.config(text="⏹️ 停止")
            self.log_message("🎤 録音準備中...")
            self.recording_thread = threading.Thread(target=self.record_audio_input, daemon=True)
            self.recording_thread.start()

    def record_audio_input(self, duration=5, sample_rate=16000, input_volume=3.0):
        """マイクから音声を録音してSTTで変換し、チャットに送信"""
        try:
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1

            audio = pyaudio.PyAudio()

            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=sample_rate,
                input=True,
                frames_per_buffer=CHUNK
            )

            # マイクのウォームアップ（最初の数フレームを破棄）
            self.log_message("マイクを準備中...")
            warmup_chunks = int(sample_rate / CHUNK * 0.5)  # 0.5秒間ウォームアップ
            for _ in range(warmup_chunks):
                stream.read(CHUNK)  # 読み捨て

            self.log_message("録音中...")

            frames = []
            # 録音時間を少し長めに調整（ウォームアップ分を考慮）
            total_chunks = int(sample_rate / CHUNK * (duration + 0.5))

            for i in range(total_chunks):
                if not self.is_recording:
                    break

                data = stream.read(CHUNK)

                # 音量を増幅
                audio_data = np.frombuffer(data, dtype=np.int16)
                audio_data = np.clip(audio_data * input_volume, -32768, 32767).astype(np.int16)
                frames.append(audio_data.tobytes())

            stream.stop_stream()
            stream.close()
            audio.terminate()

            self.log_message("✓ 録音完了")

            # ローカルフォルダに保存
            # recorded_audio フォルダを作成（存在しない場合）
            audio_dir = os.path.join(os.path.dirname(__file__), "recorded_audio")
            os.makedirs(audio_dir, exist_ok=True)

            # タイムスタンプ付きのファイル名で保存
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            temp_wav_path = os.path.join(audio_dir, f"voice_input_{timestamp}.wav")

            with wave.open(temp_wav_path, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(audio.get_sample_size(FORMAT))
                wf.setframerate(sample_rate)
                wf.writeframes(b"".join(frames))

            self.log_message(f"音声ファイルを保存しました: {temp_wav_path}")

            # STTサーバーに送信
            recognized_text = self.send_wav_to_stt(temp_wav_path)


            # 認識されたテキストをチャットに入力
            if recognized_text:
                self.root.after(0, lambda: self.chat_entry.insert(0, recognized_text))
                self.root.after(0, lambda: self.log_message(f"認識結果: {recognized_text}"))

            # 録音状態をリセット
            self.is_recording = False
            self.root.after(0, lambda: self.voice_input_button.config(text="🎤 音声入力を開始"))
            self.root.after(0, lambda: self.recording_status_label.config(text="準備完了", foreground="gray"))

        except Exception as e:
            self.log_message(f"音声入力エラー: {str(e)}")
            self.is_recording = False
            self.root.after(0, lambda: self.voice_input_button.config(text="🎤 音声入力を開始"))
            self.root.after(0, lambda: self.recording_status_label.config(text="エラー", foreground="red"))

    def send_wav_to_stt(self, wav_path):
        """WAVファイルをOpenAI Whisper APIに送信してテキストを取得"""
        try:
            if not self.client:
                self.log_message("エラー: OpenAI APIクライアントが初期化されていません")
                return ""

            with open(wav_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja"  # 日本語を指定
                )

            # Whisperの結果からテキストを取得（スペースは保持）
            return transcript.text

        except Exception as e:
            self.log_message(f"Whisper STTエラー: {str(e)}")
            return ""

    def display_user_message(self, message):
        self.chat_history.configure(state='normal')
        self.chat_history.insert(tk.END, "あなた: ", "user_tag")
        self.chat_history.insert(tk.END, message + "\n\n")
        self.chat_history.see(tk.END)
        self.chat_history.configure(state='disabled')

        # タグ設定
        self.chat_history.tag_configure("user_tag", foreground="blue", font=("", 10, "bold"))
        self.chat_history.tag_configure("bot_tag", foreground="green", font=("", 10, "bold"))

    def display_bot_message(self, message):
        self.chat_history.configure(state='normal')
        self.chat_history.insert(tk.END, "アシスタント: ", "bot_tag")
        self.chat_history.insert(tk.END, message + "\n\n")
        self.chat_history.see(tk.END)
        self.chat_history.configure(state='disabled')

    def update_product_listbox(self):
        self.product_listbox.delete(0, tk.END)  # 一旦全部クリア
        for product in self.products:
            self.product_listbox.insert(tk.END, product)

    def add_product_manual(self):
        product = self.product_entry.get().strip()
        if product:
            self.add_product(product)
            self.product_entry.delete(0, tk.END)

    def add_product(self, product):
        if not product or product in self.products:  # 空または重複チェック
            return f"「{product}」は既にリストに追加されています" if product else "商品名が指定されていません"

        self.products.append(product)
        self.product_listbox.insert(tk.END, product)
        self.log_message(f"商品「{product}」をリストに追加しました")
        self.update_product_listbox()

        # AIに追加を通知
        notification = f"ユーザーが「{product}」を買い物リストに追加しました"
        self.messages.append({"role": "system", "content": notification})

        # 商品追加のフィードバックメッセージを返す
        return f"「{product}」をリストに追加しました。他に必要な商品はありますか？"

    def remove_product(self, product):
        """商品をリストから削除する"""
        if not product:
            return "商品名が指定されていません"

        if product not in self.products:
            return f"「{product}」はリストに存在しません"

        self.products.remove(product)
        self.update_product_listbox()
        self.log_message(f"商品「{product}」をリストから削除しました")

        # AIに削除を通知
        notification = f"ユーザーが「{product}」を買い物リストから削除しました"
        self.messages.append({"role": "system", "content": notification})

        return f"「{product}」をリストから削除しました"

    def delete_selected(self):
        selected = self.product_listbox.curselection()
        if not selected:
            return

        # 逆順に削除（インデックスがずれないように）
        for i in sorted(selected, reverse=True):
            product = self.product_listbox.get(i)
            self.product_listbox.delete(i)
            self.products.remove(product)
            self.log_message(f"商品「{product}」をリストから削除しました")

    def clear_list(self):
        if self.product_listbox.size() > 0:
            self.product_listbox.delete(0, tk.END)
            self.products.clear()
            self.log_message("商品リストをクリアしました")

    def stop_shopping(self):
        if self.worker and self.worker.is_alive():
            if messagebox.askyesno("確認", "買い物処理を中断しますか？"):
                self.log_message("買い物処理を中断しています...")
                self.worker.stop()
                self.stop_button["state"] = "disabled"

    def monitor_thread_status(self):
        """ワーカースレッドのステータスを監視して、完了したらUIを更新する"""
        while self.worker and self.worker.is_alive():
            # 0.5秒ごとにチェック
            time.sleep(0.5)

        # スレッドが終了したらUIを更新
        self.root.after(0, self.update_ui_after_thread)

    def update_ui_after_thread(self):
        """スレッド終了後のUI更新を行う"""
        self.start_button["state"] = "normal"
        self.stop_button["state"] = "disabled"
        self.log_message("処理が完了しました")

    def handle_error(self, error_msg):
        self.log_message(error_msg)
        self.root.after(0, lambda: self.update_ui_after_error(error_msg))

    def update_ui_after_error(self, error_msg):
        self.start_button["state"] = "normal"
        self.stop_button["state"] = "disabled"
        messagebox.showerror("エラー", error_msg)

    def log_message(self, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message_with_timestamp = f"[{timestamp}] {message}"

        # UIスレッドからの呼び出しか確認
        if threading.current_thread() == threading.main_thread():
            self._update_log(message_with_timestamp)
        else:
            # 別スレッドからの場合、UIスレッドにタスクを委譲
            self.root.after(0, lambda: self._update_log(message_with_timestamp))

    def _update_log(self, message):
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)  # 自動スクロール
        self.log_text.configure(state='disabled')

    def on_closing(self):
        if self.worker and self.worker.is_alive():
            if messagebox.askyesno("確認", "処理が実行中です。本当に終了しますか？"):
                self.log_message("終了処理中...")
                # 先にrunningフラグをFalseにしてループを抜ける
                self.worker.running = False
                self.worker.stop()
                # 少し待機してからウィンドウを閉じる
                self.root.after(2000, self.root.destroy)
            else:
                return
        else:
            self.root.destroy()


# models.py ファイル用のコード
if not os.path.exists('models.py'):
    with open('models.py', 'w', encoding='utf-8') as f:
        f.write('''from pydantic import BaseModel

class WebpageInfo(BaseModel):
    link: str

class ProductInfo(BaseModel):
    name: str
    quantity: int = 1
''')

# アプリケーション起動
if __name__ == "__main__":
    root = tk.Tk()
    app = AINetSuperApp(root)
    root.mainloop()