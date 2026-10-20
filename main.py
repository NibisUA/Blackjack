from bott_token import TOKEN
import telebot
from telebot import types
import random
import pickle
import os

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "users.pkl"

# ==========================
# SAVE / LOAD
# ==========================

def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "rb") as f:
            return pickle.load(f)
    return {}

def save_users():
    with open(DATA_FILE, "wb") as f:
        pickle.dump(users, f)

users = load_users()

# ==========================
# USER SYSTEM
# ==========================

def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "bank": 2000,
            "bet": 0,
            "deck": [],
            "player_cards": [],
            "dealer_cards": [],
            "game_active": False
        }
        save_users()

    return users[user_id]


# ==========================
# MENU
# ==========================

def main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add(types.KeyboardButton("/game"))
    kb.add(
        types.KeyboardButton("/bank"),
        types.KeyboardButton("/earn")
    )

    bot.send_message(
        chat_id,
        "Оберіть дію:",
        reply_markup=kb
    )


# ==========================
# BLACKJACK HELPERS
# ==========================

SUITS = ["♥", "♦", "♣", "♠"]
RANKS = ["A", "K", "Q", "J",
         "10", "9", "8", "7",
         "6", "5", "4", "3", "2"]

def create_deck():
    deck = []
    for suit in SUITS:
        for rank in RANKS:
            deck.append(f"{rank}{suit}")
    random.shuffle(deck)
    return deck

def card_value(card):
    rank = card[:-1]

    if rank in ["K", "Q", "J"]:
        return 10
    if rank == "A":
        return 11
    return int(rank)

def calculate_hand(cards):
    total = 0
    aces = 0

    for card in cards:
        rank = card[:-1]
        if rank == "A":
            aces += 1
        total += card_value(card)

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    return total


# ==========================
# START
# ==========================

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привіт! Це Blackjack бот.\n\nЛаскаво просимо!"
    )
    main_menu(message.chat.id)


# ==========================
# BANK
# ==========================

@bot.message_handler(commands=["bank"])
def bank(message):
    user = get_user(message.from_user.id)

    bot.send_message(
        message.chat.id,
        f"Ваш банк: {user['bank']}"
    )

    main_menu(message.chat.id)


# ==========================
# GAME
# ==========================

@bot.message_handler(commands=["game"])
def game(message):
    user = get_user(message.from_user.id)

    if user["bank"] <= 0:
        bot.send_message(
            message.chat.id,
            "У вас немає грошей.\nВикористайте /earn"
        )
        main_menu(message.chat.id)
        return

    msg = bot.send_message(
        message.chat.id,
        f"Ваш банк: {user['bank']}\n\nВведіть ставку:"
    )

    bot.register_next_step_handler(msg, choose_bet)


def choose_bet(message):
    user = get_user(message.from_user.id)

    try:
        bet = int(message.text)

        if bet <= 0:
            raise ValueError

        if bet > user["bank"]:
            bot.send_message(message.chat.id, "Недостатньо коштів.")
            main_menu(message.chat.id)
            return

        user["bet"] = bet
        start_blackjack(message)

    except:
        bot.send_message(message.chat.id, "Введіть коректне число.")
        main_menu(message.chat.id)


def start_blackjack(message):
    user = get_user(message.from_user.id)

    user["deck"] = create_deck()

    user["player_cards"] = [
        user["deck"].pop(),
        user["deck"].pop()
    ]

    user["dealer_cards"] = [
        user["deck"].pop(),
        user["deck"].pop()
    ]

    user["game_active"] = True
    save_users()

    dealer_hidden = user["dealer_cards"][0]

    bot.send_message(
        message.chat.id,
        f"Ваші карти:\n{', '.join(user['player_cards'])}\n\n"
        f"Очки: {calculate_hand(user['player_cards'])}"
    )

    bot.send_message(
        message.chat.id,
        f"Карти дилера:\n{dealer_hidden}, ❓"
    )

    show_buttons(message.chat.id)


def show_buttons(chat_id):
    kb = types.InlineKeyboardMarkup()

    kb.add(types.InlineKeyboardButton("Взяти карту", callback_data="hit"))
    kb.add(types.InlineKeyboardButton("Зупинитись", callback_data="stand"))

    bot.send_message(chat_id, "Ваш хід:", reply_markup=kb)


# ==========================
# HIT
# ==========================

@bot.callback_query_handler(func=lambda c: c.data == "hit")
def hit(call):
    user = get_user(call.from_user.id)

    if not user["game_active"]:
        return

    user["player_cards"].append(user["deck"].pop())

    total = calculate_hand(user["player_cards"])
    save_users()

    bot.send_message(
        call.message.chat.id,
        f"Ваші карти:\n{', '.join(user['player_cards'])}\n\nОчки: {total}"
    )

    if total > 21:
        user["bank"] -= user["bet"]
        user["game_active"] = False
        save_users()

        bot.send_message(
            call.message.chat.id,
            f"Перебір!\nБанк: {user['bank']}"
        )

        main_menu(call.message.chat.id)
        return

    show_buttons(call.message.chat.id)


# ==========================
# STAND
# ==========================

@bot.callback_query_handler(func=lambda c: c.data == "stand")
def stand(call):
    user = get_user(call.from_user.id)

    dealer_total = calculate_hand(user["dealer_cards"])

    while dealer_total < 17:
        user["dealer_cards"].append(user["deck"].pop())
        dealer_total = calculate_hand(user["dealer_cards"])

    player_total = calculate_hand(user["player_cards"])

    if dealer_total > 21:
        result = "Дилер програв"
        user["bank"] += user["bet"]

    elif dealer_total > player_total:
        result = "Дилер виграв"
        user["bank"] -= user["bet"]

    elif dealer_total < player_total:
        result = "Ви виграли"
        user["bank"] += user["bet"]

    else:
        result = "Нічия"

    user["game_active"] = False
    save_users()

    bot.send_message(
        call.message.chat.id,
        f"Карти дилера:\n{', '.join(user['dealer_cards'])}\n\n"
        f"Очки дилера: {dealer_total}\n"
        f"Ваші очки: {player_total}\n\n"
        f"{result}\n\n"
        f"Банк: {user['bank']}"
    )

    main_menu(call.message.chat.id)


# ==========================
# EARN
# ==========================

@bot.message_handler(commands=["earn"])
def earn(message):
    a = random.randint(1, 100)
    b = random.randint(1, 100)
    answer = a + b

    msg = bot.send_message(
        message.chat.id,
        f"Скільки буде {a} + {b} ?"
    )

    bot.register_next_step_handler(msg, check_earn, answer)


def check_earn(message, correct_answer):
    user = get_user(message.from_user.id)

    try:
        user_answer = int(message.text)

        if user_answer == correct_answer:
            user["bank"] += 100
            save_users()

            bot.send_message(
                message.chat.id,
                f"Правильно!\n+100\nБанк: {user['bank']}"
            )
        else:
            bot.send_message(message.chat.id, "Невірна відповідь.")

    except:
        bot.send_message(message.chat.id, "Потрібно ввести число.")

    main_menu(message.chat.id)


# ==========================
# RUN
# ==========================

bot.infinity_polling(skip_pending=True)