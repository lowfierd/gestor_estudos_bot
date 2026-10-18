import asyncio
import io
from typing import Any
import matplotlib
# Configura backend headless antes de importar pyplot para evitar problemas de GUI no servidor/Windows
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _generate_chart_sync(weekly_data: dict[str, Any]) -> io.BytesIO:
    """
    Função síncrona que desenha os gráficos de barras e pizza em alta resolução
    com estética moderna (Dark/Slate Theme) e retorna o buffer de memória.
    """
    users_data = weekly_data.get("users", [])
    subjects_data = weekly_data.get("subjects", [])
    start_date, end_date = weekly_data.get("period", (None, None))

    # Paleta de cores moderna (estilo Cyberpunk/Catppuccin)
    bg_color = "#181825"
    card_color = "#1e1e2e"
    text_color = "#cdd6f4"
    accent_bar_colors = ["#89b4fa", "#f38ba8", "#a6e3a1", "#fab387"]
    pie_colors = ["#89b4fa", "#cba6f7", "#f38ba8", "#fab387", "#a6e3a1", "#94e2d5"]

    plt.style.use("dark_background")
    fig, (ax_bar, ax_pie) = plt.subplots(1, 2, figsize=(11, 5.2), dpi=200)
    fig.patch.set_facecolor(bg_color)
    ax_bar.set_facecolor(card_color)
    ax_pie.set_facecolor(card_color)

    # Título do Período
    period_str = ""
    if start_date and end_date:
        period_str = f" ({start_date.strftime('%d/%m')} a {end_date.strftime('%d/%m')})"
    fig.suptitle(f"⚔️ Batalha dos Estudos — Resumo Semanal{period_str}", fontsize=14, color="#f5e0dc", fontweight="bold", y=0.98)

    # 1. Gráfico de Barras: Comparativo entre os Usuários
    if users_data:
        names = [u["name"] for u in users_data]
        hours = [round(u["minutes"] / 60, 1) for u in users_data]
        bars = ax_bar.bar(names, hours, color=accent_bar_colors[:len(names)], width=0.45, edgecolor="#313244", linewidth=1.2)

        ax_bar.set_title("Horas Dedicadas por Estudante", color=text_color, fontsize=12, pad=10)
        ax_bar.set_ylabel("Horas de Estudo", color=text_color, fontsize=10)
        ax_bar.tick_params(colors=text_color)
        ax_bar.grid(axis="y", linestyle="--", alpha=0.25, color="#585b70")

        # Rótulos no topo das barras
        for bar in bars:
            height = bar.get_height()
            ax_bar.annotate(
                f"{height}h",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center", va="bottom",
                fontsize=10, fontweight="bold", color="#ffffff"
            )
    else:
        ax_bar.text(0.5, 0.5, "Sem estudos registrados\nna semana", ha="center", va="center", color="#a6adc8", fontsize=11)
        ax_bar.set_title("Horas Dedicadas", color=text_color, fontsize=12)
        ax_bar.axis("off")

    # 2. Gráfico de Pizza: Divisão por Disciplinas
    if subjects_data:
        sub_labels = [s["subject"] for s in subjects_data]
        sub_minutes = [s["minutes"] for s in subjects_data]

        wedges, texts, autotexts = ax_pie.pie(
            sub_minutes,
            labels=sub_labels,
            autopct="%1.0f%%",
            startangle=140,
            colors=pie_colors[:len(sub_labels)],
            wedgeprops={"edgecolor": card_color, "linewidth": 2, "antialiased": True},
            textprops={"color": text_color, "fontsize": 9}
        )
        for autotext in autotexts:
            autotext.set_color("#11111b")
            autotext.set_weight("bold")
            autotext.set_fontsize(8.5)

        ax_pie.set_title("Foco por Matéria do Casal", color=text_color, fontsize=12, pad=10)
    else:
        ax_pie.text(0.5, 0.5, "Aguardando registros\ncom /estudar", ha="center", va="center", color="#a6adc8", fontsize=11)
        ax_pie.set_title("Foco por Matéria", color=text_color, fontsize=12)
        ax_pie.axis("off")

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    buf.seek(0)
    plt.close(fig)
    return buf


async def generate_weekly_report_chart(weekly_data: dict[str, Any]) -> io.BytesIO:
    """
    Executa a geração do gráfico em uma thread separada para não travar
    o loop de eventos assíncrono do bot Telegram.
    """
    return await asyncio.to_thread(_generate_chart_sync, weekly_data)
