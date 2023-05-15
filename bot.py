import os
import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    ContextTypes, 
    CommandHandler, 
    Updater, 
    CallbackContext, 
    ConversationHandler, 
    CallbackQueryHandler, 
    MessageHandler,
    filters,
)

TOKEN = str(os.environ.get('TELEGRAM_TOKEN'))
SETUP, CONFIGURING = range(2)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
    	chat_id=update.effective_chat.id, 
    	text="Buenas! Soy el Cobrador del Frac!\n\n"
    	"Antes de empezar, necesito que me configures.\n" 
    	"Puedes llamar a /setup para empezar la configuración, o /help para ver todos los comandos disponibles."
    	)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
    	chat_id=update.effective_chat.id, 
    	text="Aquí tienes los comandos disponibles:\n\n"
        "/help - Lista todos los comandos disponibles y su significado\n"
        "/setup - Configura el bot para empezar a recordar las deudas pendientes\n"
        "/settle - Una vez pagado, librate de mas insultos marcandote como pagado con este comando"
    	)

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
    	chat_id=update.effective_chat.id, 
    	text="Vamos a empezar la configuración. Necesito la siguiente información:\n\n"
        "1. En que fecha se tiene que pagar anualmente? (Introducela en este formato: DD/MM/YYYY)\n"
        "2. Que cantidad tiene que pagar cada miembro anualmente?"
    	)
    return CONFIGURING

async def configure_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Save the reminder_date and annual_amount for later use
    reminder_date = datetime.datetime.strptime(update.message.text, "%d/%m/%Y").date()
    annual_amount = update.message.text

    await update.message.reply_text(
        f"Perfecto! El Cobrador del Frac vendra a buscaros cada {reminder_date.strftime('%d/%m/%Y')} por la siguiente cantidad: {annual_amount}€.\n\n"
    )
    return ConversationHandler.END

async def daily_reminder(context: CallbackContext) -> None:
    """TODO: Send a daily reminder about outstanding debts."""
    # Fetch the outstanding debts for each member and send the reminders


async def settle(update: Update, context: CallbackContext) -> None:
    """TODO: Handle the /settle command to tag the user as debt-free."""
    # Mark the user as debt-free

async def cancel(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Configuración cancelada.")
    return ConversationHandler.END


if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("setup", setup)],
        states={
            CONFIGURING: [MessageHandler(filters.Regex(r"^\d{2}/\d{2}/\d{4}$"), configure_reminders)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("settle", settle))
    
    app.run_polling()