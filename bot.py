import os
import logging
import datetime
import pytz
import json
import pickle
from urllib.parse import quote
from functools import wraps
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from telegram import Update, KeyboardButton, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    ContextTypes,
    Updater, 
    ConversationHandler, 
    CallbackQueryHandler, 
    MessageHandler,
    PicklePersistence,
    filters,
)
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

TOKEN = str(os.environ.get('TELEGRAM_TOKEN'))
SETUP, CONFIGURING_DATE, CONFIGURING_AMOUNT = range(3)

LIST_OF_ADMINS = json.loads(os.environ.get('TELEGRAM_ADMINS','[54997365]')) # @kRowone9
def admin(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        chat_id = update.effective_chat.id
        user_id = update.message.from_user['id']
        username = update.message.from_user['username']
        if user_id not in LIST_OF_ADMINS:
            await context.bot.send_message(chat_id=chat_id, 
                text=f"No tienes permisos de administrador para este bot, [@{username}](tg://user?id={str(user_id)}).",
                parse_mode="Markdown")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

LIST_OF_CHATS = json.loads(os.environ.get('TELEGRAM_CHATS', '[-366683659, -346416650]')) # Spotify Family & Naturcenter
def restricted(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        chat_id = update.effective_chat.id
        user_id = update.message.from_user['id']
        if chat_id not in LIST_OF_CHATS:
            if user_id not in LIST_OF_ADMINS:
                await context.bot.send_message(chat_id=chat_id, 
                    text=f"Este bot solo funciona en ciertos chats para optimizar recursos.\n\n"
                    "Si quieres usar este bot en tus propios chats, despliega tu propia instancia:\n"
                    "[Github - CobradorDelFracBot](https://github.com/CarlesLlobet/CobradorDelFracBot/)")
                return
        return await func(update, context, *args, **kwargs)
    return wrapped

def send_typing_action(action):
    """Sends the `Typing... action` while processing func command."""

    def decorator(func):
        @wraps(func)
        async def command_func(update, context, *args, **kwargs):
            await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return await func(update, context,  *args, **kwargs)
        return command_func
    
    return decorator

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

@send_typing_action(ChatAction.TYPING)
@restricted
async def start(update, context):
    await context.bot.send_message(
    	chat_id=update.effective_chat.id, 
    	text="Buenas! Soy el Cobrador del Frac!\n\n"
    	"Antes de empezar, necesito que me configures.\n" 
    	"Puedes llamar a /setup para empezar la configuración, o /help para ver todos los comandos disponibles."
    )

@restricted
@send_typing_action(ChatAction.TYPING)
async def status(update, context):
    try:
        members=pickle.load(open("members.storage","rb"))
    except (EOFError, FileNotFoundError) as e:
        members = None

    if members is not None:
        if 'annual_amount' in context.user_data:
            annual_amount = context.user_data['annual_amount']
        else:
            annual_amount = "0"
        for member in members:
            username = members[member]
            
            message = f"[@{username}](tg://user?id={str(member)}): Debe {str(annual_amount)}€ a [@anxoveta](tg://user?id=47095626)."
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Nadie debe nada!", parse_mode="Markdown")

    if 'annual_amount' in context.user_data and 'reminder_date' in context.user_data:
        reminder_date = context.user_data['reminder_date']
        annual_amount = context.user_data['annual_amount']

        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"El Cobrador del Frac vendrá a buscaros cada {reminder_date.strftime('%d/%m')} "
            f"por la siguiente cantidad: {annual_amount}€."
        )
    elif 'annual_amount' in context.user_data:
        annual_amount = context.user_data['annual_amount']
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"El Cobrador del Frac debe cobrar {annual_amount}€, pero no sabe cuando deberia ir a buscarlos.\n"
                f"Configura una fecha de recordatorio."
        )
    elif 'reminder_date' in context.user_data:
        reminder_date = context.user_data['reminder_date']
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"El Cobrador del Frac tiene que ir a buscaros cada {reminder_date.strftime('%d/%m')}, pero no sabe que cantidad reclamar.\n"
            f"Configura una cantidad a reclamar."
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="El chat aún no ha sido configurado!"
        )

