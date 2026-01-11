"""Fuzzy Search handler - Find similar steel grades by chemical composition"""
import requests
from telegram import Update
from telegram.ext import ContextTypes
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import config


async def fuzzy_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /fuzzy command"""
    if not context.args:
        await update.message.reply_text(
            "🔗 **Fuzzy Search - Поиск похожих марок**\n\n"
            "Укажите марку стали для поиска аналогов по химсоставу.\n\n"
            "**Примеры:**\n"
            "`/fuzzy HARDOX 500`\n"
            "`/fuzzy 4140`\n"
            "`/fuzzy 1.2379`\n\n"
            "**Параметры (опционально):**\n"
            "`/fuzzy <марка> <tolerance> <max_results>`\n"
            "`/fuzzy HARDOX 500 50 10` - допуск 50%, макс 10 результатов",
            parse_mode='Markdown'
        )
        return

    # Parse arguments
    grade_name = context.args[0]
    tolerance = float(context.args[1]) if len(context.args) > 1 else 50.0
    max_results = int(context.args[2]) if len(context.args) > 2 else 10

    # Validate parameters
    if not (0 <= tolerance <= 100):
        await update.message.reply_text(
            "❌ Допуск должен быть от 0 до 100%"
        )
        return

    if not (1 <= max_results <= 50):
        await update.message.reply_text(
            "❌ Макс результатов должно быть от 1 до 50"
        )
        return

    await perform_fuzzy_search(update, grade_name, tolerance, max_results)


async def perform_fuzzy_search(update: Update, grade_name: str, tolerance: float = 50.0, max_results: int = 10):
    """Perform fuzzy search for similar steel grades"""
    try:
        # Send "searching" message
        status_msg = await update.message.reply_text(
            f"🔗 Ищу марки похожие на `{grade_name}`...\n\n"
            f"▪️ Поиск в базе данных (10,394 марок)\n"
            f"▪️ Сравнение химсостава с допуском {tolerance}%\n"
            f"▪️ Макс результатов: {max_results}\n\n"
            f"⏳ Пожалуйста, подождите...",
            parse_mode='Markdown'
        )

        # First, try to get reference grade from database
        response = requests.get(
            config.SEARCH_ENDPOINT,
            params={'grade': grade_name, 'exact': 'true'},
            timeout=10
        )

        if response.status_code != 200:
            await status_msg.edit_text(
                f"❌ Ошибка поиска: {response.status_code}"
            )
            return

        results = response.json()

        # If not found in database, try AI Search
        if not results or len(results) == 0:
            await status_msg.edit_text(
                f"🔗 Марка `{grade_name}` не найдена в базе...\n\n"
                f"🤖 Пытаюсь найти через AI Search (Perplexity)...\n\n"
                f"⏳ Пожалуйста, подождите 20-30 сек...",
                parse_mode='Markdown'
            )

            # Try AI search
            ai_response = requests.get(
                config.SEARCH_ENDPOINT,
                params={'grade': grade_name, 'ai': 'true'},
                timeout=60
            )

            if ai_response.status_code == 200:
                results = ai_response.json()

            if not results or len(results) == 0:
                await status_msg.edit_text(
                    f"❌ **Марка `{grade_name}` не найдена**\n\n"
                    f"Не найдена ни в базе данных (10,394 марок), ни через AI Search.\n\n"
                    f"Попробуйте проверить название марки.",
                    parse_mode='Markdown'
                )
                return

        # Get reference grade data
        reference_grade = results[0]

        # Prepare grade data for fuzzy search
        grade_data = {
            'grade': reference_grade.get('grade'),
            'c': reference_grade.get('c'),
            'cr': reference_grade.get('cr'),
            'ni': reference_grade.get('ni'),
            'mo': reference_grade.get('mo'),
            'v': reference_grade.get('v'),
            'w': reference_grade.get('w'),
            'co': reference_grade.get('co'),
            'mn': reference_grade.get('mn'),
            'si': reference_grade.get('si'),
            'cu': reference_grade.get('cu'),
            'nb': reference_grade.get('nb'),
            'n': reference_grade.get('n'),
            's': reference_grade.get('s'),
            'p': reference_grade.get('p')
        }

        # Call Fuzzy Search API
        fuzzy_response = requests.post(
            f"{config.SEARCH_ENDPOINT.replace('/steels', '/steels/fuzzy-search')}",
            json={
                'grade_data': grade_data,
                'tolerance_percent': tolerance,
                'max_results': max_results
            },
            timeout=30
        )

        if fuzzy_response.status_code != 200:
            await status_msg.edit_text(
                f"❌ Ошибка Fuzzy Search: {fuzzy_response.status_code}"
            )
            return

        fuzzy_results = fuzzy_response.json()

        # Delete "searching" message
        await status_msg.delete()

        if not fuzzy_results.get('success') or fuzzy_results.get('found_count', 0) == 0:
            await update.message.reply_text(
                f"❌ **Похожие марки для `{grade_name}` не найдены**\n\n"
                f"Попробуйте:\n"
                f"• Увеличить допуск (tolerance): `/fuzzy {grade_name} 75 10`\n"
                f"• Проверить что марка имеет химический состав",
                parse_mode='Markdown'
            )
            return

        # Format and send results
        await send_fuzzy_results(update, reference_grade, fuzzy_results)

    except requests.exceptions.Timeout:
        await update.message.reply_text(
            "⏱️ Превышено время ожидания поиска.\n"
            "Попробуйте позже."
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}"
        )


async def send_fuzzy_results(update: Update, reference_grade: dict, fuzzy_results: dict):
    """Send fuzzy search results to user"""
    results = fuzzy_results.get('results', [])
    found_count = fuzzy_results.get('found_count', 0)
    tolerance = fuzzy_results.get('tolerance', 50)
    reference_name = fuzzy_results.get('reference_grade', 'Unknown')

    # Header message
    header = (
        f"🔗 **Fuzzy Search Results**\n\n"
        f"**Эталон:** `{reference_name}`\n"
        f"**Допуск:** {tolerance}%\n"
        f"**Найдено:** {found_count} похожих марок\n"
    )

    # Add reference composition
    ref_comp_parts = []
    for elem in ['c', 'cr', 'mo', 'ni', 'mn', 'si']:
        value = reference_grade.get(elem)
        if value and value not in ['0', '0.00', None, 'null']:
            ref_comp_parts.append(f"{elem.upper()}:{value}")

    if ref_comp_parts:
        header += f"**Состав эталона:** {', '.join(ref_comp_parts)}\n"

    header += "\n" + "─" * 30 + "\n"

    await update.message.reply_text(header, parse_mode='Markdown')

    # Send results (max 5 per message to avoid limits)
    max_per_message = 5
    for i, result in enumerate(results[:15], 1):  # Max 15 results total
        message = format_fuzzy_result(result, i)
        await update.message.reply_text(message, parse_mode='Markdown')

        # If sent 5, send "more results" indicator
        if i == max_per_message and found_count > max_per_message:
            await update.message.reply_text(
                f"⬇️ ⬇️ ⬇️",
                parse_mode='Markdown'
            )

    # If more results exist
    if found_count > 15:
        await update.message.reply_text(
            f"⚠️ Показаны первые 15 из {found_count} результатов.\n"
            f"Для более точного поиска уменьшите допуск."
        )


def format_fuzzy_result(result: dict, index: int) -> str:
    """Format single fuzzy search result"""
    grade = result.get('grade', 'N/A')
    similarity = result.get('similarity', 0)

    # Determine similarity badge
    if similarity >= 80:
        badge = "🟢 Отлично"
    elif similarity >= 60:
        badge = "🟡 Хорошо"
    else:
        badge = "🟠 Удовл."

    lines = [
        f"**{index}. {grade}** - {badge} ({similarity}%)"
    ]

    # Chemical composition (compact format)
    comp_parts = []
    for elem in ['c', 'cr', 'mo', 'ni', 'mn', 'si', 'v', 'w']:
        value = result.get(elem)
        if value and value not in ['0', '0.00', None, 'null']:
            comp_parts.append(f"{elem.upper()}:{value}")

    if comp_parts:
        lines.append(f"  📊 {', '.join(comp_parts)}")

    # Standard only (NO analogues - fuzzy search shows similar grades, not official analogues)
    standard = result.get('standard')
    if standard and standard not in ['null', None, '']:
        lines.append(f"  📋 {standard}")

    # Source link
    source_url = result.get('link')
    if source_url and source_url not in ['null', None, '', 'N/A']:
        lines.append(f"  🌐 [Источник]({source_url})")

    lines.append("")  # Empty line for separation

    return '\n'.join(lines)
