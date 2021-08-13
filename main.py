from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaDocument
from aiogram.utils import executor
from telegram_bot_calendar import LSTEP, WMonthTelegramCalendar
from utils import UserStates
import threading
import time
import io
import datetime
from urllib.request import urlopen
import json
import sqlite3

TOKEN = '1931110131:AAHr3e9d0d_04URAnHs-v69pej5E65_AZzs'

admin_id = 951299049
config_id = 99

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

user_state = {}

conn = sqlite3.connect(":memory:")  # или :memory: чтобы сохранить в RAM
cursor = conn.cursor()
cursor.execute("CREATE TABLE users (chatid INTEGER , name TEXT, date INTEGER, timestart INTEGER, timeend INTEGER)")


class User:
    def __init__(self):
        self.date = 'None'
        self.fullname = 'None'
        self.timestart = None
        self.timeend = None


# #--------------------Получение данных-------------------------
async def get_data():
    to = time.time()
    # Пересылаем сообщение в данными от админа к админу
    forward_data = await bot.forward_message(admin_id, admin_id, config_id)

    # Получаем путь к файлу, который переслали
    file_data = await bot.get_file(forward_data.document.file_id)

    # Получаем файл по url
    file_url_data = bot.get_file_url(file_data.file_path)

    # Считываем данные с файла
    json_file = urlopen(file_url_data).read()
    print('Время получения бекапа :=' + str(time.time() - to))
    # Переводим данные из json в словарь и возвращаем
    return json.loads(json_file)


# --------------------Сохранение данных-------------------------
async def save_data():
    to = time.time()
    sql = "SELECT * FROM users "
    cursor.execute(sql)
    data = cursor.fetchall()  # or use fetchone()
    try:
        # Переводим словарь в строку
        str_data = json.dumps(data)

        # Обновляем  наш файл с данными
        await bot.edit_message_media(InputMediaDocument(io.StringIO(str_data)), admin_id, config_id)

    except Exception as ex:
        print(ex)
    print('Время сохранения бекапа:=' + str(time.time() - to))

#------------------------------Кнопка расписание-----------------------------------------

@dp.callback_query_handler(lambda c: c.data == 'buttontime', state=UserStates.USER_STATE_0)
async def process_callback_button1(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, 'Вы выбрали посмотреть расписание')

#------------------------------Кнопка запись------------------------------------------------