@restricted
@send_typing_action(ChatAction.TYPING)
async def help_command(update, context):
    await context.bot.send_message(
    	chat_id=update.effective_chat.id, 
    	text="Aquí tienes los comandos disponibles:\n\n"
        "/help - Lista todos los comandos disponibles y su significado\n"
        "/status - Consulta las deudas pendientes y configuración actual\n"
        "/settle - Una vez pagado, librate de mas insultos marcandote como pagado con este comando\n"
        "/setup - Configura el bot para empezar a recordar las deudas pendientes\n"
        "/cancel - Cancela la configuración en curso\n"
        "/reset - Elimina cualquier configuración existente"
    )

@restricted
@admin
@send_typing_action(ChatAction.TYPING)
async def setup(update, context):
    reply_keyboard = [
        [
            InlineKeyboardButton("Enviar fecha", callback_data='date'),
            InlineKeyboardButton("Enviar cantidad", callback_data='amount')
        ],
        [InlineKeyboardButton("Cancelar", callback_data='cancel')]
    ]

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Panel de Configuración.\n\n Selecciona una opción:",
        reply_markup=InlineKeyboardMarkup(reply_keyboard)
    )

    return SETUP

async def configure_option(update, context):
    query = update.callback_query
    option = query.data
    await query.answer()
    
    if option == 'date':
        options = {
            "range": False, 
            "locale": "es", 
            "dateFormat": "dd/MM"
        }
        url = f"https://tgdates.hoppingturtles.repl.co?options=" + quote(json.dumps(options))  # url encoded JSON string
        but = KeyboardButton("Seleccionar fecha", web_app=WebAppInfo(url))
        
        await query.delete_message()
        await context.bot.send_message(chat_id=query.message.chat.id, text="Por favor, selecciona la fecha en que se debe pagar anualmente:", reply_markup=ReplyKeyboardMarkup.from_button(but, one_time_keyboard=True))

        return CONFIGURING_DATE
    elif option == 'amount':
        await query.edit_message_text(text="Por favor, envía la cantidad que se debe pagar anualmente:")
        return CONFIGURING_AMOUNT
    elif option == 'cancel':
        await query.edit_message_text(text="Configuración cancelada")
        return ConversationHandler.END
    else:
        await query.message.reply_text("Opción inválida. Por favor, intenta nuevamente.")
        return SETUP

async def capture_date(update, context):
    data = json.loads(update.message.web_app_data.data)

    try:
        reminder_date = datetime.datetime.strptime(data[0], "%Y-%m-%dT%H:%M:%S.%fZ")
        reminder_date += datetime.timedelta(days=1)
        # Save the reminder_date for later use
        context.user_data['reminder_date'] = reminder_date
        await update.message.reply_text(f"Fecha configurada exitosamente: {reminder_date.strftime('%d/%m')}")
        if 'annual_amount' in context.user_data:
            return await complete_setup(update, context)  # Proceed to complete setup if both date and amount are available
        else:
            return await setup(update, context)
    except ValueError:
        await update.message.reply_text("Fecha inválida. Por favor, intenta nuevamente. (Formato: dd/mm)")



async def capture_amount(update, context):    
    user_input = update.message.text    
    
    try:
        annual_amount = int(user_input)
        # Save the annual_amount for later use
        context.user_data['annual_amount'] = annual_amount
        await update.message.reply_text(f"Cantidad configurada exitosamente: {annual_amount}")
        if 'reminder_date' in context.user_data:
            return await complete_setup(update, context)  # Proceed to complete setup if both date and amount are available
        else:
            return await setup(update, context)
    except ValueError:
        await update.message.reply_text("Cantidad inválida. Por favor, intenta nuevamente.")

async def complete_setup(update, context):
    reminder_date = context.user_data['reminder_date']
    annual_amount = context.user_data['annual_amount']

    try:
        members=pickle.load(open("members.storage","rb"))
    except (EOFError, FileNotFoundError) as e:
        members = None

    await update.message.reply_text(
        f"Configuración completada.\n\n"
        f"El Cobrador del Frac vendrá a buscaros cada {reminder_date.strftime('%d/%m')} "
        f"por la siguiente cantidad: {str(annual_amount)}€."
    )

    chat_id = update.message.chat_id

    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs: job.schedule_removal()
    
    context.job_queue.run_daily(check_date, datetime.time(hour=23, minute=30, tzinfo=pytz.timezone('Europe/Madrid')), chat_id=chat_id, data=(reminder_date,annual_amount,members), name=str(chat_id))

    return ConversationHandler.END

