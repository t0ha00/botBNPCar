import asyncio

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaDocument
from aiogram.utils.callback_data import CallbackData
from aiogram.utils import executor
from telegram_bot_calendar import LSTEP, WMonthTelegramCalendar
from utils import UserStates
import prettytable as pt
import xlsxwriter
import threading
import time
import io
import datetime
from urllib.request import urlopen
import json
import sqlite3

TOKEN = '1931110131:AAHr3e9d0d_04URAnHs-v69pej5E65_AZzs'
DEF_ARR_TIMES = ['9:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00']

admin_id = 951299049
config_id = 99

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

conn = sqlite3.connect(":memory:")  # или :memory: чтобы сохранить в RAM
cursor = conn.cursor()
cursor.execute(
    "CREATE TABLE users (chatid INTEGER , name TEXT, date INTEGER, timestart INTEGER, timeend INTEGER, id INTEGER PRIMARY KEY)")


class User:
    def __init__(self):
        self.date = None
        self.fullname = None
        self.timestart = None
        self.timeend = None


arr_times = ['9:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00']
user_state = {}
callback_del = CallbackData("delbtn", "action", "id")


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


# ------------------------------Кнопка расписание-----------------------------------------

# -----------------------------Выбор нужного расписания----------------------------------

@dp.callback_query_handler(lambda c: c.data == 'buttontime', state=UserStates.USER_STATE_0)
async def process_callback_button1(callback_query: types.CallbackQuery):
    state = dp.current_state(user=callback_query.from_user.id)
    await state.set_state(UserStates.all()[5])
    markup = types.InlineKeyboardMarkup(row_width=3)
    button = [types.InlineKeyboardButton(text='Отчет по имени', callback_data='table_name'),
              types.InlineKeyboardButton(text='Отчет по дате', callback_data='table_date'),
              types.InlineKeyboardButton(text='Полный отчет', callback_data='table_full')]
    markup.add(*button)
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, 'Какой отчет нужен ?', reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == 'table_name', state=UserStates.USER_STATE_TABLE_0)
async def process_callback_button1(callback_query: types.CallbackQuery):
    state = dp.current_state(user=callback_query.from_user.id)
    await state.set_state(UserStates.all()[6])
    markup = types.InlineKeyboardMarkup(row_width=3)
    button = [types.InlineKeyboardButton(text='Файлом 📄', callback_data='file_name'),
              types.InlineKeyboardButton(text='Сообщением 📨', callback_data='message_name')]
    markup.add(*button)
    await bot.send_message(callback_query.from_user.id, 'Выберите как хотите получаить отчет', reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == 'file_name', state=UserStates.USER_STATE_TABLE_1, )
