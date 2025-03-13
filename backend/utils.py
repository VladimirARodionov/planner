import html
from typing import Any, Optional, Union

def escape_html(text: Optional[Union[str, Any]]) -> str:
    """
    Экранирует специальные HTML-символы в тексте.
    
    Args:
        text: Текст для экранирования или любой другой объект, который будет преобразован в строку.
        
    Returns:
        Экранированная строка или пустая строка, если text is None.
    """
    if text is None:
        return ""
    return html.escape(str(text)) 