async def check_date(context):
    current_date = datetime.datetime.now(pytz.timezone('Europe/Madrid')).strftime("%d/%m")
    reminder_date = context.job.data[0].strftime('%d/%m')
    annual_amount = context.job.data[1]

    try:
        members=pickle.load(open("members.storage","rb"))
    except (EOFError, FileNotFoundError) as e:
        members = None

    if current_date == reminder_date:
        members = {558352770:'mtona86', 54997365:'kRowone', 328961319:'mjubany', 27197845:'Collinmcrae', 205924861:'h4ng3r'}

        with open('members.storage', 'wb') as f:
            pickle.dump(members, f)

        await context.bot.send_message(chat_id=context.job.chat_id, text="Ha llegado el dia, morosos!")
    
    if members is not None:
        for member in members:
            username = members[member]
            
            message = f"[@{username}](tg://user?id={str(member)}): Debes {str(annual_amount)}€ a [@anxoveta](tg://user?id=47095626). Paga la coca, primer aviso"
            await context.bot.send_message(chat_id=context.job.chat_id, text=message, parse_mode="Markdown")

@restricted
@send_typing_action(ChatAction.TYPING)
async def settle(update, context):
    chat_id = update.effective_chat.id
    # Mark the user as debt-free
    if len(context.args) > 0:
        if len(context.args) > 1:
            await context.bot.send_message(chat_id=chat_id, 
                text=f"Solo se puede pasar un usuario como máximo!",
                parse_mode="Markdown")
            return
        else:
            #Check if admin
            user_id = update.message.from_user['id']
            if user_id not in LIST_OF_ADMINS:
                await context.bot.send_message(chat_id=chat_id, 
                    text=f"Solo los administradores pueden saldar cuentas de otros miembros.",
                    parse_mode="Markdown")
                return
            # Look for username
            username = context.args[0]
            if username[0] == "@":
                username = username[1:]
            aux = {'mtona86': 558352770, 'kRowone': 54997365, 'mjubany':328961319, 'Collinmcrae': 27197845, 'h4ng3r':205924861}
            if username in aux:
                userid = aux[username]
            else:
                await context.bot.send_message(chat_id=chat_id, 
                    text=f"@{username} no es un miembro válido",
                    parse_mode="Markdown")
                return
    else:
        userid = update.message.from_user['id']
        username = update.message.from_user['username']

    try:
        members=pickle.load(open("members.storage","rb"))
    except (EOFError, FileNotFoundError) as e:
        members = None

    if members is not None:
        if userid in members:
            del members[userid]
            with open('members.storage', 'wb') as f:
                pickle.dump(members, f)
            await context.bot.send_message(
                chat_id=chat_id, 
                text=f"[@{username}](tg://user?id={str(userid)}) ha sido liberado. Actualiza el [Excel](https://docs.google.com/spreadsheets/d/1y0SWXqF0I2mEOPvtsfjj23dDXEMh76g9JiihlNB7T_Q/edit?usp=drivesdk) Bitch!", 
                parse_mode="Markdown")
        else:
            await context.bot.send_message(
                chat_id=chat_id, 
                text=f"[@{username}](tg://user?id={str(userid)}) no debe nada, parguela", 
                parse_mode="Markdown")
    else:
        await context.bot.send_message(
            chat_id=chat_id, 
            text=f"Nadie debe nada ya, parguela", 
            parse_mode="Markdown")

@restricted
@admin
@send_typing_action(ChatAction.TYPING)
async def cancel(update, context):
    await update.message.reply_text("Configuración cancelada.")
    return ConversationHandler.END

@restricted
@admin
@send_typing_action(ChatAction.TYPING)
async def reset(update, context):
    reminder_date = context.user_data['reminder_date']
    annual_amount = context.user_data['annual_amount']

    if reminder_date or annual_amount:
        del context.user_data['reminder_date']
        del context.user_data['annual_amount']
        await update.message.reply_text("Configuración eliminada.")
    else:
        await update.message.reply_text("El chat aún no ha sido configurado")


if __name__ == '__main__':
    persistence = PicklePersistence(filepath="session.storage")
    app = ApplicationBuilder().token(TOKEN).persistence(persistence).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("settle", settle))
    app.add_handler(CommandHandler("reset", reset))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("setup", setup)],
        states={
            SETUP: [CallbackQueryHandler(configure_option)],
            CONFIGURING_DATE: [MessageHandler(filters.StatusUpdate.WEB_APP_DATA & (~filters.COMMAND), capture_date)],
            CONFIGURING_AMOUNT: [MessageHandler(filters.TEXT & (~filters.COMMAND), capture_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="config",
        persistent=True,
    )
    app.add_handler(conv_handler)
    
    app.run_polling()