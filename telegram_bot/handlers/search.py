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
    await perform_search(update, grade_name, context)


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

    elif intent == 'fuzzy_search' and grade:
        # Import fuzzy_search handler
        from . import fuzzy_search
        # Manually set args for fuzzy_search command
        tolerance = analysis.get('tolerance') or 50
        max_results = analysis.get('max_results') or 1
        context.args = [grade, str(tolerance), str(max_results)]
        await fuzzy_search.fuzzy_search_command(update, context)
        return

    # Default: search
    # Use extracted grade or original message
    search_query = grade if grade else message_text
    await perform_search(update, search_query, context)


async def perform_search(update: Update, grade_name: str, context: ContextTypes.DEFAULT_TYPE = None, force_ai: bool = False):
    """Perform steel grade search with AI confirmation logic"""
    try:
        # Initialize user_data if needed
        if context and 'search_attempts' not in context.user_data:
            context.user_data['search_attempts'] = {}

        # Get normalized grade name for tracking attempts
        normalized_grade = grade_name.strip().upper()

        # Get attempt count for this grade
        attempt_count = 0
        if context:
            attempt_count = context.user_data['search_attempts'].get(normalized_grade, 0)

        # Send "searching" message
        status_msg = await update.message.reply_text(
            f"🔍 Ищу марку `{grade_name}`...\n\n"
            f"▪️ Проверка в базе данных (10,394 марок)\n\n"
            f"⏳ Пожалуйста, подождите...",
            parse_mode='Markdown'
        )

        # Make API request WITHOUT AI fallback (search only in DB)
        # unless force_ai is True
        response = requests.get(
            config.SEARCH_ENDPOINT,
            params={
                'grade': grade_name,
                'ai': 'true' if force_ai else 'false'  # AI only if forced
            },
            timeout=60
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
            # Not found in database - handle based on attempt count
            if context:
                # Increment attempt count
                attempt_count += 1
                context.user_data['search_attempts'][normalized_grade] = attempt_count

            if attempt_count == 1:
                # First attempt - suggest checking spelling
                await update.message.reply_text(
                    f"❌ **Марка `{grade_name}` не найдена в базе данных**\n\n"
                    f"📋 **Проверьте написание марки и попробуйте еще раз:**\n"
                    f"• Возможно, опечатка в названии\n"
                    f"• Попробуйте без пробелов (ШХ15 вместо ШХ 15)\n"
                    f"• Проверьте регистр (AISI 420 вместо aisi 420)\n"
                    f"• Уточните производителя или стандарт\n\n"
                    f"💡 Просто отправьте исправленное название марки.",
                    parse_mode='Markdown'
                )
                return

            elif attempt_count == 2:
                # Second attempt - offer AI search confirmation
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Подтвердить AI Search", callback_data=f'confirm_ai:{grade_name}'),
                    ],
                    [
                        InlineKeyboardButton("✏️ Попробовать еще раз", callback_data=f'retry_search:{grade_name}')
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    f"❌ **Марка `{grade_name}` снова не найдена в базе данных**\n\n"
                    f"🤔 **Что делать дальше?**\n\n"
                    f"**Вариант 1:** Подтвердить поиск с помощью нейронной сети (Perplexity AI)\n"
                    f"  • Займет 20-30 секунд\n"
                    f"  • Данные могут быть неточными\n"
                    f"  • Требуется проверка по ссылке\n\n"
                    f"**Вариант 2:** Попробовать еще раз скорректировать название\n"
                    f"  • Поиск более точной информации в базе данных\n\n"
                    f"Выберите действие:",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                return

            else:
                # Third+ attempt - automatic AI search
                await update.message.reply_text(
                    f"🔍 Марка `{grade_name}` не найдена в базе данных.\n\n"
                    f"🤖 **Автоматический поиск через Perplexity AI...**\n\n"
                    f"⏳ Пожалуйста, подождите 20-30 сек...",
                    parse_mode='Markdown'
                )

                # Perform AI search
                await perform_ai_search(update, grade_name, context)
                return

        else:
            # Found in database - reset attempt counter
            if context and normalized_grade in context.user_data.get('search_attempts', {}):
                del context.user_data['search_attempts'][normalized_grade]

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
            "⏱️ Превышено время ожидания поиска.\n"
            "Попробуйте позже."
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}"
        )


async def perform_ai_search(update: Update, grade_name: str, context: ContextTypes.DEFAULT_TYPE = None):
    """Perform AI search with Perplexity"""
    try:
        status_msg = await update.message.reply_text(
            f"🤖 Ищу марку `{grade_name}` через Perplexity AI...\n\n"
            f"⏳ Пожалуйста, подождите 20-30 сек...",
            parse_mode='Markdown'
        )

        # Make API request with AI enabled
        response = requests.get(
            config.SEARCH_ENDPOINT,
            params={
                'grade': grade_name,
                'ai': 'true'
            },
            timeout=60
        )

        if response.status_code != 200:
            await status_msg.edit_text(
                f"❌ Ошибка AI поиска: {response.status_code}"
            )
            return

        results = response.json()

        # Delete status message
        await status_msg.delete()

        if not results:
            await update.message.reply_text(
                f"❌ **Марка `{grade_name}` не найдена даже через AI Search**\n\n"
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

        # Reset attempt counter after successful AI search
        if context:
            normalized_grade = grade_name.strip().upper()
            if normalized_grade in context.user_data.get('search_attempts', {}):
                del context.user_data['search_attempts'][normalized_grade]

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
            "⏱️ Превышено время ожидания AI поиска.\n"
            "Попробуйте позже."
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка AI поиска: {str(e)}"
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

        # CRITICAL WARNING about AI data accuracy
        lines.append("\n⚠️ **ВАЖНО:** Данные получены через нейронную сеть")
        lines.append("• Информация может быть неточной или неполной")
        lines.append("• **Обязательно проверьте данные** по ссылке ниже")
        lines.append("• Рекомендуем сверить с официальными источниками")

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

    if action == 'confirm_ai':
        # User confirmed AI search
        await query.edit_message_text(
            f"✅ Подтверждено. Запускаю AI Search для марки `{grade_name}`...",
            parse_mode='Markdown'
        )

        # Reset attempt counter and perform AI search
        normalized_grade = grade_name.strip().upper()
        if normalized_grade in context.user_data.get('search_attempts', {}):
            del context.user_data['search_attempts'][normalized_grade]

        # Perform AI search
        # Create a fake update object for perform_ai_search
        class FakeMessage:
            def __init__(self, chat_id):
                self.chat_id = chat_id
                self.message_id = None

            async def reply_text(self, text, parse_mode=None):
                return await query.message.reply_text(text, parse_mode=parse_mode)

        fake_update = type('obj', (object,), {
            'message': FakeMessage(query.message.chat_id)
        })()

        await perform_ai_search(fake_update, grade_name, context)
        return

    elif action == 'retry_search':
        # User wants to try again - just inform them
        await query.edit_message_text(
            f"✏️ Хорошо, попробуйте еще раз.\n\n"
            f"Отправьте исправленное название марки стали.",
            parse_mode='Markdown'
        )
        # Note: We don't reset the attempt counter - next search will be 3rd attempt (automatic AI)
        return

    elif action == 'add':
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
