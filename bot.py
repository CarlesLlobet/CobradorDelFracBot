import os
import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
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
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

TOKEN = str(os.environ.get('TELEGRAM_TOKEN'))
SETUP, CONFIGURING_DATE, CONFIGURING_AMOUNT = range(3)

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

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
    	chat_id=update.effective_chat.id, 
    	text="Aquí tienes los comandos disponibles:\n\n"
        "/help - Lista todos los comandos disponibles y su significado\n"
        "/setup - Configura el bot para empezar a recordar las deudas pendientes\n"
        "/status - Consulta la configuración actual\n"
        "/settle - Una vez pagado, librate de mas insultos marcandote como pagado con este comando"
    )

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def configure_option(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    option = query.data
    await query.answer()
    
    if option == 'date':
        await query.message.reply_text("Por favor, selecciona la fecha en que se debe pagar anualmente:")
        logging.info("DATE")
        return CONFIGURING_DATE
    elif option == 'amount':
        await query.message.reply_text("Por favor, envía la cantidad que se debe pagar anualmente:")
        return CONFIGURING_AMOUNT
    else:
        await query.message.reply_text("Opción inválida. Por favor, intenta nuevamente.")
        return SETUP

async def capture_date(update: Update, context: CallbackContext) -> None:
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
        await update.message.reply_text("Fecha inválida. Por favor, intenta nuevamente.")

async def capture_amount(update: Update, context: CallbackContext) -> None:    
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

async def complete_setup(update: Update, context: CallbackContext) -> None:
    reminder_date = context.user_data['reminder_date']
    annual_amount = context.user_data['annual_amount']

    await update.message.reply_text(
        f"Configuración completada.\n\n"
        f"El Cobrador del Frac vendrá a buscaros cada {reminder_date.strftime('%d/%m')} "
        f"por la siguiente cantidad: {annual_amount}€."
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