@dp.callback_query_handler(lambda c: c.data == 'buttonzapis', state=UserStates.USER_STATE_0)
async def process_callback_button2(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    state = dp.current_state(user=callback_query.from_user.id)
    await state.set_state(UserStates.all()[1])
    await bot.send_message(callback_query.from_user.id, 'Введите ФИО.', )

# -------------------Выбор даты первый раз------------------------------------------------

@dp.callback_query_handler(WMonthTelegramCalendar.func(), state=UserStates.USER_STATE_2)
async def inline_kb_answer_callback_handler(query):
    result, key, step = WMonthTelegramCalendar().process(query.data)

    if not result and key:
        await bot.edit_message_text(f"📅 Выберите день",
                                    query.message.chat.id,
                                    query.message.message_id,
                                    reply_markup=key)
    elif result:
        today = int(datetime.datetime.now().strftime("%Y%m%d"))
        resultInt = int(str(result).replace("-", ""))
        if resultInt >= today:
            userC = user_state[query.from_user.id]
            userC.date = resultInt
            state = dp.current_state(user=query.from_user.id)

            await state.set_state(UserStates.all()[3])
            await bot.send_message(query.from_user.id, f"Вы выбрали {result} \n Теперь введите час начала. В формате 24ч. ⏰")
        else:
            await bot.send_message(query.from_user.id, "❌ Выбрана некорректная дата ❌")
            calendar, step = WMonthTelegramCalendar().build()
            await bot.send_message(query.from_user.id, "📅 Выберите день:", reply_markup=calendar)

@dp.message_handler(commands=['1'], state='*')
async def start(message):
    sql = "SELECT * FROM users "
    cursor.execute(sql)
    data = cursor.fetchall()
    str_data = json.dumps(data)
    await bot.send_message(message.from_user.id, str_data)


@dp.message_handler(commands=['start'],state='*')
async def process_start_command(message: types.Message):
    state = dp.current_state(user=message.from_user.id)
    await state.set_state(UserStates.all()[0])
    button = InlineKeyboardButton('Посмотерть рассписание 📅', callback_data='buttontime')
    button2 = InlineKeyboardButton('Записаться 📝', callback_data='buttonzapis')
    kb = InlineKeyboardMarkup().add(button).add(button2)
    await bot.send_message(message.from_user.id,
                           "Здравствуйте! 👋\nЭто бот-расписание БНП для автомобиля!\nВыберите, что вы хотите сделать.",
                           reply_markup=kb)


@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    await bot.send_message(message.from_user.id, "Здравствуйте! 👋\nЭто бот-расписание БНП для автомобиля!\n ")

#------------Последний этап, выбор окончания аренды, запись в базу, проверки --------------------------

@dp.message_handler(state=UserStates.USER_STATE_4)
async def first_test_state_case_met(message: types.Message):
    userC = user_state[message.from_user.id]
    if userC.timestart < message.text and int(message.text) > 0 and int(message.text) < 25:
        userC.timeend = message.text
        sql_check = "SELECT * FROM users where date={}".format(userC.date)
        cursor.execute(sql_check)
        newlist = cursor.fetchall()
        dbg = ''.join(str(e) for e in newlist)
        print('DBG newlist' + dbg + ' ' + str(userC.date))
        checkpoint = False
        for elem in newlist:
            i = elem[3]
            print('DBG elem ' + str(i))
            while i <= elem[4]:
                print('DBG elem ' + str(i))
                if str(i) == str(userC.timestart) or str(i) == str(userC.timeend):
                    await message.reply('Извините время занято с ' + str(elem[3]) + ' до ' + str(elem[4]) + '\nЭтим человеком -' + elem[1], reply=False)
                    checkpoint = True
                    break
                else:
                    i = i + 1
        if checkpoint == False:
            sql_insert = "INSERT INTO users VALUES ('{}', '{}', '{}', '{}','{}')".format(message.from_user.id, userC.fullname,
                                                                                   userC.date, userC.timestart,
                                                                                   userC.timeend)
            cursor.execute(sql_insert)
            state = dp.current_state(user=message.from_user.id)
            dateOut = str(userC.date)
            dateOut = dateOut[:4] + '-' + dateOut[4:6] + '-' + dateOut[6:]
            await state.set_state(UserStates.all()[0])
            await message.reply('{}, вы записаны {} c {} до {}'.format(userC.fullname, dateOut, userC.timestart, userC.timeend), reply=False)

        elif checkpoint == True:
            button = InlineKeyboardButton('Сменить дату 📅', callback_data='buttondatehange')
            button2 = InlineKeyboardButton('Сменить время ⏰', callback_data='buttontimechange')
            kb = InlineKeyboardMarkup().add(button).add(button2)
            await bot.send_message(message.from_user.id,
                                   "Что вы хотите поменять?",
                                   reply_markup=kb)
    else:
        await message.reply('❗ Час окончания не может быть меньше или равен часу начала. ❗'
                            '\n❗ Введите час окончания в формате 24ч. ❗', reply=False)

@dp.callback_query_handler(lambda c: c.data == 'buttontimechange', state=UserStates.USER_STATE_4)
async def process_callback_button2(callback_query: types.CallbackQuery):
    userC = user_state[callback_query.from_user.id]
    userC.timeend = None
    userC.timestart = None
    state = dp.current_state(user=callback_query.from_user.id)
    await state.set_state(UserStates.all()[3])
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, 'Введите час начала в формате 24ч. ⏰', )

@dp.callback_query_handler(lambda c: c.data == 'buttondatehange', state=UserStates.USER_STATE_4)
async def process_callback_button2(callback_query: types.CallbackQuery):
    userC = user_state[callback_query.from_user.id]
    userC.timeend = None
    userC.timestart = None
    userC.date = None
    state = dp.current_state(user=callback_query.from_user.id)
    await state.set_state(UserStates.all()[2])
    await bot.send_message(callback_query.from_user.id, 'Выберите дату 📅')
    calendar, step = WMonthTelegramCalendar().build()
    await bot.send_message(callback_query.from_user.id, "Выберите день:", reply_markup=calendar)


#--------------Ввод часа начала-----------------------------------------------------------
@dp.message_handler(state=UserStates.USER_STATE_3)
async def first_test_state_case_met(message: types.Message):
    userC = user_state[message.from_user.id]
    if int(message.text) > 0 and int(message.text) < 25:
        userC.timestart = message.text
        state = dp.current_state(user=message.from_user.id)
        await state.set_state(UserStates.all()[4])
        await message.reply('Спасибо, теперь, выберите час окончания в формате 24ч. ⏰', reply=False)
    else:
        await message.reply('❗ Введите, пожалуйста время в формате 24ч. ❗', reply=False)


@dp.message_handler(state=UserStates.USER_STATE_1)
async def first_test_state_case_met(message: types.Message):
    user_state[message.from_user.id] = User()
    userC = user_state[message.from_user.id]
    userC.fullname = message.text
    state = dp.current_state(user=message.from_user.id)
    await state.set_state(UserStates.all()[2])
    await message.reply('Спасибо, ' + message.text + '\nТеперь, выберите дату 📅', reply=False)
    calendar, step = WMonthTelegramCalendar().build()
    await bot.send_message(message.chat.id, "Выберите день:", reply_markup=calendar)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
