"""Stats command handler"""
import requests
from telegram import Update
from telegram.ext import ContextTypes

import config


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    try:
        # Send "loading" message
        status_msg = await update.message.reply_text("📊 Загружаю статистику...")

        # Make API request
        response = requests.get(config.STATS_ENDPOINT, timeout=10)

        if response.status_code != 200:
            await status_msg.edit_text(
                f"❌ Ошибка получения статистики: {response.status_code}"
            )
            return

        stats = response.json()

        # Delete "loading" message
        await status_msg.delete()

        # Format stats message
        message = format_stats(stats)
        await update.message.reply_text(message, parse_mode='Markdown')

    except requests.exceptions.Timeout:
        await update.message.reply_text(
            "⏱️ Превышено время ожидания. Попробуйте позже."
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}"
        )


def format_stats(stats: dict) -> str:
    """Format statistics information"""
    total = stats.get('total', 0)
    ai_enabled = stats.get('ai_enabled', False)
    ai_cached = stats.get('ai_cached_searches', 0)
    bases = stats.get('bases', [])

    lines = [
        "📊 **Статистика ParserSteel**",
        "",
        f"🗄️ **Всего марок в БД:** {total:,}".replace(',', ' '),
        ""
    ]

    # AI status
    if ai_enabled:
        lines.append("🤖 **AI поиск:** ✅ Включен")
        lines.append(f"💾 **AI кэш:** {ai_cached} запросов")
    else:
        lines.append("🤖 **AI поиск:** ❌ Выключен")

    # Bases
    if bases:
        lines.append("\n**Базовые элементы в БД:**")
        for base in bases:
            base_name = {
                'Fe': 'Железо (Fe)',
                'Ni': 'Никель (Ni)',
                'Co': 'Кобальт (Co)',
                'Ti': 'Титан (Ti)',
                'Al': 'Алюминий (Al)',
                'Cu': 'Медь (Cu)'
            }.get(base, base)
            lines.append(f"  • {base_name}")

    lines.extend([
        "",
        "🌐 **Покрытие:**",
        "  • GOST (Россия)",
        "  • AISI/SAE (США)",
        "  • DIN/EN (Европа)",
        "  • JIS (Япония)",
        "  • GB (Китай)",
        "  • Фирменные марки",
        "",
        "💡 Используйте `/search` для поиска марок!"
    ])

    return '\n'.join(lines)
