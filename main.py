#########################################
# телеграм бот Интернационального Союза #
#                                       #
# main.py — главный файл, его и нужно   #
#           запускать для старта бота   #
#########################################

# импорты ¯\_(ツ)_/¯
from aiogram import Bot, types, Dispatcher, executor
from os import environ, remove
import db as botdb
import subprocess
import asyncio
import logging
import pymysql
import pandas


# это что-бы небыло ошибок при отправке сообщений
def escape(s):
    return s.replace("-", "\\-").replace(".", "\\.").replace("!", "\\!").replace("+", "\\+").replace("_", "\\_").replace(";", "\\;").replace("{", "\\{").replace("}", "\\}")


# настройка логера
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# добавление хэндлера на уровне инфо для вывода в консоль
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(levelname)s: %(message)s\n")
handler.setFormatter(formatter)
logger.addHandler(handler)

# добавление хэндлера на уровне дебаг для вывода в файл
handler = logging.FileHandler("debug.log")
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s: %(message)s\n")
handler.setFormatter(formatter)
logger.addHandler(handler)


# хуйня нужная для бота
loop = asyncio.get_event_loop()
bot = Bot(token=environ["IU_BOT_TOKEN"], parse_mode = types.ParseMode.MARKDOWN_V2)
dp = Dispatcher(bot, loop=loop)


# получить логи через сообщение
# кст тут нужно будет пароль сделать или вроде того,
# а то будет непойми кто так хуйню творить
@dp.message_handler(commands=["getlog"])
async def command_getlog(message: types.Message):
    await message.reply_document(open("debug.log"))


# почистить логи, а то начнут ещё места дохера занимать
# кст и тут нужно будет пароль сделать или вроде того,
# а то будет непойми кто так хуйню творить
@dp.message_handler(commands=["clrlog"])
async def command_clrlog(message: types.Message):
    with open("debug.log", "w") as file:
        file.write("")
        await message.reply(escape("Успешно выполнено."))


# посмотреть транзакции
# кст тут тоже нужно будет пароль сделать или вроде того,
# а то будет непойми кто так хуйню творить
@dp.message_handler(commands=["gettra"])
async def command_gettra(message: types.Message):
    cursor = botdb.db.cursor()
    sql  = "SELECT * FROM bank_transactions;"
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        await message.reply("`" + ("\n".join([", ".join([str(r) for r in res]) for res in results])) + "`")
    except pymysql.MySQLError as e:
        botdb.db.rollback()
        logger.error('Got error {!r}, errno is {}'.format(e, e.args[0]))


# линк на гитхаб
@dp.message_handler(commands=["source"])
async def command_source(message: types.Message):
    await message.reply(escape("Этот бот на гитхабе: https://github.com/miraneko/IUBot"))


# при старте бота в лс чтоб сразу регало
@dp.message_handler(commands=["start"])
async def command_start(message: types.Message):
    if message.chat.id < 0:
        await message.reply(escape("Данное действие запрещено в чатах."))
    else:
        if botdb.addUser(botdb.db, message):
            await message.reply(escape("Вы уже зарегистрированы в боте."))
        else:
            await message.reply(escape("Вы успешно зарегистрированы в боте."))


# зарегать баланс в боте
@dp.message_handler(commands=["register_balance"])
async def command_register_balance(message: types.Message):
    if message.chat.id < 0:
        await message.reply(escape("Данное действие запрещено в чатах."))
    else:
        val = botdb.regBalance(botdb.db, message)
        if val:
            if val == 1:
                await message.reply(escape("Вы не зарегистрированы в боте. Для исправления этого напишите /start мне в лс."))
            elif val == 2:
                await message.reply(escape("Вы уже зарегистрированы в нашей банковской системе."))
        else:
            await message.reply(escape("Вы успешно зарегистрированы в нашей банковской системе."))


# обновить данные юзверя, на случай изменения ника или темболее юзверьнэйма
@dp.message_handler(commands=["update"])
async def command_update(message: types.Message):
    if message.chat.id < 0:
        await message.reply(escape("Данное действие запрещено в чатах."))
    else:
        botdb.updateUser(botdb.db, message)
        await message.reply(escape("Успешно выполнено."))


# посмотрить уи чата
# кст (нечто оригинальное) нужно будет пароль сделать или вроде того,
# а то будет непойми кто так хуйню творить
@dp.message_handler(commands=["get_chat_id"])
async def command_get_chat_id(message: types.Message):
    await message.reply(escape(str(message.chat.id)))

