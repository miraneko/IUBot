from aiogram import Bot, types, Dispatcher, executor
from datetime import datetime
from os import environ
import subprocess
import logging
import asyncio
import pymysql
import random
import pandas

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(levelname)s: %(message)s\n")
handler.setFormatter(formatter)
logger.addHandler(handler)

def getUser(db, id=None, tg_id=None, tg_username=None, tg_name=None):
    cursor = db.cursor()
    sql  = "SELECT * FROM users "
    if   id          != None: sql += "WHERE id = "           + str(id)          + ";"
    elif tg_id       != None: sql += "WHERE tg_id = "        + str(tg_id)       + ";"
    elif tg_username != None: sql += "WHERE tg_username = '" + str(tg_username) + "';"
    elif tg_name     != None: sql += "WHERE tg_name = '"     + str(tg_name)     + "';"
    else: return None
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        return {"id": results[0][0], "tg_id": results[0][1], "tg_username": results[0][2], "tg_name": results[0][3]} if results else None
    except pymysql.MySQLError as e:
        db.rollback()
        logger.error('Got error {!r}, errno is {}'.format(e, e.args[0]))

def getBalance(db, id=None, tg_id=None, tg_username=None, tg_name=None):
    if id == None:
        user = getUser(db, tg_id=tg_id, tg_username=tg_username, tg_name=tg_name)
        if user == None:
            return None
        else:
            id = user["id"]
    cursor = db.cursor()
    sql  = "SELECT * FROM balances WHERE id = " + str(id) + ";"
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        return float(results[0][1]) if results else None
    except pymysql.MySQLError as e:
        db.rollback()
        logger.error('Got error {!r}, errno is {}'.format(e, e.args[0]))

def addUser(db, message):
    if getUser(db, tg_id=message.from_user.id):
        return 1
    cursor = db.cursor()
    sql  = "INSERT INTO "
    sql += "users(tg_id, tg_username, tg_name) "
    sql += "VALUES(" + str(message.from_user.id) + ", '" + message.from_user.username + "', '" + message.from_user.full_name + "');"
    try:
        cursor.execute(sql)
        db.comft()
    except pymysql.MySQLError as e:
        db.rollback()
        logger.error('Got error {!r}, errno is {}'.format(e, e.args[0]))

def updateUser(db, message):
    cursor = db.cursor()
    sql = "UPDATE users SET tg_username = '" + message.from_user.username + "' WHERE tg_id = " + str(message.from_user.id) + ";"
    try:
        cursor.execute(sql)
        db.commit()
    except pymysql.MySQLError as e:
        db.rollback()
        logger.error('Got error {!r}, errno is {}'.format(e, e.args[0]))
    cursor = db.cursor()
    sql = "UPDATE users SET tg_name = '" + message.from_user.full_name + "' WHERE tg_id = " + str(message.from_user.id) + ";"
    try:
        cursor.execute(sql)
        db.commit()
    except pymysql.MySQLError as e:
        db.rollback()
        logger.error('Got error {!r}, errno is {}'.format(e, e.args[0]))

def regBalance(db, message):
    user = getUser(db, tg_id=message.from_user.id)
    if user == None:
        return 1
    if getBalance(db, tg_id=message.from_user.id) != None:
        return 2
    cursor = db.cursor()
    sql  = "INSERT INTO "
    sql += "balances(id) "
    sql += "VALUES(" + str(user["id"]) + ");"
    try:
        cursor.execute(sql)
        db.commit()
    except pymysql.MySQLError as e:
        db.rollback()
        logger.error('Got error {!r}, errno is {}'.format(e, e.args[0]))

