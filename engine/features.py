import os
import sys
from shlex import quote
import re
import sqlite3
import struct
import subprocess
import time
import webbrowser
import eel
import pyaudio
import pyautogui
import pywhatkit as kit
import pvporcupine
from playsound import playsound
from hugchat import hugchat

# Ensure Python finds the 'engine' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.command import speak
from engine.config import ASSISTANT_NAME
from engine.helper import extract_yt_term, remove_words

# Database connection
con = sqlite3.connect("jarvis.db")
cursor = con.cursor()

@eel.expose
def playAssistantSound():
    music_dir = "www/assets/audio/start_sound.mp3"
    playsound(music_dir)

def openCommand(query):
    query = query.replace(ASSISTANT_NAME, "").replace("open", "").strip().lower()

    if query:
        try:
            cursor.execute('SELECT path FROM sys_command WHERE name = ?', (query,))
            results = cursor.fetchall()

            if results:
                speak("Opening " + query)
                os.startfile(results[0][0])
            else:
                cursor.execute('SELECT url FROM web_command WHERE name = ?', (query,))
                results = cursor.fetchall()

                if results:
                    speak("Opening " + query)
                    webbrowser.open(results[0][0])
                else:
                    speak("Opening " + query)
                    os.system(f'start {query}')
        except Exception as e:
            speak("Something went wrong: " + str(e))

def PlayYoutube(query):
    search_term = extract_yt_term(query)
    speak("Playing " + search_term + " on YouTube")
    kit.playonyt(search_term)

def hotword():
    porcupine = None
    paud = None
    audio_stream = None
    try:
        # Use Porcupine with an API key (replace 'YOUR_ACCESS_KEY' with your actual key)
        porcupine = pvporcupine.create(access_key="YOUR_ACCESS_KEY", keywords=["jarvis", "alexa"])
        paud = pyaudio.PyAudio()
        audio_stream = paud.open(
            rate=porcupine.sample_rate, channels=1,
            format=pyaudio.paInt16, input=True, frames_per_buffer=porcupine.frame_length
        )

        while True:
            keyword = audio_stream.read(porcupine.frame_length)
            keyword = struct.unpack_from("h" * porcupine.frame_length, keyword)
            keyword_index = porcupine.process(keyword)

            if keyword_index >= 0:
                print("Hotword detected")
                pyautogui.hotkey("win", "j")
                time.sleep(2)
    except Exception as e:
        print("Error in hotword detection:", e)
    finally:
        if porcupine:
            porcupine.delete()
        if audio_stream:
            audio_stream.close()
        if paud:
            paud.terminate()

def findContact(query):
    words_to_remove = [ASSISTANT_NAME, 'make', 'a', 'to', 'phone', 'call', 'send', 'message', 'whatsapp', 'video']
    query = remove_words(query, words_to_remove).strip().lower()

    try:
        cursor.execute("SELECT mobile_no FROM contacts WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?", ('%' + query + '%', query + '%'))
        results = cursor.fetchall()

        if results:
            mobile_number_str = str(results[0][0])
            if not mobile_number_str.startswith('+91'):
                mobile_number_str = '+91' + mobile_number_str
            return mobile_number_str, query
        else:
            speak("Contact not found")
            return None, None
    except Exception as e:
        speak("Error finding contact: " + str(e))
        return None, None

def whatsApp(mobile_no, message, flag, name):
    if flag == 'message':
        jarvis_message = "Message sent successfully to " + name
    elif flag == 'call':
        message = ''
        jarvis_message = "Calling " + name
    else:
        message = ''
        jarvis_message = "Starting video call with " + name

    encoded_message = quote(message)
    whatsapp_url = f"https://api.whatsapp.com/send?phone={mobile_no}&text={encoded_message}"
    
    # Open WhatsApp via web browser (works on all devices)
    webbrowser.open(whatsapp_url)

    speak(jarvis_message)

def chatBot(query):
    try:
        chatbot = hugchat.ChatBot(cookie_path="engine/cookies.json")  # Fixed file path
        id = chatbot.new_conversation()
        chatbot.change_conversation(id)
        response = chatbot.chat(query.lower())
        print(response)
        speak(response)
        return response
    except Exception as e:
        print("Chatbot error:", e)
        speak("I'm having trouble processing that request.")
        return ""

def makeCall(name, mobileNo):
    mobileNo = mobileNo.replace(" ", "")
    speak("Calling " + name)
    command = f'adb shell am start -a android.intent.action.CALL -d tel:{mobileNo}'
    os.system(command)

def sendMessage(message, mobileNo, name):
    from engine.helper import replace_spaces_with_percent_s, goback, keyEvent, tapEvents, adbInput

    message = replace_spaces_with_percent_s(message)
    mobileNo = replace_spaces_with_percent_s(mobileNo)
    speak("Sending message")
    
    goback(4)
    time.sleep(1)
    keyEvent(3)

    tapEvents(136, 2220)  # Open SMS app
    tapEvents(819, 2192)  # Start chat
    adbInput(mobileNo)  # Enter mobile number
    tapEvents(601, 574)  # Select contact
    tapEvents(390, 2270)  # Tap input field
    adbInput(message)  # Enter message
    tapEvents(957, 1397)  # Send message

    speak("Message sent successfully to " + name)
