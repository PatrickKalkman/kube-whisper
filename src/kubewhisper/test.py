import sounddevice as sd
import numpy as np
import matplotlib.pyplot as plt


def callback(indata, frames, time, status):
    if status:
        print(f"Status: {status}")
    plt.plot(indata)
    plt.show()


try:
    with sd.InputStream(samplerate=16000, channels=1, callback=callback):
        print("Recording for 5 seconds...")
        sd.sleep(5000)
except Exception as e:
    print(f"Error: {e}")
