from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from pathlib import Path

from models.schemas import SlideSpec
from services.gcs_service import GcsService, GcsServiceConfig


@dataclass(frozen=True)
class ChartServiceConfig:
    dpi: int = 150


class ChartService:
    def __init__(self, config: ChartServiceConfig | None = None) -> None:
        self._config = config or ChartServiceConfig()

    def generate_charts(self, slides: list[SlideSpec], out_dir: Path) -> dict[int, Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        result: dict[int, Path] = {}
        for idx, slide in enumerate(slides):
            if not slide.chart:
                continue
            chart_type = str(slide.chart.get("type", "")).lower()
            if chart_type == "bar":
                result[idx] = self._bar_chart(slide, out_dir / f"chart_{idx+1}.png")
        return result

    def _bar_chart(self, slide: SlideSpec, out_path: Path) -> Path:
        labels = list(slide.chart.get("labels") or [])
        values = list(slide.chart.get("values") or [])
        title = str(slide.chart.get("title") or slide.title)

        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(8, 4.5))
        ax = fig.add_subplot(111)
        ax.bar(labels, values)
        ax.set_title(title)
        ax.set_ylabel("Value")
        fig.tight_layout()
        fig.savefig(out_path, dpi=self._config.dpi)
        plt.close(fig)
        return out_path


def _safe_session_id(session_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", (session_id or "").strip())
    return cleaned or "session"


def _coerce_series(labels: object, values: object) -> tuple[list[str], list[float]]:
    raw_labels = labels if isinstance(labels, (list, tuple)) else []
    raw_values = values if isinstance(values, (list, tuple)) else []

    lbls = [str(x) for x in raw_labels]
    vals: list[float] = []
    for v in raw_values:
        try:
            vals.append(float(v))
        except Exception:
            vals.append(0.0)

    n = min(len(lbls), len(vals))
    return lbls[:n], vals[:n]


def _render_premium_chart(chart_type: str, title: str, labels: list[str], values: list[float], out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import colors as mcolors

    bg = "#1a1a2e"
    fg = "#ffffff"
    accent = "#6c63ff"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with matplotlib.rc_context(
        {
            "figure.facecolor": bg,
            "axes.facecolor": bg,
            "savefig.facecolor": bg,
            "text.color": fg,
            "axes.labelcolor": fg,
            "xtick.color": fg,
            "ytick.color": fg,
            "axes.edgecolor": (1, 1, 1, 0.18),
            "grid.color": (1, 1, 1, 0.12),
            "grid.linestyle": "-",
            "grid.linewidth": 0.8,
            "font.family": "DejaVu Sans",
        }
    ):
        fig = plt.figure(figsize=(10, 6), dpi=150)
        ax = fig.add_subplot(111)
        ax.grid(True, axis="both")
        ax.set_axisbelow(True)

        for spine in ax.spines.values():
            spine.set_alpha(0.18)

        ctype = (chart_type or "").strip().lower()
        if ctype == "bar":
            if not labels or not values:
                ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=14, fontweight="bold")
                ax.set_xticks([])
                ax.set_yticks([])
            else:
                vmax = max(values) if values else 0.0
                vmin = min(values) if values else 0.0
                if vmax == vmin:
                    norm_vals = [i / max(1, len(values) - 1) for i in range(len(values))]
                else:
                    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
                    norm_vals = [float(norm(v)) for v in values]

                cmap = plt.get_cmap("viridis")
                bar_colors = [cmap(0.25 + 0.65 * nv) for nv in norm_vals]

                bars = ax.barh(labels, values, color=bar_colors, edgecolor=(1, 1, 1, 0.16), linewidth=1.0)
                ax.invert_yaxis()

                pad = (max(abs(v) for v in values) or 1.0) * 0.02
                for b, v in zip(bars, values, strict=False):
                    x = b.get_width()
                    x_text = x + pad if v >= 0 else x - pad
                    ha = "left" if v >= 0 else "right"
                    ax.text(
                        x_text,
                        b.get_y() + b.get_height() / 2,
                        f"{v:g}",
                        va="center",
                        ha=ha,
                        fontsize=10,
                        color=(1, 1, 1, 0.92),
                    )
                ax.margins(x=0.12)

        elif ctype == "pie":
            ax.grid(False)
            ax.set_xticks([])
            ax.set_yticks([])
            if not labels or not values or sum(abs(v) for v in values) == 0:
                ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=14, fontweight="bold")
            else:
                max_idx = max(range(len(values)), key=lambda i: values[i])
                explode = [0.08 if i == max_idx else 0.0 for i in range(len(values))]
                cmap = plt.get_cmap("plasma")
                slice_colors = [cmap(0.18 + 0.72 * (i / max(1, len(values) - 1))) for i in range(len(values))]

                def _pct(p: float) -> str:
                    return f"{p:.0f}%" if p >= 4 else ""

                wedges, _texts, _autotexts = ax.pie(
                    values,
                    explode=explode,
                    colors=slice_colors,
                    autopct=_pct,
                    startangle=90,
                    counterclock=False,
                    pctdistance=0.75,
                    wedgeprops={"linewidth": 1.2, "edgecolor": bg},
                    textprops={"color": fg, "fontsize": 10, "fontweight": "bold"},
                )
                ax.legend(
                    wedges,
                    labels,
                    loc="center left",
                    bbox_to_anchor=(1.02, 0.5),
                    frameon=False,
                    labelcolor=fg,
                    fontsize=10,
                )
                ax.set_aspect("equal")

        elif ctype == "line":
            if not labels or not values:
                ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=14, fontweight="bold")
                ax.set_xticks([])
                ax.set_yticks([])
            else:
                x = list(range(len(values)))
                ax.plot(
                    x,
                    values,
                    color=accent,
                    linewidth=2.6,
                    marker="o",
                    markersize=6,
                    markerfacecolor=bg,
                    markeredgewidth=2,
                    markeredgecolor=accent,
                )
                ax.fill_between(x, values, [0.0 for _ in values], color=accent, alpha=0.18)
                ax.set_xticks(x)
                ax.set_xticklabels(labels, rotation=0, ha="center")
                ax.margins(x=0.02)
        else:
            ax.text(0.5, 0.5, f"Unsupported chart type: {ctype or 'unknown'}", ha="center", va="center", fontsize=12)
            ax.set_xticks([])
            ax.set_yticks([])

        ax.set_title(str(title or "").strip() or "Chart", fontsize=16, fontweight="bold", color=fg, pad=14)
        fig.tight_layout()
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)


async def generate_charts(chart_specs: list[dict], session_id: str) -> list[str]:
    gcs_bucket = os.getenv("GCS_BUCKET_NAME")
    gcs_prefix = os.getenv("GCS_PREFIX", "pitch-decks")
    gcs_service = GcsService(GcsServiceConfig(bucket_name=gcs_bucket, prefix=gcs_prefix))

    tmp_dir = Path("/tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    sid = _safe_session_id(session_id)
    urls: list[str] = []

    for i, spec in enumerate(chart_specs or []):
        if not isinstance(spec, dict):
            spec = {}

        chart_type = str(spec.get("chart_type") or spec.get("type") or "").strip().lower()
        title = str(spec.get("title") or "").strip()
        labels, values = _coerce_series(spec.get("labels"), spec.get("values"))

        local_path = tmp_dir / f"{sid}_chart_{i}.png"
        await asyncio.to_thread(_render_premium_chart, chart_type, title, labels, values, local_path)

        upload = await asyncio.to_thread(gcs_service.upload_file, local_path)
        url = upload.get("url") if isinstance(upload, dict) else None
        urls.append(url or str(local_path))

    return urls
