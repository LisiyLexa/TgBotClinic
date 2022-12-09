import logging
import string
import os
import subprocess
import requests

from aiogram import Bot, Dispatcher, executor, types

import speech_recognition as sr

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC, SVC
from sklearn.linear_model import LogisticRegression

from pymystem3 import Mystem
from random import choice

API_TOKEN = '***'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

alphabet = ' 1234567890-йцукенгшщзхъфывапролджэячсмитьбюёqwertyuiopasdfghjklzxcvbnm?%.,()!:;'

M = Mystem()

def diction_form(text):
    text = ''.join(M.lemmatize(text)).rstrip('\n')
    return text

def clean_str(r):
    r = r.lower()
    r = [c for c in r if c in alphabet]
    return ''.join(r)

def update():
    with open('dialogs.txt', encoding='utf-8') as f:
        content = f.read()

    blocks = content.split('\n')
    dataset = []

    for block in blocks:
        replicas = block.split('\\')[:2]
        if len(replicas) == 2:
            pair = [clean_str(replicas[0]), clean_str(replicas[1])]
            if pair[0] and pair[1]:
                dataset.append(pair)

    X_text = []
    y = []

    for question, answer in dataset[:10000]:
        X_text.append(diction_form(question))
        y += [answer]

    global vectorizer
    vectorizer = TfidfVectorizer(analyzer='char_wb',
                                 ngram_range=(2, 5),
                                 max_df=0.8)
    X = vectorizer.fit_transform(X_text)

    global clf
    clf = LogisticRegression()
    clf.fit(X, y)

update()

def remove_punctuation(text):
    translator = str.maketrans('', '', string.punctuation)
    return text.translate(translator)

def get_generative_replica(text):
    text = diction_form(text)
    text_vector = vectorizer.transform([text]).toarray()[0]
    test_q = max(clf.predict_proba([text_vector])[0])
    if test_q < 0.21:
        question = 'NoAnswer'
    else:
        question = clf.predict([text_vector])[0]
    return question

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("Здравствуйте! Что бы вы хотели узнать?")

question = ""

@dp.message_handler()
async def echo(message: types.Message):
    command = message.text.lower()
    global question
    question = command
    reply = get_generative_replica(command)
    if reply == 'записьнаприем':
        await message.reply("Запись на прием к врачу:\n☎ по телефону 8(***) **-**-**, +7-9**-***-**-** (без выходных)\n📱 WhatsApp +7 98******** https://**********.ru/запись-онлайн/\n\n📍С*********, ул.Э********, 116А.")
    elif reply == 'профиль' or reply == 'личныйкабинет':
        await message.reply('Ваш Профиль вы можете найти по ссылке:\nhttps://********.ru/login/')
    elif reply == 'цены':
        await message.reply('Цены представлены в таблице:')
        await bot.send_document(message.from_id, f'https://******.ru/wp-content/uploads/****/**/Прайс-*******-**.**.****.pdf')
    elif reply == 'NoAnswer':
        await message.reply(choice(["Извините, я вас не понял.", "Пожалуйста, скорректируйте ваш вопрос.", "Я не совсем вас понимаю."]))
        #await bot.send_message(message.from_id, "Перевожу на сотрудника поддержки...")
    else:
        await message.reply(reply)

@dp.message_handler(content_types=ContentType.VOICE)
async def get_audio_messages(message: types.Message):
    try:
        print("Started recognition...")
        file_info = bot.get_file(message.voice.file_id)
        path = os.path.splitext(file_info.file_path)[0]
        fname = os.path.basename(path) 
        doc = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(API_TOKEN, file_info.file_path))

        with open(fname + '.oga', 'wb') as f:
            f.write(doc.content)

        process = subprocess.run(['ffmpeg', '-i', fname + '.oga', fname + '.wav'])
        result = audio_to_text(fname+'.wav') 
        reply = get_generative_replica(format(result))

        await message.reply(reply)

    except sr.UnknownValueError as e:
        await bot.send_message(message.from_id,  "Не пон... А! А не, не пон...")

    except Exception as e:
        await bot.send_message(message.from_id,  "Ойойойой...")
    
    finally:
        os.remove(fname + '.wav')
        os.remove(fname + '.oga')
     

def audio_to_text(dest_name: str):
    r = sr.Recognizer()
    message = sr.AudioFile(dest_name)

    with message as source:
        audio = r.record(source)

    result = r.recognize_google(audio, language="ru_RU")
    return result


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
