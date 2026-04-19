import pyaudio, struct, math

audio = pyaudio.PyAudio()
print("=== Устройства ввода ===")
for i in range(audio.get_device_count()):
    info = audio.get_device_info_by_index(i)
    if info["maxInputChannels"] > 0:
        print(f"[{i}] {info['name']}  rate={int(info['defaultSampleRate'])}")

d = audio.get_default_input_device_info()
print(f"\nПо умолчанию: [{d['index']}] {d['name']}")
audio.terminate()
