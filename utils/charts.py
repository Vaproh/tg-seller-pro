import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import config


def _style_ax(ax, title):
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=10)


def revenue_chart(rows):
    if not rows:
        return None
    days = [datetime.strptime(r["day"], "%Y-%m-%d") for r in rows]
    revenue = [r["revenue"] for r in rows]
    counts = [r["count"] for r in rows]

    fig, ax1 = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor("#1a1a2e")
    ax1.set_facecolor("#16213e")

    color_bar = "#00d2ff"
    color_line = "#ff6b6b"

    ax1.bar(days, revenue, color=color_bar, alpha=0.7, width=0.8, label="Revenue")
    ax1.set_ylabel(f"Revenue ({config.CURRENCY})", color=color_bar, fontsize=11)
    ax1.tick_params(axis="y", labelcolor=color_bar)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())

    ax2 = ax1.twinx()
    ax2.plot(days, counts, color=color_line, marker="o", markersize=5, linewidth=2, label="Sales")
    ax2.set_ylabel("Sales Count", color=color_line, fontsize=11)
    ax2.tick_params(axis="y", labelcolor=color_line)

    _style_ax(ax1, "📈 Revenue Over Time")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=90, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf


def category_pie(rows):
    if not rows:
        return None
    labels = [str(r["category"]) for r in rows]
    sizes = [r["revenue"] for r in rows]
    colors = ["#ff6b6b", "#00d2ff", "#ffd93d", "#6bcb77", "#4d96ff", "#ff922b", "#cc5de8", "#20c997"]

    fig, ax = plt.subplots(figsize=(5, 5))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.0f%%",
        colors=colors[:len(labels)],
        textprops={"color": "white", "fontsize": 11},
        pctdistance=0.8,
        startangle=90,
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax.set_title("📂 Revenue by Category", fontsize=13, fontweight="bold", color="white", pad=15)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=90, bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return buf


def payment_donut(rows):
    if not rows:
        return None
    labels = []
    sizes = []
    colors_map = {"paid": "#6bcb77", "pending": "#ffd93d"}
    for r in rows:
        status = r["payment_status"]
        labels.append(f"{status} ({r['count']})")
        sizes.append(r["amount"])
    colors = [colors_map.get(l.split(" ")[0], "#888") for l in labels]

    fig, ax = plt.subplots(figsize=(4, 4))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    wedges, texts = ax.pie(
        sizes, labels=labels, colors=colors,
        textprops={"color": "white", "fontsize": 11},
        startangle=90, wedgeprops={"width": 0.4},
    )
    total = sum(sizes)
    ax.text(0, 0, f"{config.CURRENCY}{total:.0f}", ha="center", va="center", fontsize=16, fontweight="bold", color="white")
    ax.set_title("💳 Payment Status", fontsize=13, fontweight="bold", color="white", pad=15)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=90, bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return buf


def top_sellers_bar(rows):
    if not rows:
        return None
    names = [str(r["seller_name"])[:15] for r in reversed(rows)]
    revenue = [r["total_revenue"] for r in reversed(rows)]
    counts = [r["total_sales"] for r in reversed(rows)]

    fig, ax = plt.subplots(figsize=(7, max(3, len(names) * 0.5)))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    bars = ax.barh(names, revenue, color="#4d96ff", alpha=0.85, height=0.6)
    ax.set_xlabel(f"Total Revenue ({config.CURRENCY})", color="white", fontsize=11)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + max(revenue) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{config.CURRENCY}{bar.get_width():.0f} ({count})", va="center", color="white", fontsize=9)

    _style_ax(ax, "👨‍💼 Top Sellers")
    ax.tick_params(axis="y", colors="white")
    ax.tick_params(axis="x", colors="white")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=90, bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return buf