async def process_callback_button1(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    state = dp.current_state(user=callback_query.from_user.id)
    await state.set_state(UserStates.all()[7])
    await bot.send_message(callback_query.from_user.id, 'Введите ФИО.')


@dp.callback_query_handler(lambda c: c.data == 'message_name', state=UserStates.USER_STATE_TABLE_1, )
async def process_callback_button1(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    state = dp.current_state(user=callback_query.from_user.id)
    await state.set_state(UserStates.all()[8])
    await bot.send_message(callback_query.from_user.id, 'Введите ФИО.')


@dp.message_handler(state=UserStates.USER_STATE_TABLE_2)
async def process_callback_button1(message: types.Message):
    name = '\"' + message.text + '\"'
    sql_select = "SELECT * FROM users where name={} ORDER BY date DESC".format(name)
    cursor.execute(sql_select)
    resultlist = cursor.fetchall()
    state = dp.current_state(user=message.from_user.id)
    await state.set_state(UserStates.all()[0])
    if not resultlist:
        await bot.send_message(message.from_user.id, 'Пустая таблица')
    else:
        workbook = xlsxwriter.Workbook(message.text + '.xlsx')
        worksheet = workbook.add_worksheet()
        worksheet.write(0, 0, 'Дата')
        worksheet.write(0, 1, 'Время')
        count = 1
        for elem in resultlist:
            dateOut = str(elem[2])
            dateOut = dateOut[:4] + '-' + dateOut[4:6] + '-' + dateOut[6:]
            worksheet.write(count, 0, dateOut)
            worksheet.write(count, 1, 'c ' + DEF_ARR_TIMES[elem[3]] + ' до ' + DEF_ARR_TIMES[elem[4]])
            count += 1
        workbook.close()
        f = open('./' + message.text + '.xlsx', 'rb')
        await bot.send_document(message.from_user.id, f)


@dp.message_handler(state=UserStates.USER_STATE_TABLE_3)
async def process_callback_button1(message: types.message):
    name = '\"' + message.text + '\"'
    sql_select = "SELECT * FROM users where name={} ORDER BY date DESC".format(name)
    cursor.execute(sql_select)
    resultlist = cursor.fetchall()
    state = dp.current_state(user=message.from_user.id)
    await state.set_state(UserStates.all()[0])
    if not resultlist:
        await bot.send_message(message.from_user.id, 'Пустая таблица')
    else:
        table = pt.PrettyTable(["Дата", "Время"])
        for elem in resultlist:
            dateOut = str(elem[2])
            dateOut = dateOut[:4] + '-' + dateOut[4:6] + '-' + dateOut[6:]
            table.add_row([dateOut, 'c ' + DEF_ARR_TIMES[elem[3]] + ' до ' + DEF_ARR_TIMES[elem[4]]])
        await bot.send_message(message.from_user.id, f'<pre>{table}</pre>', parse_mode='html')


@dp.callback_query_handler(lambda c: c.data == 'table_date', state=UserStates.USER_STATE_TABLE_0)
async def process_callback_button1(callback_query: types.CallbackQuery):
    state = dp.current_state(user=callback_query.from_user.id)
    await state.set_state(UserStates.all()[9])
    markup = types.InlineKeyboardMarkup(row_width=3)
    button = [types.InlineKeyboardButton(text='Файлом 📄', callback_data='file_date'),
              types.InlineKeyboardButton(text='Сообщением 📨', callback_data='message_date')]
    markup.add(*button)
    await bot.send_message(callback_query.from_user.id, 'Выберите как хотите получаить отчет', reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == 'file_date', state=UserStates.USER_STATE_TABLE_4, )
async def process_callback_button1(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    state = dp.current_state(user=callback_query.from_user.id)
    await state.set_state(UserStates.all()[10])
    calendar, step = WMonthTelegramCalendar().build()
    await bot.send_message(callback_query.from_user.id, 'Выберите дату', reply_markup=calendar)


@dp.callback_query_handler(lambda c: c.data == 'message_date', state=UserStates.USER_STATE_TABLE_4, )
async def process_callback_button1(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    state = dp.current_state(user=callback_query.from_user.id)
    await state.set_state(UserStates.all()[11])
    calendar, step = WMonthTelegramCalendar().build()
    await bot.send_message(callback_query.from_user.id, 'Выберите дату', reply_markup=calendar)


@dp.callback_query_handler(WMonthTelegramCalendar.func(), state=UserStates.USER_STATE_TABLE_5)
async def process_callback_button1(callback_query: types.CallbackQuery):
    result, key, step = WMonthTelegramCalendar().process(callback_query.data)
    if not result and key:
        await bot.edit_message_text(f"📅 Выберите день",
                                    callback_query.message.chat.id,
                                    callback_query.message.message_id,
                                    reply_markup=key)
    elif result:
        resultInt = int(str(result).replace("-", ""))
        sql_check = "SELECT * FROM users where date={}".format(resultInt)
        cursor.execute(sql_check)
        resultlist = cursor.fetchall()
        state = dp.current_state(user=callback_query.from_user.id)
        await state.set_state(UserStates.all()[0])
        if not resultlist:
            await bot.answer_callback_query(callback_query.id)
            await bot.send_message(callback_query.from_user.id, 'Пустая таблица')
        else:
            workbook = xlsxwriter.Workbook(str(result) + '.xlsx')
            worksheet = workbook.add_worksheet()
            worksheet.write(0, 0, 'Имя')
            worksheet.write(0, 1, 'Время')
            count = 1
            for elem in resultlist:
                worksheet.write(count, 0, elem[1])
                worksheet.write(count, 1, 'c ' + DEF_ARR_TIMES[elem[3]] + ' до ' + DEF_ARR_TIMES[elem[4]])
                count += 1
            workbook.close()
            f = open('./' + str(result) + '.xlsx', 'rb')
            await bot.send_document(callback_query.from_user.id, f)


@dp.callback_query_handler(WMonthTelegramCalendar.func(), state=UserStates.USER_STATE_TABLE_6)
async def process_callback_button1(callback_query: types.CallbackQuery):
    result, key, step = WMonthTelegramCalendar().process(callback_query.data)
    if not result and key:
        await bot.edit_message_text(f"📅 Выберите день",
                                    callback_query.message.chat.id,
                                    callback_query.message.message_id,
                                    reply_markup=key)
    elif result:
        resultInt = int(str(result).replace("-", ""))
        sql_check = "SELECT * FROM users where date={} ORDER BY date DESC".format(resultInt)
        cursor.execute(sql_check)
        resultlist = cursor.fetchall()
        state = dp.current_state(user=callback_query.from_user.id)
        await state.set_state(UserStates.all()[0])
        if not resultlist:
            await bot.answer_callback_query(callback_query.id)
            await bot.send_message(callback_query.from_user.id, 'Пустая таблица')
        else:
            table = pt.PrettyTable(["Имя", "Время"])
            for elem in resultlist:
                table.add_row([elem[1], 'c ' + DEF_ARR_TIMES[elem[3]] + ' до ' + DEF_ARR_TIMES[elem[4]]])
            await bot.answer_callback_query(callback_query.id)
            await bot.send_message(callback_query.from_user.id, f'<pre>{table}</pre>', parse_mode='html')


@dp.callback_query_handler(lambda c: c.data == 'table_full', state=UserStates.USER_STATE_TABLE_0)
async def process_callback_button1(callback_query: types.CallbackQuery):
    state = dp.current_state(user=callback_query.from_user.id)
    await state.set_state(UserStates.all()[12])
    markup = types.InlineKeyboardMarkup(row_width=3)
    button = [types.InlineKeyboardButton(text='Файлом 📄', callback_data='file_full'),
              types.InlineKeyboardButton(text='Сообщением 📨', callback_data='message_full')]
    markup.add(*button)
    await bot.send_message(callback_query.from_user.id, 'Выберите как хотите получаить отчет', reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == 'file_full', state=UserStates.USER_STATE_TABLE_7)
async def process_callback_button1(callback_query: types.CallbackQuery):
    sql_check = "SELECT * FROM users ORDER BY date DESC"
    cursor.execute(sql_check)
    resultlist = cursor.fetchall()
    if not resultlist:
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, 'Пустая таблица')
    else:
        workbook = xlsxwriter.Workbook('full.xlsx')
        worksheet = workbook.add_worksheet()
        worksheet.write(0, 0, 'Дата')
        worksheet.write(0, 1, 'Имя')
        worksheet.write(0, 2, 'Время')
        count = 1
        for elem in resultlist:
            dateOut = str(elem[2])
            dateOut = dateOut[:4] + '-' + dateOut[4:6] + '-' + dateOut[6:]
            worksheet.write(count, 0, dateOut)
            worksheet.write(count, 1, elem[1])
            worksheet.write(count, 2, 'c ' + DEF_ARR_TIMES[elem[3]] + ' до ' + DEF_ARR_TIMES[elem[4]])
            count += 1
        workbook.close()
        f = open('./full.xlsx', 'rb')
        await bot.send_document(callback_query.from_user.id, f)


@dp.callback_query_handler(lambda c: c.data == 'message_full', state=UserStates.USER_STATE_TABLE_7)
async def process_callback_button1(callback_query: types.CallbackQuery):
    sql_check = "SELECT * FROM users ORDER BY date DESC"
    cursor.execute(sql_check)
    resultlist = cursor.fetchall()
    if not resultlist:
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, 'Пустая таблица')
    else:
        table = pt.PrettyTable(["Имя", "Дата", "Время"])
        for elem in resultlist:
            dateOut = str(elem[2])
            dateOut = dateOut[:4] + '-' + dateOut[4:6] + '-' + dateOut[6:]
            table.add_row([elem[1], dateOut, 'c ' + DEF_ARR_TIMES[elem[3]] + ' до ' + DEF_ARR_TIMES[elem[4]]])
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, f'<pre>{table}</pre>', parse_mode='html')


# ------------------------------Кнопка запись------------------------------------------------

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
    arr_times = ['9:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '❌']
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

            sql_check = "SELECT * FROM users where date={}".format(userC.date)
            cursor.execute(sql_check)
            newlist = cursor.fetchall()
            markup = types.InlineKeyboardMarkup(row_width=3)
            if not newlist:
                print("Здесь пусто")
            else:
                for ellist in newlist:
                    for i in range(int(ellist[3]), int(ellist[4])):
                        arr_times[i] = '❌'

            button = [types.InlineKeyboardButton(text=arr_times[0], callback_data=arr_times[0]),
                      types.InlineKeyboardButton(text=arr_times[1], callback_data=arr_times[1]),
                      types.InlineKeyboardButton(text=arr_times[2], callback_data=arr_times[2]),
                      types.InlineKeyboardButton(text=arr_times[3], callback_data=arr_times[3]),
                      types.InlineKeyboardButton(text=arr_times[4], callback_data=arr_times[4]),
                      types.InlineKeyboardButton(text=arr_times[5], callback_data=arr_times[5]),
                      types.InlineKeyboardButton(text=arr_times[6], callback_data=arr_times[6]),
                      types.InlineKeyboardButton(text=arr_times[7], callback_data=arr_times[7]),
                      types.InlineKeyboardButton(text=arr_times[8], callback_data=arr_times[8])]
            markup.add(*button)
            await state.set_state(UserStates.all()[3])
            await bot.send_message(query.from_user.id, f"Вы выбрали {result} \nТеперь выберите час начала. ⏰",
                                   reply_markup=markup)
        else:
            await bot.send_message(query.from_user.id, "❌ Выбрана некорректная дата ❌")
            calendar, step = WMonthTelegramCalendar().build()
            await bot.send_message(query.from_user.id, "📅 Выберите день:", reply_markup=calendar)


# -----------------------------Запретная кнопка-----------------------------------------------

@dp.callback_query_handler(lambda c: c.data == '❌', state='*')
async def first_test_state_case_met(message: types.Message):
    arr_times = ['9:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '❌']
    userC = user_state[message.from_user.id]
    sql_check = "SELECT * FROM users where date={}".format(userC.date)
    cursor.execute(sql_check)
    newlist = cursor.fetchall()
    for ellist in newlist:
        for i in range(int(ellist[3]), int(ellist[4])):
            arr_times[i] = '❌'
    markup = types.InlineKeyboardMarkup(row_width=3)
    button = [types.InlineKeyboardButton(text=arr_times[0], callback_data=arr_times[0]),
              types.InlineKeyboardButton(text=arr_times[1], callback_data=arr_times[1]),
              types.InlineKeyboardButton(text=arr_times[2], callback_data=arr_times[2]),
              types.InlineKeyboardButton(text=arr_times[3], callback_data=arr_times[3]),
              types.InlineKeyboardButton(text=arr_times[4], callback_data=arr_times[4]),
              types.InlineKeyboardButton(text=arr_times[5], callback_data=arr_times[5]),
              types.InlineKeyboardButton(text=arr_times[6], callback_data=arr_times[6]),
              types.InlineKeyboardButton(text=arr_times[7], callback_data=arr_times[7]),
              types.InlineKeyboardButton(text=arr_times[8], callback_data=arr_times[8])]
    markup.add(*button)
    await bot.send_message(message.from_user.id, '❗ Нельзя выбирать эту кнопку она же красная ❗',
                           reply_markup=markup)


# --------------Ввод часа начала-----------------------------------------------------------
@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[0], state=UserStates.USER_STATE_3)
async def first_test_state_case_met(message: types.Message):
    arr_times[0] = '❌'
    arr_times[8] = '17:00'
    userC = user_state[message.from_user.id]
    userC.timestart = 0
    state = dp.current_state(user=message.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=3)
    button = [types.InlineKeyboardButton(text=arr_times[0], callback_data=arr_times[0]),
              types.InlineKeyboardButton(text=arr_times[1], callback_data=arr_times[1]),
              types.InlineKeyboardButton(text=arr_times[2], callback_data=arr_times[2]),
              types.InlineKeyboardButton(text=arr_times[3], callback_data=arr_times[3]),
              types.InlineKeyboardButton(text=arr_times[4], callback_data=arr_times[4]),
              types.InlineKeyboardButton(text=arr_times[5], callback_data=arr_times[5]),
              types.InlineKeyboardButton(text=arr_times[6], callback_data=arr_times[6]),
              types.InlineKeyboardButton(text=arr_times[7], callback_data=arr_times[7]),
              types.InlineKeyboardButton(text=arr_times[8], callback_data=arr_times[8])]
    markup.add(*button)
    await state.set_state(UserStates.all()[4])
    await bot.send_message(message.from_user.id, 'Спасибо, теперь, выберите час окончания в формате 24ч. ⏰',
                           reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[1], state=UserStates.USER_STATE_3)
async def first_test_state_case_met(message: types.Message):
    arr_times[0] = '❌'
    arr_times[1] = '❌'
    arr_times[8] = '17:00'
    userC = user_state[message.from_user.id]
    userC.timestart = 1
    state = dp.current_state(user=message.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=3)
    button = [types.InlineKeyboardButton(text=arr_times[0], callback_data=arr_times[0]),
              types.InlineKeyboardButton(text=arr_times[1], callback_data=arr_times[1]),
              types.InlineKeyboardButton(text=arr_times[2], callback_data=arr_times[2]),
              types.InlineKeyboardButton(text=arr_times[3], callback_data=arr_times[3]),
              types.InlineKeyboardButton(text=arr_times[4], callback_data=arr_times[4]),
              types.InlineKeyboardButton(text=arr_times[5], callback_data=arr_times[5]),
              types.InlineKeyboardButton(text=arr_times[6], callback_data=arr_times[6]),
              types.InlineKeyboardButton(text=arr_times[7], callback_data=arr_times[7]),
              types.InlineKeyboardButton(text=arr_times[8], callback_data=arr_times[8])]
    markup.add(*button)
    await state.set_state(UserStates.all()[4])
    await bot.send_message(message.from_user.id, 'Спасибо, теперь, выберите час окончания в формате 24ч. ⏰',
                           reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[2], state=UserStates.USER_STATE_3)
async def first_test_state_case_met(message: types.Message):
    arr_times[0] = '❌'
    arr_times[1] = '❌'
    arr_times[2] = '❌'
    arr_times[8] = '17:00'
    userC = user_state[message.from_user.id]
    userC.timestart = 2
    state = dp.current_state(user=message.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=3)
    button = [types.InlineKeyboardButton(text=arr_times[0], callback_data=arr_times[0]),
              types.InlineKeyboardButton(text=arr_times[1], callback_data=arr_times[1]),
              types.InlineKeyboardButton(text=arr_times[2], callback_data=arr_times[2]),
              types.InlineKeyboardButton(text=arr_times[3], callback_data=arr_times[3]),
              types.InlineKeyboardButton(text=arr_times[4], callback_data=arr_times[4]),
              types.InlineKeyboardButton(text=arr_times[5], callback_data=arr_times[5]),
              types.InlineKeyboardButton(text=arr_times[6], callback_data=arr_times[6]),
              types.InlineKeyboardButton(text=arr_times[7], callback_data=arr_times[7]),
              types.InlineKeyboardButton(text=arr_times[8], callback_data=arr_times[8])]
    markup.add(*button)
    await state.set_state(UserStates.all()[4])
    await bot.send_message(message.from_user.id, 'Спасибо, теперь, выберите час окончания в формате 24ч. ⏰',
                           reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[3], state=UserStates.USER_STATE_3)
async def first_test_state_case_met(message: types.Message):
    arr_times[0] = '❌'
    arr_times[1] = '❌'
    arr_times[2] = '❌'
    arr_times[3] = '❌'
    arr_times[8] = '17:00'
    userC = user_state[message.from_user.id]
    userC.timestart = 3
    state = dp.current_state(user=message.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=3)
    button = [types.InlineKeyboardButton(text=arr_times[0], callback_data=arr_times[0]),
              types.InlineKeyboardButton(text=arr_times[1], callback_data=arr_times[1]),
              types.InlineKeyboardButton(text=arr_times[2], callback_data=arr_times[2]),
              types.InlineKeyboardButton(text=arr_times[3], callback_data=arr_times[3]),
              types.InlineKeyboardButton(text=arr_times[4], callback_data=arr_times[4]),
              types.InlineKeyboardButton(text=arr_times[5], callback_data=arr_times[5]),
              types.InlineKeyboardButton(text=arr_times[6], callback_data=arr_times[6]),
              types.InlineKeyboardButton(text=arr_times[7], callback_data=arr_times[7]),
              types.InlineKeyboardButton(text=arr_times[8], callback_data=arr_times[8])]
    markup.add(*button)
    await state.set_state(UserStates.all()[4])
    await bot.send_message(message.from_user.id, 'Спасибо, теперь, выберите час окончания в формате 24ч. ⏰',
                           reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[4], state=UserStates.USER_STATE_3)
async def first_test_state_case_met(message: types.Message):
    arr_times[0] = '❌'
    arr_times[1] = '❌'
    arr_times[2] = '❌'
    arr_times[3] = '❌'
    arr_times[4] = '❌'
    arr_times[8] = '17:00'
    userC = user_state[message.from_user.id]
    userC.timestart = 4
    state = dp.current_state(user=message.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=3)
    button = [types.InlineKeyboardButton(text=arr_times[0], callback_data=arr_times[0]),
              types.InlineKeyboardButton(text=arr_times[1], callback_data=arr_times[1]),
              types.InlineKeyboardButton(text=arr_times[2], callback_data=arr_times[2]),
              types.InlineKeyboardButton(text=arr_times[3], callback_data=arr_times[3]),
              types.InlineKeyboardButton(text=arr_times[4], callback_data=arr_times[4]),
              types.InlineKeyboardButton(text=arr_times[5], callback_data=arr_times[5]),
              types.InlineKeyboardButton(text=arr_times[6], callback_data=arr_times[6]),
              types.InlineKeyboardButton(text=arr_times[7], callback_data=arr_times[7]),
              types.InlineKeyboardButton(text=arr_times[8], callback_data=arr_times[8])]
    markup.add(*button)
    await state.set_state(UserStates.all()[4])
    await bot.send_message(message.from_user.id, 'Спасибо, теперь, выберите час окончания в формате 24ч. ⏰',
                           reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[5], state=UserStates.USER_STATE_3)
async def first_test_state_case_met(message: types.Message):
    arr_times[0] = '❌'
    arr_times[1] = '❌'
    arr_times[2] = '❌'
    arr_times[3] = '❌'
    arr_times[4] = '❌'
    arr_times[5] = '❌'
    arr_times[8] = '17:00'
    userC = user_state[message.from_user.id]
    userC.timestart = 5
    state = dp.current_state(user=message.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=3)
    button = [types.InlineKeyboardButton(text=arr_times[0], callback_data=arr_times[0]),
              types.InlineKeyboardButton(text=arr_times[1], callback_data=arr_times[1]),
              types.InlineKeyboardButton(text=arr_times[2], callback_data=arr_times[2]),
              types.InlineKeyboardButton(text=arr_times[3], callback_data=arr_times[3]),
              types.InlineKeyboardButton(text=arr_times[4], callback_data=arr_times[4]),
              types.InlineKeyboardButton(text=arr_times[5], callback_data=arr_times[5]),
              types.InlineKeyboardButton(text=arr_times[6], callback_data=arr_times[6]),
              types.InlineKeyboardButton(text=arr_times[7], callback_data=arr_times[7]),
              types.InlineKeyboardButton(text=arr_times[8], callback_data=arr_times[8])]
    markup.add(*button)
    await state.set_state(UserStates.all()[4])
    await bot.send_message(message.from_user.id, 'Спасибо, теперь, выберите час окончания в формате 24ч. ⏰',
                           reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[6], state=UserStates.USER_STATE_3)
async def first_test_state_case_met(message: types.Message):
    arr_times[0] = '❌'
    arr_times[1] = '❌'
    arr_times[2] = '❌'
    arr_times[3] = '❌'
    arr_times[4] = '❌'
    arr_times[5] = '❌'
    arr_times[6] = '❌'
    arr_times[8] = '17:00'
    userC = user_state[message.from_user.id]
    userC.timestart = 6
    state = dp.current_state(user=message.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=3)
    button = [types.InlineKeyboardButton(text=arr_times[0], callback_data=arr_times[0]),
              types.InlineKeyboardButton(text=arr_times[1], callback_data=arr_times[1]),
              types.InlineKeyboardButton(text=arr_times[2], callback_data=arr_times[2]),
              types.InlineKeyboardButton(text=arr_times[3], callback_data=arr_times[3]),
              types.InlineKeyboardButton(text=arr_times[4], callback_data=arr_times[4]),
              types.InlineKeyboardButton(text=arr_times[5], callback_data=arr_times[5]),
              types.InlineKeyboardButton(text=arr_times[6], callback_data=arr_times[6]),
              types.InlineKeyboardButton(text=arr_times[7], callback_data=arr_times[7]),
              types.InlineKeyboardButton(text=arr_times[8], callback_data=arr_times[8])]
    markup.add(*button)
    await state.set_state(UserStates.all()[4])
    await bot.send_message(message.from_user.id, 'Спасибо, теперь, выберите час окончания в формате 24ч. ⏰',
                           reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[7], state=UserStates.USER_STATE_3)
async def first_test_state_case_met(message: types.Message):
    arr_times[0] = '❌'
    arr_times[1] = '❌'
    arr_times[2] = '❌'
    arr_times[3] = '❌'
    arr_times[4] = '❌'
    arr_times[5] = '❌'
    arr_times[6] = '❌'
    arr_times[7] = '❌'
    arr_times[8] = '17:00'
    userC = user_state[message.from_user.id]
    userC.timestart = 5
    state = dp.current_state(user=message.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=3)
    button = [types.InlineKeyboardButton(text=arr_times[0], callback_data=arr_times[0]),
              types.InlineKeyboardButton(text=arr_times[1], callback_data=arr_times[1]),
              types.InlineKeyboardButton(text=arr_times[2], callback_data=arr_times[2]),
              types.InlineKeyboardButton(text=arr_times[3], callback_data=arr_times[3]),
              types.InlineKeyboardButton(text=arr_times[4], callback_data=arr_times[4]),
              types.InlineKeyboardButton(text=arr_times[5], callback_data=arr_times[5]),
              types.InlineKeyboardButton(text=arr_times[6], callback_data=arr_times[6]),
              types.InlineKeyboardButton(text=arr_times[7], callback_data=arr_times[7]),
              types.InlineKeyboardButton(text=arr_times[8], callback_data=arr_times[8])]
    markup.add(*button)
    await state.set_state(UserStates.all()[4])
    await bot.send_message(message.from_user.id, 'Спасибо, теперь, выберите час окончания в формате 24ч. ⏰',
                           reply_markup=markup)


# --------------------------------------Команды------------------------------------------------------------------------

@dp.message_handler(commands=['start'], state='*')
async def process_start_command(message: types.Message):
    arr_times = DEF_ARR_TIMES
    sql_check = "SELECT * FROM users "
    cursor.execute(sql_check)
    newlist = cursor.fetchall()
    if not newlist:
        data = await get_data()
        cursor.executemany("INSERT INTO users VALUES(?,?,?,?,?,?)", data)
        await save_data()
    state = dp.current_state(user=message.from_user.id)
    await state.set_state(UserStates.all()[0])
    conn.commit()
    button = InlineKeyboardButton('Посмотерть рассписание 📅', callback_data='buttontime')
    button2 = InlineKeyboardButton('Записаться 📝', callback_data='buttonzapis')
    button3 = InlineKeyboardButton('Удалить запись ❌', callback_data='buttondelzapis')
    kb = InlineKeyboardMarkup().add(button).add(button2).add(button3)
    await bot.send_message(message.from_user.id,
                           "Здравствуйте! 👋\nЭто бот-расписание БНП для автомобиля!\nВыберите, что вы хотите сделать.",
                           reply_markup=kb)


@dp.message_handler(commands=['help'], state='*')
async def process_help_command(message: types.Message):
    await bot.send_message(message.from_user.id, "Здравствуйте! 👋\nЭто бот-расписание БНП для автомобиля!\n"
                                                 "Для начала используйте команду /start\n"
                                                 "Для записи команда /zapis\n"
                                                 "Для просмотра расписания /otchet\n"
                                                 "Если что-то посло не так - /reset")


@dp.message_handler(commands=['reset2'], state='*')
async def process_help_command(message: types.Message):
    if message.from_user.id == admin_id:
        cursor.execute("DROP TABLE users")
        cursor.execute(
            "CREATE TABLE users (chatid INTEGER , name TEXT, date INTEGER, timestart INTEGER, timeend INTEGER, "
            "id INTEGER PRIMARY KEY)")
        state = dp.current_state(user=message.from_user.id)
        await state.set_state(UserStates.all()[0])
        await save_data()
        await bot.send_message(message.from_user.id, "Все СТЕРТО.")
    else:
        await bot.send_message(message.from_user.id, "Вам сюда нельзя.")


@dp.message_handler(commands=['base'], state='*')
async def process_help_command(message: types.Message):
    if message.from_user.id == admin_id:
        sql_check = "SELECT * FROM users ORDER BY date DESC"
        cursor.execute(sql_check)
        resultlist = cursor.fetchall()
        if not resultlist:
            await bot.send_message(message.from_user.id, 'Пустая таблица')
        else:
            workbook = xlsxwriter.Workbook('base.xlsx')
            worksheet = workbook.add_worksheet()
            worksheet.write(0, 0, 'ID')
            worksheet.write(0, 1, 'Chat_id')
            worksheet.write(0, 2, 'Имя')
            worksheet.write(0, 3, 'Дата')
            worksheet.write(0, 4, 'Время')
            count = 1
            for elem in resultlist:
                dateOut = str(elem[2])
                dateOut = dateOut[:4] + '-' + dateOut[4:6] + '-' + dateOut[6:]
                worksheet.write(count, 0, elem[5])
                worksheet.write(count, 1, elem[0])
                worksheet.write(count, 2, elem[1])
                worksheet.write(count, 3, dateOut)
                worksheet.write(count, 4, 'c ' + DEF_ARR_TIMES[elem[3]] + ' до ' + DEF_ARR_TIMES[elem[4]])
                count += 1
            workbook.close()
            f = open('./base.xlsx', 'rb')
            await bot.send_document(message.from_user.id, f)
    else:
        await bot.send_message(message.from_user.id, "Вам сюда нельзя.")


@dp.message_handler(commands=['otchet'], state="*")
async def process_callback_button1(message: types.Message):
    state = dp.current_state(user=message.from_user.id)
    await state.set_state(UserStates.all()[5])
    markup = types.InlineKeyboardMarkup(row_width=3)
    button = [types.InlineKeyboardButton(text='Отчет по имени', callback_data='table_name'),
              types.InlineKeyboardButton(text='Отчет по дате', callback_data='table_date'),
              types.InlineKeyboardButton(text='Полный отчет', callback_data='table_full')]
    markup.add(*button)
    await bot.send_message(message.from_user.id, 'Какой отчет нужен ?', reply_markup=markup)


@dp.message_handler(commands=['zapis'], state="*")
async def process_callback_button2(message: types.Message):
    state = dp.current_state(user=message.from_user.id)
    await state.set_state(UserStates.all()[1])
    await bot.send_message(message.from_user.id, 'Введите ФИО.', )


@dp.message_handler(commands=['delzapis'], state="*")
async def process_callback_button_del(message: types.Message):
    state = dp.current_state(user=message.from_user.id)
    await state.set_state(UserStates.all()[0])
    sql_check = "SELECT * FROM users where chatid={}".format(message.from_user.id)
    cursor.execute(sql_check)
    newlist = cursor.fetchall()
    if not newlist:
        await bot.send_message(message.from_user.id, 'У Вас нет записей.', )
    else:
        i = 0
        markup = types.InlineKeyboardMarkup(resize_keyboard=True)
        for elem in newlist:
            dateOut = str(elem[2])
            dateOut = dateOut[:4] + '-' + dateOut[4:6] + '-' + dateOut[6:]
            button = types.InlineKeyboardButton(text=dateOut + ' ' + DEF_ARR_TIMES[elem[3]] + ' - ' + DEF_ARR_TIMES[elem[4]],
                                                callback_data=callback_del.new(action="del", id=elem[5]))
            markup.add(button)
            i += 1
        state = dp.current_state(user=message.from_user.id)
        await state.set_state(UserStates.all()[1])
        await bot.send_message(message.from_user.id, 'Какую запись удалить?', reply_markup=markup)


@dp.message_handler(commands=['reset'], state='*')
async def process_help_command(message: types.Message):
    arr_times = DEF_ARR_TIMES
    data = await get_data()
    cursor.execute("DROP TABLE users")
    cursor.execute(
        "CREATE TABLE users (chatid INTEGER , name TEXT, date INTEGER, timestart INTEGER, timeend INTEGER, "
        "id INTEGER PRIMARY KEY)")
    cursor.executemany("INSERT INTO users VALUES(?,?,?,?,?)", data)
    await save_data()
    state = dp.current_state(user=message.from_user.id)
    await state.set_state(UserStates.all()[0])
    await bot.send_message(message.from_user.id, "Все, можете возвращаться к работе.")


# ------------Последний этап, выбор окончания аренды, запись в базу --------------------------

@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[1], state=UserStates.USER_STATE_4)
async def first_test_state_case_met(message: types.Message):
    userC = user_state[message.from_user.id]
    userC.timeend = 1
    await timeendfunc(message, userC)


@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[2], state=UserStates.USER_STATE_4)
async def first_test_state_case_met(message: types.Message):
    userC = user_state[message.from_user.id]
    userC.timeend = 2
    await timeendfunc(message, userC)


