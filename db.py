#########################################
# телеграм бот Интернационального Союза #
#                                       #
# db.py — файл для всего, что касается  #
#         доступа к базе данных         #
#########################################

# было бы неплохо ещё структуру бд
# и sql запрос для её создания тут написать,
# но мне лень

# импорты ¯\_(ツ)_/¯
from datetime import datetime
from os import environ
import pymysql
import logging


# настройка логера
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# добавление хэндлера на уровне дебаг для вывода в файл
handler = logging.FileHandler("debug.log")
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s: %(message)s\n")
handler.setFormatter(formatter)
logger.addHandler(handler)


# получить инфу о юзвере
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


# посмотреть баланс
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


# добавить нового юзверя
def addUser(db, message):
    if getUser(db, tg_id=message.from_user.id):
        return 1
    cursor = db.cursor()
    sql  = "INSERT INTO "
    sql += "users(tg_id, tg_username, tg_name) "
    sql += "VALUES(" + str(message.from_user.id) + ", '" + message.from_user.username + "', '" + message.from_user.full_name + "');"
    try:
        cursor.execute(sql)
        db.commit()
    except pymysql.MySQLError as e:
        db.rollback()
        logger.error('Got error {!r}, errno is {}'.format(e, e.args[0]))


# обновить инфу о юзвере
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


# зарегать в банковской системе
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


# дать бабла
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


# послать бабла
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


# сохранение некоторых данных о сообщении для дальнейшего анализа
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


# подключение к бд
db = pymysql.connect("localhost", environ["IU_DATABASE_USERNAME"], environ["IU_DATABASE_PASSWORD"], "fremar")
