"""Compare grades handler"""
import requests
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
    """Perform comparison of steel grades"""
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
            f"▪️ Проверка в базе данных\n",
            parse_mode='Markdown'
        )

        reference_grade = grades[0]
        compare_grades = grades[1:]

        # Step 1: Find reference grade in DB
        ref_response = requests.get(
            config.SEARCH_ENDPOINT,
            params={'grade': reference_grade, 'exact': 'true'},
            timeout=30
        )

        ref_found = False
        ref_data = None

        if ref_response.status_code == 200:
            ref_results = ref_response.json()
            if ref_results:
                ref_found = True
                ref_data = ref_results[0]

        # Step 2: If reference grade not found in DB, try AI Search
        if not ref_found:
            await status_msg.edit_text(
                f"⚖️ Сравниваю марки: `{', '.join(grades)}`...\n\n"
                f"▪️ Проверка в базе данных\n"
                f"▪️ Марка `{reference_grade}` не найдена в БД\n"
                f"▪️ Поиск через AI Search...\n",
                parse_mode='Markdown'
            )

            # Try AI Search for reference grade
            ai_response = requests.get(
                config.SEARCH_ENDPOINT,
                params={'grade': reference_grade, 'ai': 'true'},
                timeout=60
            )

            if ai_response.status_code == 200:
                ai_results = ai_response.json()
                if ai_results:
                    ref_found = True
                    ref_data = ai_results[0]

        if not ref_found:
            await status_msg.edit_text(
                f"❌ Марка `{reference_grade}` не найдена ни в базе данных, ни через AI Search.",
                parse_mode='Markdown'
            )
            return

        # Step 3: Find comparison grades in DB (exact match only)
        await status_msg.edit_text(
            f"⚖️ Сравниваю марки: `{', '.join(grades)}`...\n\n"
            f"▪️ Эталонная марка найдена\n"
            f"▪️ Поиск марок для сравнения...\n",
            parse_mode='Markdown'
        )

        found_compare_grades = []
        not_found_grades = []

        for grade in compare_grades:
            response = requests.get(
                config.SEARCH_ENDPOINT,
                params={'grade': grade, 'exact': 'true'},
                timeout=30
            )

            if response.status_code == 200:
                results = response.json()
                if results:
                    found_compare_grades.append(results[0])
                else:
                    not_found_grades.append(grade)
            else:
                not_found_grades.append(grade)

        if not found_compare_grades:
            await status_msg.edit_text(
                f"❌ Ни одна марка для сравнения не найдена в базе данных:\n"
                f"{', '.join(not_found_grades)}",
                parse_mode='Markdown'
            )
            return

        # Delete status message
        await status_msg.delete()

        # Step 4: Format comparison table
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
    """Format comparison as Markdown table with elements as rows, grades as columns"""

    lines = ["⚖️ **Сравнение марок стали**\n"]

    # Collect all grades
    all_grades = [ref_data] + compare_grades
    grade_names = [g['grade'] for g in all_grades]

    # Elements to compare (14 elements from fuzzy_search.py)
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
        ('N', 'n'),
        ('S', 's'),
        ('P', 'p')
    ]

    # Build table header
    # Format: | Element | Grade1 | Grade2 | Grade3 |
    header = "| Эл-т | " + " | ".join(grade_names) + " |"
    separator = "|" + "|".join(["---"] * (len(all_grades) + 1)) + "|"

    lines.append(header)
    lines.append(separator)

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

        row = f"| **{element_name}** |"

        for grade in all_grades:
            value = grade.get(element_key)
            if value and value not in [None, '', '0', '0.00', 'N/A']:
                row += f" {value} |"
            else:
                row += " - |"

        lines.append(row)

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
            # Truncate if too long
            if len(analogues) > 100:
                analogues = analogues[:97] + "..."
            lines.append(f"• **{grade['grade']}**: {analogues}")
        else:
            lines.append(f"• **{grade['grade']}**: _Нет в БД_")

    # Add warning for not found grades
    if not_found:
        lines.append(f"\n⚠️ **Не найдены в БД:** {', '.join(not_found)}")

    return '\n'.join(lines)