@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[3], state=UserStates.USER_STATE_4)
async def first_test_state_case_met(message: types.Message):
    userC = user_state[message.from_user.id]
    userC.timeend = 3
    await timeendfunc(message, userC)


@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[4], state=UserStates.USER_STATE_4)
async def first_test_state_case_met(message: types.Message):
    userC = user_state[message.from_user.id]
    userC.timeend = 4
    await timeendfunc(message, userC)


@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[5], state=UserStates.USER_STATE_4)
async def first_test_state_case_met(message: types.Message):
    userC = user_state[message.from_user.id]
    userC.timeend = 5
    await timeendfunc(message, userC)


@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[6], state=UserStates.USER_STATE_4)
async def first_test_state_case_met(message: types.Message):
    userC = user_state[message.from_user.id]
    userC.timeend = 6
    await timeendfunc(message, userC)


@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[7], state=UserStates.USER_STATE_4)
async def first_test_state_case_met(message: types.Message):
    userC = user_state[message.from_user.id]
    userC.timeend = 7
    await timeendfunc(message, userC)


@dp.callback_query_handler(lambda c: c.data == DEF_ARR_TIMES[8], state=UserStates.USER_STATE_4)
async def first_test_state_case_met(message: types.Message):
    userC = user_state[message.from_user.id]
    userC.timeend = 8
    await timeendfunc(message, userC)


