from tkinter import ttk, scrolledtext, messagebox
import tkinter as tk
from datetime import datetime
from shopping_session import ShoppingThread

class NetSuperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("イオンネットスーパー自動買い物アシスタント")
        self.root.geometry("650x600")

        self.products = []
        self.worker = None

        # 接続情報設定
        self.link = 'https://shop.aeon.com/netsuper/'
        self.aeon_id = "09074037766"
        self.pass_word = "4t7DyJgUg9sn5H6"

        self.create_widgets()

    def create_widgets(self):
        # メインフレーム
        mainframe = ttk.Frame(self.root, padding="10")
        mainframe.pack(fill=tk.BOTH, expand=True)

        # 認証情報フレーム
        auth_frame = ttk.LabelFrame(mainframe, text="認証情報", padding="10")
        auth_frame.pack(fill=tk.X, pady=5)

        # ウェブサイト設定
        ttk.Label(auth_frame, text="ウェブサイト:").grid(column=0, row=0, sticky=tk.W)
        self.link_entry = ttk.Entry(auth_frame, width=50)
        self.link_entry.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=5)
        self.link_entry.insert(0, self.link)

        # ID設定
        ttk.Label(auth_frame, text="イオンID:").grid(column=0, row=1, sticky=tk.W)
        self.id_entry = ttk.Entry(auth_frame, width=50)
        self.id_entry.grid(column=1, row=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.id_entry.insert(0, self.aeon_id)

        # パスワード設定
        ttk.Label(auth_frame, text="パスワード:").grid(column=0, row=2, sticky=tk.W)
        self.pass_entry = ttk.Entry(auth_frame, width=50, show="*")
        self.pass_entry.grid(column=1, row=2, sticky=(tk.W, tk.E), padx=5)
        self.pass_entry.insert(0, self.pass_word)

        # 商品リスト管理フレーム
        product_frame = ttk.LabelFrame(mainframe, text="商品リスト管理", padding="10")
        product_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 商品入力エリア
        input_frame = ttk.Frame(product_frame)
        input_frame.pack(fill=tk.X)

        self.product_entry = ttk.Entry(input_frame, width=40)
        self.product_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.product_entry.bind("<Return>", lambda e: self.add_product())
        self.product_entry.focus()

        add_button = ttk.Button(input_frame, text="追加", command=self.add_product)
        add_button.pack(side=tk.RIGHT, padx=5)

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

        # 実行コントロールフレーム
        exec_frame = ttk.LabelFrame(mainframe, text="実行コントロール", padding="10")
        exec_frame.pack(fill=tk.BOTH, pady=5)

        self.start_button = ttk.Button(exec_frame, text="買い物を開始", command=self.start_shopping)
        self.start_button.pack(fill=tk.X)

        # ログ表示エリア
        ttk.Label(exec_frame, text="ログ:").pack(anchor=tk.W, pady=2)
        self.log_text = scrolledtext.ScrolledText(exec_frame, width=70, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state='disabled')

        # 終了時の処理を設定
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def add_product(self):
        product = self.product_entry.get().strip()
        if product:
            self.products.append(product)
            self.product_listbox.insert(tk.END, product)
            self.product_entry.delete(0, tk.END)
            self.log_message(f"商品「{product}」をリストに追加しました")

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
        self.log_message("買い物処理を開始します...")

        self.worker = ShoppingThread(
            self.products.copy(),
            self.link,
            self.aeon_id,
            self.pass_word,
            self.log_message,
            self.handle_error
        )
        self.worker.start()

    def handle_error(self, error_msg):
        self.log_message(error_msg)
        self.start_button["state"] = "normal"
        messagebox.showerror("エラー", error_msg)

    def log_message(self, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message_with_timestamp = f"[{timestamp}] {message}"
        self._log_message(message_with_timestamp)

    def _log_message(self, message):
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
                # 少し待機してからウィンドウを閉じる
                self.root.after(2000, self.root.destroy)
            else:
                return
        else:
            self.root.destroy()