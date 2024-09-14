import logging
import json
import os
import time
import random
import asyncio
import requests
from database import ensure_connection
from datetime import datetime
from aiogram.types import InputFile

from aiogram import Dispatcher, html
from aiogram.filters import CommandStart, CommandObject
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.markdown import hlink
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import FSInputFile, InputMediaPhoto
from ping3 import ping
import requests
from bs4 import BeautifulSoup
import re
import os
from states import OrderFood


def register_handlers(dp: Dispatcher, conn, bot):

    @dp.message(CommandStart())
    async def command_start_handler(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        username = message.from_user.username
        async with conn.cursor() as cursor:
            
            start = await ensure_connection(conn)
            print("Good command")
            await cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
            result = await cursor.fetchone()

            if result is None:
                await cursor.execute("INSERT INTO users (user_id, username) VALUES (%s, %s)", (user_id, username))
            await conn.commit()
            

        inline_kb_full = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📞 ADMIN", url="t.me/exfador")]
            ]
        )

        sent_message = await bot.send_message(
            user_id,
            text=(
                "<b>Hello. Give me a link to Pintrest photo </b>\n\n"
            ),
            reply_markup=inline_kb_full, parse_mode='HTML'
        )
        await state.update_data(start_message_id=sent_message.message_id)
        await state.set_state(OrderFood.wait_for_photo)

    def download_image(url, folder_path):
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            file_name = url.split("/")[-1]
            file_path = os.path.join(folder_path, file_name)
            
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f"Downloaded: {file_name}")
        else:
            print(f"Failed to download: {url}")

    def get_image_urls(pinterest_url):
        response = requests.get(pinterest_url)
        if response.status_code != 200:
            print("Failed to fetch the page")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        image_urls = []

        for img in soup.find_all('img', src=re.compile(r'\.jpg|\.png|\.jpeg')):
            img_url = img.get('src')
            if img_url:
                image_urls.append(img_url)

        return image_urls

    def main(pinterest_url, download_folder):
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)

        image_urls = get_image_urls(pinterest_url)
        for img_url in image_urls:
            download_image(img_url, download_folder)     


    @dp.message(OrderFood.wait_for_photo)
    async def photo_handler(message: Message, state: FSMContext) -> None:
        photo_url = message.text
        try:
            user_id = message.from_user.id
            download_folder = f"{user_id}"
            main(photo_url, download_folder)
            
            file_path = os.path.join(download_folder, os.listdir(download_folder)[0])
            
            photo_file = FSInputFile(path=file_path)
            inline = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📞 CHANNEL", url="t.me/naumov_glav")]
            ])
            
            state_data = await state.get_data()
            start_message_id = state_data.get('start_message_id')
            
            try:
                await bot.edit_message_media(
                    chat_id=user_id,
                    message_id=start_message_id,
                    media=InputMediaPhoto(media=photo_file, caption="🔥 | Thanks for the download!\nJoin my channel!"),
                    reply_markup=inline
                )
            except Exception as e:
                if "there is no media in the message to edit" in str(e):
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=photo_file,
                        caption="🔥 | Thanks for the download!\nJoin my channel!",
                        reply_markup=inline
                    )
                else:
                    raise e
            
            await state.set_state(OrderFood.wait_for_photo)
        except Exception as e:
            await message.reply(f"Error... PLease, try again later.")


    @dp.message(Command("admin"))
    async def admin_handler(message: Message, state: FSMContext) -> None:
        async with conn.cursor() as cursor:
            start = await ensure_connection(conn)
            await cursor.execute("SELECT admin FROM users WHERE user_id = %s", (message.from_user.id,))
            result = await cursor.fetchone()
            

            key = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ | Рассылка", callback_data="rass"),
                        InlineKeyboardButton(text="💋 | Статистика", callback_data='users'), 
                    ],
                ]

            )
            if result and result[0] == 1:
                sent_message = await bot.send_message(message.from_user.id, text="MENU-ADMIN. Выбери то, что тебе нужно", reply_markup=key)
                await state.update_data(admin_message_id=sent_message.message_id)
            else:
                await bot.send_message(message.from_user.id, text="Ошибка: вы не администратор!")

 

    @dp.callback_query(lambda call: call.data.startswith("users"))
    async def rass_callback(callback_query: CallbackQuery, state: FSMContext):
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        async with conn.cursor() as cursor:
            start = await ensure_connection(conn)
            await cursor.execute("SELECT admin FROM users WHERE user_id = %s", (callback_query.from_user.id,))
            result = await cursor.fetchone()

            if result and result[0] == 1:
                await cursor.execute("SELECT COUNT(*) FROM users")
                count = await cursor.fetchone()
                

                ip_address = 'www.google.com'
                response = ping(ip_address)
                print(response)
                if response is not None:
                    delay = int(response * 1000)
                    print(delay, " Delay ")
                state_data = await state.get_data()
                admin_message_id = state_data.get('admin_message_id')
                await bot.edit_message_text(
                    chat_id=callback_query.from_user.id,
                    message_id=admin_message_id,
                    text=f"Всего пользователей: {count[0]}\nPing: {delay}"
                )
            else:
                await bot.send_message(callback_query.from_user.id, text="Ошибка: вы не администратор!")
                await state.clear()

    @dp.callback_query(lambda call: call.data.startswith("rass"))
    async def rass_callback(callback_query: CallbackQuery, state: FSMContext):
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        async with conn.cursor() as cursor:
            start = await ensure_connection(conn)
            await cursor.execute("SELECT admin FROM users WHERE user_id = %s", (callback_query.from_user.id,))
            result = await cursor.fetchone()
            

            if result and result[0] == 1:
                state_data = await state.get_data()
                admin_message_id = state_data.get('admin_message_id')
                await bot.edit_message_text(
                    chat_id=callback_query.from_user.id,
                    message_id=admin_message_id,
                    text="Введите текст для рассылки"
                )
                await state.set_state(OrderFood.admin_text)
            else:
                await bot.send_message(callback_query.from_user.id, text="Ошибка: вы не администратор!")
                await state.clear()

    @dp.message(OrderFood.admin_text)
    async def admin_text(message: Message, state: FSMContext) -> None:
        text = message.text

        async with conn.cursor() as cursor:
            start = await ensure_connection(conn)
            await cursor.execute("SELECT user_id FROM users")
            users = await cursor.fetchall()
            

        for user in users:
            user_id = user[0]
            try:
                await bot.send_message(chat_id=user_id, text=f"⚠️ Admin sent a new SMS: \n\n{text}")
            except Exception as e:
                if "chat not found" in str(e):
                    print(f"Chat not found for user ID: {user_id}. Skipping this user.")
                else:
                    print(f"An error occurred while sending message to user ID: {user_id}. Error: {e}")
            except TelegramForbiddenError:
                print(f"User {user_id} has blocked the bot.")

        await state.clear()

    @dp.message(lambda message: not message.text.startswith("/"))
    async def handle_unknown_command(message: Message):
        await message.reply("⚠️ Error: Unknown command. Please use /start to begin.")