def pay(db, amount, id=None, tg_id=None, tg_username=None, tg_name=None):
    user = getUser(db, id=id, tg_id=tg_id, tg_username=tg_username, tg_name=tg_name)
    if user == None:
        return 1
    balance = getBalance(db, id=user["id"])
    if balance == None:
        return 2
    cursor = db.cursor()
    sql  = "INSERT INTO "
    sql += "bank_transactions(from_user, to_user, amount, tra_type, dt) "
    sql += "VALUES(0, " + str(user["id"]) + ", " + str(round(amount, 5)) + ", 'pay', '" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "');"
    try:
        cursor.execute(sql)
        db.commit()
    except pymysql.MySQLError as e:
        db.rollback()
        logger.error('Got error {!r}, errno is {}'.format(e, e.args[0]))
    cursor = db.cursor()
    sql  = "UPDATE balances "
    sql += "SET balance = " + str(round(balance + amount, 5))
    sql += "WHERE id = " + str(user["id"]) + ";"
    try:
        cursor.execute(sql)
        db.commit()
    except pymysql.MySQLError as e:
        db.rollback()
        logger.error('Got error {!r}, errno is {}'.format(e, e.args[0]))

def send(db, amount, id_from=None, tg_id_from=None, tg_username_from=None, tg_name_from=None, id_to=None, tg_id_to=None, tg_username_to=None, tg_name_to=None):
    user_from = getUser(db, id=id_from, tg_id=tg_id_from, tg_username=tg_username_from, tg_name=tg_name_from)
    user_to = getUser(db, id=id_to, tg_id=tg_id_to, tg_username=tg_username_to, tg_name=tg_name_to)
    if user_from == None:
        return 1
    elif user_to == None:
        return 2
    balance_from = getBalance(db, id=user_from["id"])
    balance_to = getBalance(db, id=user_to["id"])
    if balance_from == None:
        return 3
    elif balance_to == None:
        return 4
    balance_from = round(balance_from - amount, 5)
    balance_to = round(balance_to + amount, 5)
    cursor = db.cursor()
    sql  = "INSERT INTO "
    sql += "bank_transactions(from_user, to_user, amount, tra_type, dt) "
    sql += "VALUES(" + str(user_from["id"]) + ", " + str(user_to["id"]) + ", " + str(round(amount, 5)) + ", 'snd', '" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "');"
    try:
        cursor.execute(sql)
        db.commit()
    except pymysql.MySQLError as e:
        db.rollback()
        logger.error('Got error {!r}, errno is {}'.format(e, e.args[0]))
    cursor = db.cursor()
    sql  = "UPDATE balances "
    sql += "SET balance = " + str(balance_from) + " "
    sql += "WHERE id = " + str(user_from["id"]) + ";"
    try:
        cursor.execute(sql)
        db.commit()
    except pymysql.MySQLError as e:
        db.rollback()
        logger.error('Got error {!r}, errno is {}'.format(e, e.args[0]))
    cursor = db.cursor()
    sql  = "UPDATE balances "
    sql += "SET balance = " + str(balance_to) + " "
    sql += "WHERE id = " + str(user_to["id"]) + ";"
    try:
        cursor.execute(sql)
        db.commit()
    except pymysql.MySQLError as e:
        db.rollback()
        logger.error('Got error {!r}, errno is {}'.format(e, e.args[0]))

def newmsg(db, message):
    if len(message.text.split()) > 100:
        return
    cursor = db.cursor()
    sql  = "INSERT INTO "
    sql += "messages(id, dt, tg_name, words) "
    sql += "VALUES(" + str(message.message_id) + ", '" + str(message.date) + "', '" + message.from_user.full_name + "', " + str(len(message.text.split())) + ");"
    try:
        cursor.execute(sql)
        db.commit()
    except pymysql.MySQLError as e:
        db.rollback()
        logger.error('Got error {!r}, errno is {}'.format(e, e.args[0]))

def escape(s):
    return s.replace("-", "\\-").replace(".", "\\.").replace("!", "\\!").replace("+", "\\+").replace("_", "\\_").replace(";", "\\;").replace("{", "\\{").replace("}", "\\}")

db = pymysql.connect("localhost", environ["IU_DATABASE_USERNAME"], environ["IU_DATABASE_PASSWORD"], "fremar")

chats = [-1001331650913]
canPay = [958493955, 1210500401, 807020736]

handler = logging.FileHandler("debug.log")
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s: %(message)s\n")
handler.setFormatter(formatter)
logger.addHandler(handler)