async def timeendfunc(message, userC):
    sql_check = "SELECT * FROM users where date={}".format(userC.date)
    cursor.execute(sql_check)
    newlist = cursor.fetchall()
    if not newlist:
        print('Пуста 2')
        sql_insert = "INSERT INTO users (chatid, name, date, timestart, timeend) VALUES ('{}', '{}', '{}', '{}','{}')" \
            .format(message.from_user.id,
                    userC.fullname,
                    userC.date, userC.timestart,
                    userC.timeend)
        cursor.execute(sql_insert)
        state = dp.current_state(user=message.from_user.id)
        dateOut = str(userC.date)
        dateOut = dateOut[:4] + '-' + dateOut[4:6] + '-' + dateOut[6:]
        await state.set_state(UserStates.all()[0])
        await save_data()
        await bot.send_message(message.from_user.id,
                               '{}, вы записаны {} c {} до {}'.format(userC.fullname, dateOut,
                                                                      DEF_ARR_TIMES[userC.timestart],
                                                                      DEF_ARR_TIMES[userC.timeend]))
    else:
        chek = False
        for i in range(userC.timestart, userC.timeend - 1):
            for elem in newlist:
                if i == elem[3] or i == elem[4]:
                    chek = True
                    break
        if not chek:
            sql_insert = "INSERT INTO users (chatid, name, date, timestart, timeend) VALUES ('{}', '{}', '{}', '{}','{}')" \
                .format(message.from_user.id,
                        userC.fullname,
                        userC.date,
                        userC.timestart,
                        userC.timeend)
            cursor.execute(sql_insert)
            state = dp.current_state(user=message.from_user.id)
            dateOut = str(userC.date)
            dateOut = dateOut[:4] + '-' + dateOut[4:6] + '-' + dateOut[6:]
            await state.set_state(UserStates.all()[0])
            await save_data()
            await bot.send_message(message.from_user.id,
                                   '{}, вы записаны {} c {} до {}'.format(userC.fullname, dateOut,
                                                                          DEF_ARR_TIMES[userC.timestart],
                                                                          DEF_ARR_TIMES[userC.timeend]))
        else:
            arr_times = DEF_ARR_TIMES
            for ellist in newlist:
                for i in range(int(ellist[3]), int(ellist[4])):
                    arr_times[i] = '❌'
            state = dp.current_state(user=message.from_user.id)
            markup = types.InlineKeyboardMarkup(row_width=3)
            button = [types.InlineKeyboardButton(text=arr_times[0], callback_data=arr_times[0]),
                      types.InlineKeyboardButton(text=arr_times[1], callback_data=arr_times[1]),
                      types.InlineKeyboardButton(text=arr_times[2], callback_data=arr_times[2]),
                      types.InlineKeyboardButton(text=arr_times[3], callback_data=arr_times[3]),
                      types.InlineKeyboardButton(text=arr_times[4], callback_data=arr_times[4]),
                      types.InlineKeyboardButton(text=arr_times[5], callback_data=arr_times[5]),
                      types.InlineKeyboardButton(text=arr_times[6], callback_data=arr_times[6]),
                      types.InlineKeyboardButton(text=arr_times[7], callback_data=arr_times[7]),
                      types.InlineKeyboardButton(text=arr_times[8], callback_data=arr_times[8])]
            markup.add(*button)
            await state.set_state(UserStates.all()[3])
            await bot.send_message(message.from_user.id, 'Нельзя выбрать этот промежуток выберите другой',
                                   reply_markup=markup)


