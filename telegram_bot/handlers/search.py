"""Search handler"""
import requests
from telegram import Update
from telegram.ext import ContextTypes

import config


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command"""
    if not context.args:
        await update.message.reply_text(
            "Укажите марку стали для поиска.\nПример: `/search 420`",
            parse_mode='Markdown'
        )
        return

    grade_name = ' '.join(context.args)
    await perform_search(update, grade_name)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle direct text messages as search queries"""
    grade_name = update.message.text.strip()

    # Ignore very short or long messages
    if len(grade_name) < 2 or len(grade_name) > 50:
        return

    await perform_search(update, grade_name)


async def perform_search(update: Update, grade_name: str):
    """Perform steel grade search"""
    try:
        # Send "searching" message
        status_msg = await update.message.reply_text(
            f"🔍 Ищу марку `{grade_name}`...",
            parse_mode='Markdown'
        )

        # Make API request
        response = requests.get(
            config.SEARCH_ENDPOINT,
            params={'grade': grade_name},
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
                f"❌ Марка `{grade_name}` не найдена.\n\n"
                f"Попробуйте:\n"
                f"• Проверить написание\n"
                f"• Использовать другое обозначение\n"
                f"• Использовать `/analogues` для поиска похожих марок",
                parse_mode='Markdown'
            )
            return

        # Format and send results
        for i, result in enumerate(results[:config.MAX_RESULTS_PER_MESSAGE], 1):
            message = format_steel_result(result, i, len(results))
            await update.message.reply_text(message, parse_mode='Markdown')

        # If more results exist
        if len(results) > config.MAX_RESULTS_PER_MESSAGE:
            await update.message.reply_text(
                f"⚠️ Показаны первые {config.MAX_RESULTS_PER_MESSAGE} из {len(results)} результатов."
            )

    except requests.exceptions.Timeout:
        await update.message.reply_text(
            "⏱️ Превышено время ожидания. Попробуйте позже."
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}"
        )


def format_steel_result(result: dict, index: int = 1, total: int = 1) -> str:
    """Format steel grade result for display"""
    # Header
    grade = result.get('grade', 'N/A')
    is_ai = result.get('id') == 'AI'

    header = f"🔧 **Марка: {grade}**"
    if is_ai:
        header += " 🤖 (AI)"
    if total > 1:
        header += f" ({index}/{total})"

    # Basic info
    lines = [header, ""]

    # Standard and manufacturer
    standard = result.get('standard')
    manufacturer = result.get('manufacturer')

    if standard:
        lines.append(f"📋 **Стандарт:** {standard}")
    if manufacturer:
        lines.append(f"🏭 **Производитель:** {manufacturer}")

    # Chemical composition
    lines.append("\n**Химический состав:**")

    elements = {
        'C': 'Углерод',
        'Cr': 'Хром',
        'Ni': 'Никель',
        'Mo': 'Молибден',
        'V': 'Ванадий',
        'W': 'Вольфрам',
        'Co': 'Кобальт',
        'Mn': 'Марганец',
        'Si': 'Кремний',
        'Cu': 'Медь',
        'Nb': 'Ниобий',
        'N': 'Азот'
    }

    composition_found = False
    for symbol, name in elements.items():
        value = result.get(symbol.lower())
        if value and value not in ['0', '0.00', None]:
            lines.append(f"  • {symbol}: {value}%")
            composition_found = True

    if not composition_found:
        lines.append("  _Состав не указан_")

    # Analogues
    analogues = result.get('analogues')
    if analogues and analogues not in [None, '', 'N/A']:
        lines.append(f"\n🔗 **Аналоги:** {analogues}")

    # Application (if available from AI)
    application = result.get('application')
    if application:
        lines.append(f"\n💡 **Применение:**\n_{application}_")

    # Properties (if available from AI)
    properties = result.get('properties')
    if properties:
        lines.append(f"\n⚙️ **Свойства:**\n_{properties}_")

    # Source
    if is_ai:
        ai_source = result.get('ai_source', 'AI')
        lines.append(f"\n🌐 Источник: {ai_source.upper()}")

    return '\n'.join(lines)