loop = asyncio.get_event_loop()
bot = Bot(token=environ["IU_BOT_TOKEN"], parse_mode = types.ParseMode.MARKDOWN_V2)
dp = Dispatcher(bot, loop=loop)

@dp.message_handler(commands=["getlog"])
async def command_getlog(message: types.Message):
    await message.reply_document(open("debug.log"))

@dp.message_handler(commands=["clrlog"])
async def command_clrlog(message: types.Message):
    with open("debug.log", "w") as file:
        file.write("")
        await message.reply(escape("Успешно выполнено."))

@dp.message_handler(commands=["gettra"])
async def command_gettra(message: types.Message):
    cursor = db.cursor()
    sql  = "SELECT * FROM bank_transactions;"
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        await message.reply("`" + ("\n".join([", ".join([str(r) for r in res]) for res in results])) + "`")
    except pymysql.MySQLError as e:
        db.rollback()
        logger.error('Got error {!r}, errno is {}'.format(e, e.args[0]))

@dp.message_handler(commands=["start"])
async def command_start(message: types.Message):
    if message.chat.id < 0:
        await message.reply(escape("Данное действие запрещено в чатах."))
    else:
        if addUser(db, message):
            await message.reply(escape("Вы уже зарегистрированы в боте."))
        else:
            await message.reply(escape("Вы успешно зарегистрированы в боте."))

@dp.message_handler(commands=["register_balance"])
async def command_register_balance(message: types.Message):
    if message.chat.id < 0:
        await message.reply(escape("Данное действие запрещено в чатах."))
    else:
        val = regBalance(db, message)
        if val:
            if val == 1:
                await message.reply(escape("Вы не зарегистрированы в боте. Для исправления этого напишите /start мне в лс."))
            elif val == 2:
                await message.reply(escape("Вы уже зарегистрированы в нашей банковской системе."))
        else:
            await message.reply(escape("Вы успешно зарегистрированы в нашей банковской системе."))

@dp.message_handler(commands=["update"])
async def command_update(message: types.Message):
    if message.chat.id < 0:
        await message.reply(escape("Данное действие запрещено в чатах."))
    else:
        updateUser(db, message)
        await message.reply(escape("Успешно выполнено."))

@dp.message_handler(commands=["get_chat_id"])
async def command_get_chat_id(message: types.Message):
    await message.reply(escape(str(message.chat.id)))

@dp.message_handler(commands=["get_msg"])
async def command_msg(message: types.Message):
    if message.reply_to_message:
        await message.reply(escape(str(message.reply_to_message)))
    else:
        await message.reply(escape(str(message)))

@dp.message_handler(commands=["plots"])
async def command_plots(message: types.Message):
    sql = "SELECT * FROM messages"
    results = pandas.read_sql_query(sql, db)
    results.to_csv("messages.csv", index=False) # да, костыль, и что с того? сделайте лучше если можете
    subprocess.run(["R", "--vanilla", "--slave", "-f", "plot.r"]) # и да, опять костыль
    await message.reply_photo(open("pie.png", "rb"), caption=escape("Количество сообщений: " + str(results.count()).split()[1]))
    await message.reply_photo(open("abh.png", "rb"))
    await message.reply_photo(open("words.png", "rb"))
    await message.reply_photo(open("days.png", "rb"))
    subprocess.run(["rm", "*.png", "messages.csv"]) # ещё 1 костыль…

@dp.message_handler(commands=["navigator"])
async def command_navigator(message: types.Message):
    await message.reply(escape(("Навигатор\n\n"
        + "[🗃 Канцелярия]({0}) — здесь можно получить паспорт\n"
        + "[🎖 Газета Пионерская Слава]({1})\n"
        + "[📰 Информационное бюро]({2})\n"
        + "[🛃 Законодательство]({3})\n"
        + "[⚔️ Военкомат]({4})").format(
            "https://t.me/joinchat/SCbFMU2Q4tbKnv2LjCNtkA",
            "https://t.me/joinchat/AAAAAEUlQFEGCnIQZfnPJg",
            "https://t.me/joinchat/AAAAAFZyHztGygmQLlOKAw",
            "https://t.me/joinchat/AAAAAEuafsJAUmzt3xvjYw",
            "https://t.me/joinchat/SCbFMRy_nbvO3oW2zyXpJQ")
    ))

