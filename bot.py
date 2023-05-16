import os
import logging
import datetime
import pytz
import json
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    ContextTypes,
    Updater, 
    ConversationHandler, 
    CallbackQueryHandler, 
    MessageHandler,
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

members = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

@restricted
async def start(update, context):
    await context.bot.send_message(
    	chat_id=update.effective_chat.id, 
    	text="Buenas! Soy el Cobrador del Frac!\n\n"
    	"Antes de empezar, necesito que me configures.\n" 
    	"Puedes llamar a /setup para empezar la configuración, o /help para ver todos los comandos disponibles."
    )

@restricted
async def status(update, context):
    if 'annual_amount' in context.user_data and 'reminder_date' in context.user_data:
        reminder_date = context.user_data['reminder_date']
        annual_amount = context.user_data['annual_amount']

        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"El Cobrador del Frac vendrá a buscaros cada {reminder_date.strftime('%d/%m')} "
            f"por la siguiente cantidad: {annual_amount}€."
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="El chat aun no ha sido configurado"
        )

@restricted
async def help_command(update, context):
    await context.bot.send_message(
    	chat_id=update.effective_chat.id, 
    	text="Aquí tienes los comandos disponibles:\n\n"
        "/help - Lista todos los comandos disponibles y su significado\n"
        "/setup - Configura el bot para empezar a recordar las deudas pendientes\n"
        "/status - Consulta la configuración actual\n"
        "/settle - Una vez pagado, librate de mas insultos marcandote como pagado con este comando"
    )

@restricted
@admin
async def setup(update, context):
    reply_keyboard = [
        [
            InlineKeyboardButton("Enviar fecha", callback_data='date'),
            InlineKeyboardButton("Enviar cantidad", callback_data='amount')
        ]
    ]

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Vamos a empezar la configuración. Selecciona una opción:",
        reply_markup=InlineKeyboardMarkup(reply_keyboard)
    )
    return SETUP

async def configure_option(update, context):
    query = update.callback_query
    option = query.data
    await query.answer()
    
    if option == 'date':
        await query.message.reply_text("Por favor, selecciona la fecha en que se debe pagar anualmente:")
        return CONFIGURING_DATE
    elif option == 'amount':
        await query.message.reply_text("Por favor, envía la cantidad que se debe pagar anualmente:")
        return CONFIGURING_AMOUNT
    else:
        await query.message.reply_text("Opción inválida. Por favor, intenta nuevamente.")
        return SETUP

async def capture_date(update, context):
    user_input = update.message.text

    try:
        reminder_date = datetime.datetime.strptime(user_input, "%d/%m").date()
        # Save the reminder_date for later use
        context.user_data['reminder_date'] = reminder_date
        await update.message.reply_text("Fecha configurada exitosamente.")
        if 'annual_amount' in context.user_data:
            await complete_setup(update, context)  # Proceed to complete setup if both date and amount are available
        else:
            await update.message.reply_text("Por favor, envía la cantidad que se debe pagar anualmente:")
            return CONFIGURING_AMOUNT  # Ask for the amount
    except ValueError:
        await update.message.reply_text("Fecha inválida. Por favor, intenta nuevamente. (Formato: dd/mm)")

async def capture_amount(update, context):    
    user_input = update.message.text    
    
    try:
        annual_amount = float(user_input)
        # Save the annual_amount for later use
        context.user_data['annual_amount'] = annual_amount
        await update.message.reply_text("Cantidad configurada exitosamente.")
        if 'reminder_date' in context.user_data:
            await complete_setup(update, context)  # Proceed to complete setup if both date and amount are available
        else:
            await update.message.reply_text("Por favor, selecciona la fecha en que se debe pagar anualmente:")
            return CONFIGURING_DATE  # Ask for the date
    except ValueError:
        await update.message.reply_text("Cantidad inválida. Por favor, intenta nuevamente.")

async def complete_setup(update, context):
    reminder_date = context.user_data['reminder_date']
    annual_amount = context.user_data['annual_amount']

    await update.message.reply_text(
        f"Configuración completada.\n\n"
        f"El Cobrador del Frac vendrá a buscaros cada {reminder_date.strftime('%d/%m')} "
        f"por la siguiente cantidad: {str(int(annual_amount))}€."
    )

    chat_id = update.message.chat_id

    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs: job.schedule_removal()
    
    context.job_queue.run_daily(check_date, datetime.time(hour=8, minute=00, tzinfo=pytz.timezone('Europe/Madrid')), chat_id=chat_id, data=(reminder_date,annual_amount), name=str(chat_id))

    return ConversationHandler.END

async def check_date(context):
    current_date = datetime.datetime.now(pytz.timezone('Europe/Madrid')).strftime("%d/%m")
    reminder_date = context.job.data[0].strftime('%d/%m')
    annual_amount = context.job.data[1]

    if current_date == reminder_date:
        global members
        members = {558352770:'mtona86', 54997365:'kRowone', 328961319:'mjubany', 27197845:'Collinmcrae', 205924861:'h4ng3r'}
        await context.bot.send_message(chat_id=context.job.chat_id, text="Ha llegado el dia, morosos!")
    

    for member in members:
        username = members[member]
        
        message = f"[@{username}](tg://user?id={str(member)}): Debes {str(int(annual_amount))}€ a [@anxoveta](tg://user?id=47095626). Paga la coca, primer aviso"
        await context.bot.send_message(chat_id=context.job.chat_id, text=message, parse_mode="Markdown")

@restricted
async def settle(update, context):
    # Mark the user as debt-free
    userid = update.message.from_user['id']
    username = update.message.from_user['username']

    global members
    if userid in members:
        del members[userid]

        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"[@{username}](tg://user?id={str(userid)}) ha sido liberado. Actualiza el [Excel](https://docs.google.com/spreadsheets/d/1y0SWXqF0I2mEOPvtsfjj23dDXEMh76g9JiihlNB7T_Q/edit?usp=drivesdk) Bitch!", 
            parse_mode="Markdown")
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Tu no debias nada, parguela", 
            parse_mode="Markdown")

@restricted
@admin
async def cancel(update, context):
    await update.message.reply_text("Configuración cancelada.")
    return ConversationHandler.END


if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("setup", setup)],
        states={
            SETUP: [CallbackQueryHandler(configure_option)],
            CONFIGURING_DATE: [MessageHandler(filters.TEXT & (~filters.COMMAND), capture_date)],
            CONFIGURING_AMOUNT: [MessageHandler(filters.TEXT & (~filters.COMMAND), capture_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("settle", settle))
    
    app.run_polling()