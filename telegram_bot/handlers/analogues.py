"""Analogues search handler"""
import requests
from telegram import Update
from telegram.ext import ContextTypes

import config


async def analogues_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /analogues command"""
    if not context.args:
        await update.message.reply_text(
            "Укажите марку для поиска аналогов.\nПример: `/analogues AISI 304`",
            parse_mode='Markdown'
        )
        return

    grade_name = ' '.join(context.args)

    try:
        # Send "searching" message
        status_msg = await update.message.reply_text(
            f"🔍 Ищу аналоги для `{grade_name}`...",
            parse_mode='Markdown'
        )

        # First, find the grade (exact match only)
        response = requests.get(
            config.SEARCH_ENDPOINT,
            params={'grade': grade_name, 'exact': 'true'},
            timeout=30
        )

        if response.status_code != 200:
            await status_msg.edit_text(
                f"❌ Ошибка поиска: {response.status_code}"
            )
            return

        results = response.json()

        # Delete "searching" message
        await status_msg.delete()

        if not results:
            await update.message.reply_text(
                f"❌ Марка `{grade_name}` не найдена в базе данных.",
                parse_mode='Markdown'
            )
            return

        # Get the first result
        steel = results[0]

        # Format analogues message
        message = format_analogues(steel)
        await update.message.reply_text(message, parse_mode='Markdown')

    except requests.exceptions.Timeout:
        await update.message.reply_text(
            "⏱️ Превышено время ожидания. Попробуйте позже."
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}"
        )


def format_analogues(steel: dict) -> str:
    """Format analogues information"""
    grade = steel.get('grade', 'N/A')
    analogues = steel.get('analogues', '')

    lines = [
        f"🔗 **Аналоги для: {grade}**",
        ""
    ]

    if analogues and analogues not in [None, '', 'N/A']:
        lines.append("**Мировые аналоги:**")
        # Split by space or comma
        analogue_list = analogues.replace(',', ' ').split()
        for analogue in analogue_list:
            if analogue:
                lines.append(f"  • {analogue}")
    else:
        lines.append("_Аналоги не найдены в базе данных._")
        lines.append("\nПопробуйте использовать `/search` для поиска похожих марок по химическому составу.")

    # Add composition for reference
    lines.append("\n**Химический состав исходной марки:**")
    composition_found = False

    elements = ['C', 'Cr', 'Ni', 'Mo', 'V', 'W']
    for element in elements:
        value = steel.get(element.lower())
        if value and value not in ['0', '0.00', None]:
            lines.append(f"  • {element}: {value}%")
            composition_found = True

    if not composition_found:
        lines.append("  _Состав не указан_")

    return '\n'.join(lines)