@dp.message_handler(commands=["get_balance"])
async def command_get_balance(message: types.Message):
    val = getBalance(db, tg_id=message.from_user.id)
    if val != None:
        await message.reply(escape("Ваш баланс — {0} МАР.").format(escape(str(val))))
    else:
        if getUser(db, tg_id=message.from_user.id):
            await message.reply(escape("Вы не зарегистрированы в банковской системе."))
        else:
            await message.reply(escape("Вы не зарегистрированы в боте."))

@dp.message_handler(commands=["pay"])
async def command_pay(message: types.Message):
    if message.from_user.id in canPay:
        try:
            username = str(message.get_args().split()[0][1:])
            amount = float(message.get_args().split()[1])
        except:
            await message.reply(escape("Вы неправильно ввелии данные."))
            return
        val = pay(db, amount, tg_username=username)
        if val == 1:
            await message.reply(escape("Пользователь не зарегистрирован в боте."))
        elif val == 2:
            await message.reply(escape("Пользователь не зарегистрирован в банковской системе."))
        else:
            await message.reply(escape("Операция выполнена успешно."))
            await bot.send_message(getUser(db, tg_username=username)["tg_id"], escape("Вы получили от государства {0} МАР.").format(
                escape(str(amount))
            ))
    else:
        await message.reply(escape("У вас нодостаточно прав для данного действия."))

@dp.message_handler(commands=["send"])
async def command_send(message: types.Message):
    try:
        username = str(message.get_args().split()[0][1:])
        amount = float(message.get_args().split()[1])
    except:
        await message.reply(escape("Вы неправильно ввелии данные."))
        return
    if amount <= 0:
        await message.reply(escape("Вы ввелии неправильные данные."))
        return
    if message.from_user.username == username:
        await message.reply(escape("Вы не можете отправить МАР себе."))
        return
    if getBalance(db, tg_id=message.from_user.id) < amount:
        await message.reply(escape("Вы не можете отправить больше чем имеете."))
        return
    val = send(db, amount, tg_id_from=message.from_user.id, tg_username_to=username)
    if val == 1:
        await message.reply(escape("Вы не зарегистрированы в боте."))
    elif val == 2:
        await message.reply(escape("Пользователь не зарегистрирован в боте."))
    elif val == 3:
        await message.reply(escape("Вы не зарегистрированы в банковской системе."))
    elif val == 4:
        await message.reply(escape("Пользователь не зарегистрирован в банковской системе."))
    else:
        await message.reply(escape("Операция выполнена успешно."))
        await bot.send_message(getUser(db, tg_username=username)["tg_id"], escape("Вы получили {0} МАР от {1}.").format(
            escape(str(amount)),
            escape(message.from_user.full_name)
        ))

@dp.message_handler(content_types=types.ContentType.NEW_CHAT_MEMBERS)
async def new_member(message: types.Message):
    await message.answer((escape("Приветствую вас, {0}!\n"
        + "Здесь вы можете пообщаться с разными интересными людьми, стать частью политической жизни государства, а также просто отдохнуть от проблем.\n"
        + "Если вы желаете лучше ознакомится с нашим государством, можете посмотреть навигатор, это делается коммандой /navigator.")).format(
            escape(message.new_chat_members[0].full_name)
    ))

@dp.message_handler(content_types=types.ContentType.LEFT_CHAT_MEMBER)
async def left_member(message: types.Message):
    await message.answer(escape("Рада была вас видеть, {0}. Буду ждать вашего возвращения!").format(
        escape(message.left_chat_member.full_name)
    ))

@dp.message_handler(content_types=types.ContentType.TEXT)
async def new_message(message: types.Message):
    if message.chat.id == -1001331650913:
        newmsg(db, message)

executor.start_polling(dp, loop=loop, skip_updates=False)
db.close()
