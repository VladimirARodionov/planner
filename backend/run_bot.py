from telegram.ext import (
     ApplicationBuilder,
)
import os, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

from telegram_django_bot.tg_dj_bot import TG_DJ_Bot
from telegram_django_bot.routing import RouterCallbackMessageCommandHandler

from backend.settings import TELEGRAM_TOKEN, TELEGRAM_LOG, DEBUG
import logging


def add_handlers(updater):
    dp = updater.dispatcher
    dp.add_handler(RouterCallbackMessageCommandHandler())


def main():
    if not DEBUG:
        logging.basicConfig(
            filename=TELEGRAM_LOG,
            filemode='a',
            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
            datefmt='%Y.%m.%d %H:%M:%S',
            level=logging.INFO
        )

    bot = TG_DJ_Bot(TELEGRAM_TOKEN)
    application = ApplicationBuilder().bot(bot).build()
    application.add_handler(RouterCallbackMessageCommandHandler())
    application.run_polling()
    #application.idle()


if __name__ == '__main__':
    main()

