# -*- coding: utf-8 -*-
import os, time
import telebot
from telebot import types
import paho.mqtt.client as mqtt
from urllib.parse import urlparse

bot = telebot.TeleBot(os.environ.get('TELEGRAM_TOKEN'))
bot_name = bot.get_me().username

# Parse CLOUDMQTT_URL (or fallback to localhost)
url_str = os.environ.get('CLOUDMQTT_URL')
url = urlparse(url_str)


# Define event callbacks
def on_connect(client, userdata, flags, rc):
    # print("rc: " + str(rc))
    pass


def on_message(client, obj, msg):
    message = str(msg.payload.decode("utf-8")).strip()
    topic = msg.topic
    # print(topic.strip() + "::" + str(msg.qos) + "::" + message)
    # print(topic.strip() + " :: " + message)

    if msg.topic == "kettle/temp":
        temp = int(message)
        if 'reply_message_id' not in os.environ:
            reply = bot.send_message(os.environ.get('chat_id'), "Температура: %s°C" % message)
            os.environ['reply_chat_id'] = str(reply.chat.id)
            os.environ['reply_message_id'] = str(reply.message_id)
        else:
            reply_chat_id = os.environ.get('reply_chat_id')
            reply_message_id = os.environ.get('reply_message_id')
            try:
                reply = bot.edit_message_text(chat_id=reply_chat_id, message_id=reply_message_id, text="Температура: %s°C" % message)
                os.environ['reply_chat_id'] = str(reply.chat.id)
                os.environ['reply_message_id'] = str(reply.message_id)
            except:
                pass

    # посылать сообщение после отключения чайника
    if message == "kettle off" and 'chat_id' in os.environ:
        kb_kettle = {'delete_msg': 'Отлично, иду'}
        keyboard = pages_inline_keyboard(kb_kettle, True)
        bot_msg = "Вода закипела."
        if 'reply_message_id' not in os.environ:
            bot.send_message(os.environ.get('chat_id'), bot_msg, reply_markup=keyboard)
        else:
            bot.edit_message_text(chat_id=os.environ.get('reply_chat_id'), message_id=os.environ['reply_message_id'], text=bot_msg, reply_markup=keyboard)


def on_publish(client, obj, mid):
    # print("mid: " + str(mid))
    pass


def on_subscribe(client, obj, mid, granted_qos):
    # print("Subscribed: " + str(mid) + " " + str(granted_qos))
    pass


def on_log(client, obj, level, string):
    # print(string)
    pass


# Connect
mqttc = mqtt.Client()
mqttc.username_pw_set(url.username, url.password)
mqttc.connect(url.hostname, url.port)
mqttc.loop_start()

# Assign event callbacks
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_subscribe = on_subscribe

# Uncomment to enable debug messages
# mqttc.on_log = on_log

# Start subscribe, with QoS level 0
mqttc.subscribe("kettle/status", 0)
mqttc.subscribe("kettle/temp", 0)
mqttc.subscribe("info", 0)

# Publish a message
# mqttc.publish("info", "hello world")
# mqttc.publish("kettle/status", "0")


@bot.message_handler(commands=["start"])
def cmd_start(message):
    os.environ['chat_id'] = str(message.chat.id)
    kb_kettle = {'kettle_on': 'Включить чайник', 'kettle_off': 'Выключить чайник'}
    keyboard = pages_inline_keyboard(kb_kettle, True)
    bot.send_message(message.chat.id, "Вскипятить воду?", reply_markup=keyboard)
    return 0


@bot.callback_query_handler(func=lambda call: hasattr(call, 'data') and call.data.find('delete_msg') == 0)
def delete_msg(message):
    try:
        bot.delete_message(message.from_user.id, message.message.message_id)
        del os.environ['reply_chat_id']
        del os.environ['reply_message_id']
    except:
        pass


@bot.callback_query_handler(func=lambda call: hasattr(call, 'data') and call.data.find('kettle_') == 0)
def kettle(message):
    if 'chat_id' not in os.environ:
        os.environ['chat_id'] = str(message.from_user.id)

    if message.data == 'kettle_on':
        mqttc.publish("kettle/status", "1")
    if message.data == 'kettle_off':
        mqttc.publish("kettle/status", "0")
        if 'reply_message_id' in os.environ:
            bot.delete_message(message.from_user.id, os.environ['reply_message_id'])
            del os.environ['reply_chat_id']
            del os.environ['reply_message_id']
    time.sleep(2)
    return 0


def pages_reply_keyboard(m, rk=True, ot=False):
    kb_start = types.ReplyKeyboardMarkup(resize_keyboard=rk, one_time_keyboard=ot)
    kb_start.add(*[types.KeyboardButton(name) for name in m])
    return kb_start


def pages_inline_keyboard(m, rows=False):
    keyboard = types.InlineKeyboardMarkup()
    btns = []
    if rows:
        for k, v in m.items():
            if urlparse(k).scheme != "":
                keyboard.row(types.InlineKeyboardButton(text=v, url=k))
            else:
                keyboard.row(types.InlineKeyboardButton(text=v, callback_data=k))
    else:
        for k, v in m.items():
            if urlparse(k).scheme != "":
                btns.append(types.InlineKeyboardButton(text=v, url=k))
            else:
                btns.append(types.InlineKeyboardButton(text=v, callback_data=k))
        keyboard.add(*btns)
    return keyboard  # возвращаем объект клавиатуры


if __name__ == '__main__':
    bot.polling(none_stop=True)
    # Continue the network loop, exit when an error occurs
    # while rc == 0:
    #     rc = mqttc.loop()
    #     print("rc: " + str(rc))
