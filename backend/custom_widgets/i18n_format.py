from typing import Dict, Union, Any

from aiogram_dialog.api.protocols import DialogManager
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.text import Format
from fluentogram import TranslatorRunner
import logging

from backend.locale_config import i18n

logger = logging.getLogger(__name__)

class I18NFormat(Format):
    def __init__(self, key: str, args: Union[Dict[str, Any], None] = None, when: WhenCondition = None):
        super().__init__(key, when)
        self.key = key
        self.args = args

    async def _render_text(self, data: Dict, manager: DialogManager) -> str:
        #i18n: TranslatorRunner = manager.middleware_data.get('i18n')
        #if not i18n:
            #return f"[Ошибка: переводчик не найден для ключа {self.key}]"
        
        try:
            # Первая попытка перевода с полученными данными
            #value = i18n.get(self.key, **self.args)
            if self.args:
                self.text = i18n.format_value(self.key, self.args)
                logger.info(f"Текст для ключа {self.key}: {self.text}")
                value = await super()._render_text(data, manager)
            else:
                value = i18n.format_value(self.key)
            if value is None:
                raise KeyError(f'translation key = "{self.key}" not found')
            return value

        except Exception as e:
            # Если не хватает переменных, логируем ошибку и пробуем добавить недостающие
            error_msg = str(e)
            logger.exception(f"Ошибка локализации для ключа {self.key}: {error_msg}")