#-----------------------------------Удаление записи---------------------------------------------------------------

@dp.callback_query_handler(lambda c: c.data == "buttondelzapis", state="*")
async def process_callback_button_del(message: types.Message):
    state = dp.current_state(user=message.from_user.id)
    await state.set_state(UserStates.all()[0])
    sql_check = "SELECT * FROM users where chatid={}".format(message.from_user.id)
    cursor.execute(sql_check)
    newlist = cursor.fetchall()
    if not newlist:
        await bot.send_message(message.from_user.id, 'У Вас нет записей.', )
    else:
        i = 0
        markup = types.InlineKeyboardMarkup(resize_keyboard=True)
        for elem in newlist:
            dateOut = str(elem[2])
            dateOut = dateOut[:4] + '-' + dateOut[4:6] + '-' + dateOut[6:]
            button = types.InlineKeyboardButton(text=dateOut + ' ' + DEF_ARR_TIMES[elem[3]] + ' - ' + DEF_ARR_TIMES[elem[4]],
                                                callback_data=callback_del.new(action="del", id=elem[5]))
            markup.add(button)
            i += 1
        state = dp.current_state(user=message.from_user.id)
        await state.set_state(UserStates.all()[1])
        await bot.send_message(message.from_user.id, 'Какую запись удалить?', reply_markup=markup)

@dp.callback_query_handler(callback_del.filter(action=["del"]), state="*")
async def callbacks_del(call: types.CallbackQuery, callback_data: dict):
    state = dp.current_state(user=call.from_user.id)
    await state.set_state(UserStates.all()[0])
    del_id = callback_data["id"]
    cursor.execute("DELETE FROM users WHERE id={}".format(del_id))
    await save_data()
    await bot.send_message(call.from_user.id, 'Все успешно удалено ✅')
    await call.answer()

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
