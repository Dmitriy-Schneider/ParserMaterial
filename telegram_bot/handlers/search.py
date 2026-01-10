"""Search handler with AI context understanding"""
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import config
from context_analyzer import get_context_analyzer


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
    """Handle direct text messages with automatic intent recognition"""
    message_text = update.message.text.strip()

    # Ignore very short or long messages
    if len(message_text) < 2 or len(message_text) > 100:
        return

    # Analyze intent using GPT-4 mini
    analyzer = get_context_analyzer()
    analysis = analyzer.analyze_message(message_text)

    intent = analysis.get('intent', 'search')
    grade = analysis.get('grade')

    # Route to appropriate handler based on intent
    if intent == 'stats':
        # Import stats handler
        from . import stats
        await stats.stats_command(update, context)
        return

    elif intent == 'help':
        # Import help handler
        from . import help_command
        await help_command.help_command(update, context)
        return

    elif intent == 'analogues' and grade:
        # Import analogues handler
        from . import analogues
        # Manually set args for analogues command
        context.args = [grade]
        await analogues.analogues_command(update, context)
        return

    # Default: search
    # Use extracted grade or original message
    search_query = grade if grade else message_text
    await perform_search(update, search_query)


async def perform_search(update: Update, grade_name: str):
    """Perform steel grade search with AI fallback"""
    try:
        # Send "searching" message with progress indication
        status_msg = await update.message.reply_text(
            f"🔍 Ищу марку `{grade_name}`...\n\n"
            f"▪️ Проверка в базе данных (10,394 марок)\n"
            f"▪️ Если не найдено → AI Search через Perplexity (20-30 сек)\n\n"
            f"⏳ Пожалуйста, подождите...",
            parse_mode='Markdown'
        )

        # Make API request with AI fallback enabled
        response = requests.get(
            config.SEARCH_ENDPOINT,
            params={
                'grade': grade_name,
                'ai': 'true'  # Enable AI fallback (Perplexity priority)
            },
            timeout=60  # Increased timeout for AI search (Perplexity can take 20-30 sec)
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
            # Clear "not found" message
            await update.message.reply_text(
                f"❌ **Марка `{grade_name}` не найдена**\n\n"
                f"Поиск выполнен:\n"
                f"• ✓ В базе данных (10,394 марок)\n"
                f"• ✓ Через Perplexity AI (интернет-поиск)\n"
                f"• ✓ Проверено в нескольких источниках\n\n"
                f"**Результат:** Химический состав и аналоги не найдены.\n\n"
                f"Попробуйте:\n"
                f"• Проверить написание марки\n"
                f"• Использовать альтернативное обозначение\n"
                f"• Уточнить производителя или стандарт",
                parse_mode='Markdown'
            )
            return

        # Format and send results
        for i, result in enumerate(results[:config.MAX_RESULTS_PER_MESSAGE], 1):
            message = format_steel_result(result, i, len(results))

            # Send message without buttons (removed all button functionality)
            await update.message.reply_text(message, parse_mode='Markdown')

        # If more results exist
        if len(results) > config.MAX_RESULTS_PER_MESSAGE:
            await update.message.reply_text(
                f"⚠️ Показаны первые {config.MAX_RESULTS_PER_MESSAGE} из {len(results)} результатов."
            )

    except requests.exceptions.Timeout:
        await update.message.reply_text(
            "⏱️ Превышено время ожидания поиска (возможно AI обрабатывает запрос).\n"
            "Попробуйте позже."
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
        ai_source = result.get('ai_source', 'ai').upper()
        header += f" 🤖 ({ai_source})"
    if total > 1:
        header += f" ({index}/{total})"

    # Basic info
    lines = [header, ""]

    # Validation warning (if failed)
    if is_ai and not result.get('validated', True):
        lines.append("⚠️ **ВНИМАНИЕ:** Данные не прошли полную валидацию")
        lines.append("")

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
        if value and value not in ['0', '0.00', None, 'null']:
            lines.append(f"  • {symbol}: {value}%")
            composition_found = True

    if not composition_found:
        lines.append("  _Химический состав не найден_")

    # Analogues
    analogues = result.get('analogues')
    if analogues:
        # Check for "not found" messages
        if 'не найден' in str(analogues).lower() or 'уникальная' in str(analogues).lower():
            lines.append(f"\n🔗 **Аналоги:** _Аналоги не найдены (уникальная марка)_")
        elif analogues not in [None, '', 'N/A', 'null']:
            lines.append(f"\n🔗 **Аналоги:** {analogues}")

    # Application (if available from AI)
    application = result.get('application')
    if application and application not in ['null', None, '']:
        lines.append(f"\n💡 **Применение:**\n_{application}_")

    # Properties (if available from AI)
    properties = result.get('properties')
    if properties and properties not in ['null', None, '']:
        lines.append(f"\n⚙️ **Свойства:**\n_{properties}_")

    # Source information and link
    source_url = result.get('link') or result.get('source_url')

    if is_ai:
        ai_src = result.get('ai_source', 'AI')
        lines.append(f"\n🌐 **Источник данных:** {ai_src.upper()}")

        # Show if from PDF
        if result.get('pdf_extracted'):
            pdf_url = result.get('pdf_source', 'PDF datasheet')
            lines.append(f"📄 Данные извлечены из PDF спецификации")

        # Show validation status
        if result.get('validated', True):
            lines.append("✅ Данные прошли валидацию")
        else:
            lines.append("⚠️ Данные требуют проверки")

    # Add source link if available (for both AI and DB results)
    if source_url and source_url not in ['null', None, '', 'N/A']:
        # Format as Markdown link for cleaner appearance
        lines.append(f"\n🔗 [Ссылка на источник]({source_url})")

    return '\n'.join(lines)


async def handle_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button callbacks"""
    query = update.callback_query
    await query.answer()

    # Parse callback data
    action, grade_name = query.data.split(':', 1)

    if action == 'add':
        # Get AI result from cache to add to database
        try:
            # Request API to get full result
            response = requests.get(
                f"{config.SEARCH_ENDPOINT}?grade={grade_name}&ai=true",
                timeout=10
            )

            if response.status_code == 200:
                results = response.json()
                if results and len(results) > 0:
                    result = results[0]

                    # Call API to add to database
                    add_response = requests.post(
                        f"{config.SEARCH_ENDPOINT.replace('/steels', '/steels/add')}",
                        json=result,
                        timeout=10
                    )

                    if add_response.status_code == 200:
                        await query.edit_message_text(
                            f"✅ Марка `{grade_name}` добавлена в базу данных!",
                            parse_mode='Markdown'
                        )
                    else:
                        error = add_response.json().get('error', 'Unknown error')
                        await query.edit_message_text(
                            f"❌ Ошибка добавления: {error}",
                            parse_mode='Markdown'
                        )
                else:
                    await query.edit_message_text(
                        f"❌ Данные для `{grade_name}` не найдены",
                        parse_mode='Markdown'
                    )
            else:
                await query.edit_message_text(
                    f"❌ Ошибка получения данных: {response.status_code}",
                    parse_mode='Markdown'
                )

        except Exception as e:
            await query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                parse_mode='Markdown'
            )

    elif action == 'del':
        # Delete from database
        try:
            response = requests.post(
                f"{config.SEARCH_ENDPOINT.replace('/steels', '/steels/delete')}",
                json={'grade': grade_name},
                timeout=10
            )

            if response.status_code == 200:
                await query.edit_message_text(
                    f"✅ Марка `{grade_name}` удалена из базы данных!",
                    parse_mode='Markdown'
                )
            else:
                error = response.json().get('error', 'Unknown error')
                await query.edit_message_text(
                    f"❌ Ошибка удаления: {error}",
                    parse_mode='Markdown'
                )

        except Exception as e:
            await query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                parse_mode='Markdown'
            )