# посмотрить уи чата
# кст (что-то оригинальное, опять…) нужно будет пароль сделать или вроде того,
# а то будет непойми кто так хуйню творить
@dp.message_handler(commands=["get_msg"])
async def command_msg(message: types.Message):
    if message.reply_to_message:
        await message.reply(escape(str(message.reply_to_message)))
    else:
        await message.reply(escape(str(message)))


# посмотреть всякие оч интересные (нет) графики
@dp.message_handler(commands=["plots"])
async def command_plots(message: types.Message):
    sql = "SELECT * FROM messages"
    results = pandas.read_sql_query(sql, botdb.db)
    results.to_csv("messages.csv", index=False) # да, костыль, и что с того? сделайте лучше если можете
    subprocess.run(["R", "--vanilla", "--slave", "-f", "plot.r"]) # и да, опять костыль
    await message.reply_photo(open("pie.png", "rb"), caption=escape("Количество сообщений: " + str(results.count()).split()[1]))
    await message.reply_photo(open("abh.png", "rb"))
    await message.reply_photo(open("words.png", "rb"))
    await message.reply_photo(open("days.png", "rb"))
    for file in ["pie.png", "abh.png", "words.png", "days.png", "messages.csv"]:
        remove(file)


# вывести список наших чатов и каналов
# и да, кто-нибудь сделайте уже для остальных хуёвин
# подобные краткие описания, а то онли канцелярия…
# это как-то странно выглядит
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


# посмотреть баланс
@dp.message_handler(commands=["get_balance"])
async def command_get_balance(message: types.Message):
    val = botdb.getBalance(botdb.db, tg_id=message.from_user.id)
    if val != None:
        await message.reply(escape("Ваш баланс — {0} МАР.".format(str(val))))
    else:
        if botdb.getUser(botdb.db, tg_id=message.from_user.id):
            await message.reply(escape("Вы не зарегистрированы в банковской системе."))
        else:
            await message.reply(escape("Вы не зарегистрированы в боте."))


# дать бабла
@dp.message_handler(commands=["pay"])
async def command_pay(message: types.Message):
    if message.from_user.id in [958493955, 1210500401, 807020736]:
        try:
            username = str(message.get_args().split()[0][1:])
            amount = float(message.get_args().split()[1])
        except:
            await message.reply(escape("Вы неправильно ввелии данные."))
            return
        val = botdb.pay(botdb.db, amount, tg_username=username)
        if val == 1:
            await message.reply(escape("Пользователь не зарегистрирован в боте."))
        elif val == 2:
            await message.reply(escape("Пользователь не зарегистрирован в банковской системе."))
        else:
            await message.reply(escape("Операция выполнена успешно."))
            await bot.send_message(botdb.getUser(botdb.db, tg_username=username)["tg_id"], escape("Вы получили от государства {0} МАР.").format(
                escape(str(amount))
            ))
    else:
        await message.reply(escape("У вас нодостаточно прав для данного действия."))


# послать бабла
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
    if botdb.getBalance(botdb.db, tg_id=message.from_user.id) < amount:
        await message.reply(escape("Вы не можете отправить больше чем имеете."))
        return
    val = botdb.send(botdb.db, amount, tg_id_from=message.from_user.id, tg_username_to=username)
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
        await bot.send_message(botdb.getUser(botdb.db, tg_username=username)["tg_id"], escape("Вы получили {0} МАР от {1}.").format(
            escape(str(amount)),
            escape(message.from_user.full_name)
        ))


# о, ещё 1 чел припёрся
@dp.message_handler(content_types=types.ContentType.NEW_CHAT_MEMBERS)
async def new_member(message: types.Message):
    await message.answer((escape("Приветствую вас, {0}!\n"
        + "Здесь вы можете пообщаться с разными интересными людьми, стать частью политической жизни государства, а также просто отдохнуть от проблем.\n"
        + "Если вы желаете лучше ознакомится с нашим государством, можете посмотреть навигатор, это делается коммандой /navigator.")).format(
            escape(message.new_chat_members[0].full_name)
    ))


# какой-то дурак свалил
@dp.message_handler(content_types=types.ContentType.LEFT_CHAT_MEMBER)
async def left_member(message: types.Message):
    await message.answer(escape("Рада была вас видеть, {0}. Буду ждать вашего возвращения!".format(
        message.left_chat_member.full_name
    )))


# сохранение некоторых данных о сообщениях для дальнейшего анализа
@dp.message_handler(content_types=types.ContentType.TEXT)
async def new_message(message: types.Message):
    if message.chat.id == -1001331650913:
        botdb.newmsg(botdb.db, message)


# запуск бота
executor.start_polling(dp, loop=loop, skip_updates=False)


# закрытие бд
botdb.db.close()
