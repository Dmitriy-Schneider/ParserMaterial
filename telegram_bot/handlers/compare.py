"""Compare grades handler"""
import requests
import html
from telegram import Update
from telegram.ext import ContextTypes

import config


async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle compare command - compare multiple steel grades side-by-side"""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚖️ **Сравнение марок**\n\n"
            "Укажите минимум 2 марки для сравнения.\n\n"
            "Примеры:\n"
            "• `/compare Х12МФ D2`\n"
            "• `/compare 420 AISI 420 1.4034`",
            parse_mode='Markdown'
        )
        return

    grades = context.args
    await perform_compare(update, grades)


async def perform_compare(update: Update, grades: list):
    """Perform comparison of steel grades (with AI support)"""
    try:
        if len(grades) < 2:
            await update.message.reply_text(
                "❌ Укажите минимум 2 марки для сравнения.",
                parse_mode='Markdown'
            )
            return

        # Send "processing" message
        status_msg = await update.message.reply_text(
            f"⚖️ Сравниваю марки: `{', '.join(grades)}`...\n\n"
            f"▪️ Поиск марок (БД + AI)...\n",
            parse_mode='Markdown'
        )

        reference_grade = grades[0]
        compare_grades = grades[1:]

        # Step 1: Find ALL grades (reference + compare) in DB or AI
        # ИСПРАВЛЕНО: Теперь ищем все марки через AI если не найдены в БД
        all_grades_data = {}
        ai_data_to_send = {}

        for i, grade in enumerate(grades, 1):
            # Try DB first
            response = requests.get(
                config.SEARCH_ENDPOINT,
                params={'grade': grade, 'exact': 'true'},
                timeout=30
            )

            found = False
            if response.status_code == 200:
                results = response.json()
                if results:
                    found = True
                    all_grades_data[grade] = results[0]
                    print(f"[Compare] Found {grade} in DB")

            # If not in DB, try AI
            if not found:
                await status_msg.edit_text(
                    f"⚖️ Сравниваю марки ({i}/{len(grades)})...\n\n"
                    f"▪️ Марка `{grade}` не в БД\n"
                    f"▪️ Поиск через AI Search...\n"
                    f"⏳ Пожалуйста, подождите...",
                    parse_mode='Markdown'
                )

                ai_response = requests.get(
                    config.SEARCH_ENDPOINT,
                    params={'grade': grade, 'ai': 'true'},
                    timeout=60
                )

                if ai_response.status_code == 200:
                    ai_results = ai_response.json()
                    if ai_results:
                        found = True
                        all_grades_data[grade] = ai_results[0]
                        ai_data_to_send[grade] = ai_results[0]
                        print(f"[Compare] Found {grade} via AI")

            if not found:
                await status_msg.edit_text(
                    f"❌ Марка `{grade}` не найдена ни в БД, ни через AI Search.",
                    parse_mode='Markdown'
                )
                return

        # Step 2: Use /api/steels/compare endpoint with AI data
        # ИСПРАВЛЕНО: Используем улучшенный endpoint с поддержкой AI данных
        await status_msg.edit_text(
            f"⚖️ Сравниваю марки: `{', '.join(grades)}`...\n\n"
            f"▪️ Все марки найдены\n"
            f"▪️ Формирую таблицу сравнения...\n",
            parse_mode='Markdown'
        )

        compare_request = {
            'reference_grade': reference_grade,
            'compare_grades': compare_grades
        }

        # Add AI data if reference is from AI
        if reference_grade in ai_data_to_send:
            compare_request['reference_data'] = ai_data_to_send[reference_grade]
            print(f"[Compare] Sending AI data for reference: {reference_grade}")

        # Add AI data for compare grades
        compare_ai_data = []
        for grade in compare_grades:
            if grade in ai_data_to_send:
                compare_ai_data.append(ai_data_to_send[grade])
                print(f"[Compare] Sending AI data for compare: {grade}")

        if compare_ai_data:
            compare_request['compare_data'] = compare_ai_data

        # Call compare endpoint
        compare_response = requests.post(
            f"{config.SEARCH_ENDPOINT.replace('/steels', '/steels/compare')}",
            json=compare_request,
            timeout=30
        )

        if compare_response.status_code != 200:
            error_data = compare_response.json() if compare_response.text else {}
            error_msg = error_data.get('error', f'HTTP {compare_response.status_code}')
            await status_msg.edit_text(
                f"❌ Ошибка сравнения: {error_msg}",
                parse_mode='Markdown'
            )
            return

        compare_data = compare_response.json()

        # Delete status message
        await status_msg.delete()

        # Step 3: Format comparison table
        ref_data = compare_data['reference_data']
        found_compare_grades = compare_data['results']
        not_found_grades = []  # Все марки найдены (иначе вернулись бы раньше)

        message = format_comparison_table(ref_data, found_compare_grades, not_found_grades)

        # Send in chunks if too long (Telegram limit is 4096 characters)
        if len(message) > 4000:
            # Split by double newline
            chunks = message.split('\n\n')
            current_chunk = ""

            for chunk in chunks:
                if len(current_chunk) + len(chunk) + 2 < 4000:
                    current_chunk += chunk + "\n\n"
                else:
                    if current_chunk:
                        await update.message.reply_text(current_chunk, parse_mode='Markdown')
                    current_chunk = chunk + "\n\n"

            if current_chunk:
                await update.message.reply_text(current_chunk, parse_mode='Markdown')
        else:
            await update.message.reply_text(message, parse_mode='Markdown')

    except requests.exceptions.Timeout:
        await update.message.reply_text(
            "⏱️ Превышено время ожидания. Попробуйте позже."
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка при сравнении: {str(e)}"
        )


def format_comparison_table(ref_data: dict, compare_grades: list, not_found: list) -> str:
    """Format comparison as code block table with elements as rows, grades as columns"""

    lines = ["⚖️ **Сравнение марок стали**\n"]

    # Collect all grades
    all_grades = [ref_data] + compare_grades
    grade_names = [g['grade'] for g in all_grades]

    # Elements to compare (12 elements, S and P excluded as often not reported)
    elements = [
        ('C', 'c'),
        ('Cr', 'cr'),
        ('Ni', 'ni'),
        ('Mo', 'mo'),
        ('V', 'v'),
        ('W', 'w'),
        ('Co', 'co'),
        ('Mn', 'mn'),
        ('Si', 'si'),
        ('Cu', 'cu'),
        ('Nb', 'nb'),
        ('N', 'n')
    ]

    # Start code block for table
    table_lines = []

    # Build header row
    # Max width for grade names (truncate if needed)
    max_grade_width = 12
    truncated_names = [name[:max_grade_width].ljust(max_grade_width) for name in grade_names]

    header = "Эл-т  " + "  ".join(truncated_names)
    table_lines.append(header)
    table_lines.append("-" * len(header))

    # Build table rows (one row per element)
    for element_name, element_key in elements:
        # Check if any grade has this element
        has_element = any(
            grade.get(element_key) and
            grade.get(element_key) not in [None, '', '0', '0.00', 'N/A']
            for grade in all_grades
        )

        if not has_element:
            continue  # Skip elements that are absent in all grades

        # Format element name (2 chars, left-justified)
        row_parts = [element_name.ljust(4)]

        for grade in all_grades:
            value = grade.get(element_key)
            if value and value not in [None, '', '0', '0.00', 'N/A']:
                # Decode HTML entities (e.g., &nbsp; → space) and truncate
                clean_value = html.unescape(str(value))
                value_str = clean_value[:max_grade_width].ljust(max_grade_width)
                row_parts.append(value_str)
            else:
                row_parts.append("-".ljust(max_grade_width))

        table_lines.append("  ".join(row_parts))

    # Wrap table in code block
    lines.append("```")
    lines.extend(table_lines)
    lines.append("```")

    # Add standards/manufacturers info
    lines.append("\n**📋 Стандарты:**")
    for grade in all_grades:
        standard = grade.get('standard', 'N/A')
        lines.append(f"• **{grade['grade']}**: {standard}")

    # Add analogues
    lines.append("\n**🔗 Аналоги:**")
    for grade in all_grades:
        analogues = grade.get('analogues', '')
        if analogues and analogues not in [None, '', 'N/A']:
            # Split by pipe separator and format
            analogue_list = [a.strip() for a in analogues.split('|') if a.strip()]
            if analogue_list:
                analogue_str = ', '.join(analogue_list)
                # Truncate if too long
                if len(analogue_str) > 100:
                    analogue_str = analogue_str[:97] + "..."
                lines.append(f"• **{grade['grade']}**: {analogue_str}")
            else:
                lines.append(f"• **{grade['grade']}**: _Нет в БД_")
        else:
            lines.append(f"• **{grade['grade']}**: _Нет в БД_")

    # Add other elements info
    lines.append("\n**ℹ️ Другие элементы:**")
    for grade in all_grades:
        other = grade.get('other', '')
        if other and other not in [None, '', 'N/A', '-']:
            # Truncate if too long
            if len(other) > 100:
                other = other[:97] + "..."
            lines.append(f"• **{grade['grade']}**: {other}")
        else:
            lines.append(f"• **{grade['grade']}**: _Нет в БД_")

    # Add warning for not found grades
    if not_found:
        lines.append(f"\n⚠️ **Не найдены в БД:** {', '.join(not_found)}")

    return '\n'.join(lines)
