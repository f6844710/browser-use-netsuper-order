import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import requests
from pydub import AudioSegment
from pydub.playback import play
import concurrent

# APIサーバーのエンドポイントURL
URL = "http://192.168.1.5:10101"
# 話者ID (話させたい音声モデルidに変更してください)
speaker = 127206176  # subaru


def create_synthesis(text: str):
    params = {"text": text, "speaker": speaker}
    query_response = requests.post(f"{URL}/audio_query", params=params).json()

    audio_response = requests.post(
        f"{URL}/synthesis",
        params={"speaker": speaker},
        headers={"accept": "audio/wav", "Content-Type": "application/json"},
        data=json.dumps(query_response),
    )

    audio_io = io.BytesIO(audio_response.content)
    return audio_io


def playback(end_of_playback, audio_io):
    wave_file = AudioSegment.from_file(audio_io, format="wav")
    play(wave_file)
    end_of_playback += 1
    return end_of_playback


def threading_synthesis(a_dict, end_of_playback):
    def create_synthesis_and_get_audio_io(text):
        audio_io = create_synthesis(text)
        return audio_io

    # １回目の並列処理
    executor = ThreadPoolExecutor(max_workers=len(a_dict))
    futures = []
    for i in range(len(a_dict)):
        # tts_aivis.py の該当箇所
        text_key = 'text' + str(i + 1)
        if text_key in a_dict:
            future = executor.submit(create_synthesis_and_get_audio_io, str(a_dict[text_key]))
        # future = executor.submit(create_synthesis_and_get_audio_io, str(a_dict['text' + str(i + 1)]))
            futures.append(future)
    audio_ios = [future.result() for future in futures]

    for i in range(len(a_dict)):
        # 並列処理
        thread = threading.Thread(
            target=lambda: create_synthesis_and_get_audio_io(str(a_dict['text' + str(i + 1)])))
        thread.start()
    thread.join(5)

    for i, audio_io in enumerate(audio_ios):
        # 並列処理
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(end_of_playback)
        end_of_playback = 0
        playback(end_of_playback, audio_io)