"""
Based on the basic speech recognition script bundled with the module speech_recognition

_REQUIRES_ <=Python3.6. I could not get PyAudio to work with Python3.7
"""

import speech_recognition
from functools import partial
import sys
import json
from pynput import keyboard

DEBUG = True
MAX_ENERGY_THRESHOLD = 75
FILE_NAME = "alexa"
TRIGGER_KEY = "*"

def log(msg: str) -> None:
    if DEBUG:
        print(msg)

r = speech_recognition.Recognizer()
m = speech_recognition.Microphone()

def do_recognize() -> None:
    #while True:
    log("Say something!")
    with m as source: audio = r.listen(source)
    log("Got it! Now to recognize it...")
    try:
        # recognize speech using Google Speech Recognition
        value = r.recognize_google(audio)
        value = value.lower()
        try:
            action, member, *_ = value.split(" ")
        except:
            pass
        else:
            # save speech command to file
            with open("{}.json".format(FILE_NAME), "w") as f:
                json.dump((action, member), f)
        print("You said {}".format(value))
    except speech_recognition.UnknownValueError:
        log("Oops! Didn't catch that")
    except speech_recognition.RequestError as e:
        log("Uh oh! Couldn't request results from Google Speech Recognition service; {0}".format(e))

def on_press(key):
    try:
        if key.char == TRIGGER_KEY:
            do_recognize()
        log('alphanumeric key {0} pressed'.format(key.char))
    except AttributeError:
        log('special key {0} pressed'.format(key))

def on_release(key):
    if key == keyboard.Key.esc:
        # Stop listener
        return False

def setup() -> None:
    log("A moment of silence, please...")
    while r.energy_threshold > MAX_ENERGY_THRESHOLD:
        with m as source: r.adjust_for_ambient_noise(source) # calibrate ambient noise level
    log("Set minimum energy threshold to {}".format(r.energy_threshold))

if __name__ == "__main__":
    setup()
    with keyboard.Listener(on_press=on_press,on_release=on_release) as listener:
        listener.join()