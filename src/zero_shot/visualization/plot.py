import pandas as pd
import matplotlib.pyplot as plt
import io
from PIL import Image
from zero_shot.config.config import (
    MAX_BAR_ITEMS, MAX_LINE_POINTS, MAX_SCATTER_POINTS,
    PLOT_BLACKLIST, MIN_PLOT_ROWS, MIN_PLOT_COLS,
    MIN_DISTINCT_Y, MAX_PIE_UNIQUE,
    LABEL_LENGTH_THRESHOLD, PLOT_FIGSIZE, PLOT_DPI
)

def generate_plot(df: pd.DataFrame) -> Image.Image | None:
    if df.shape[1] < MIN_PLOT_COLS or df.shape[0] < MIN_PLOT_ROWS:
        return None

    x_col = df.columns[0]

    y_col = next((col for col in df.columns[1:] if pd.api.types.is_numeric_dtype(df[col])), None)
    if y_col is None:
        for col in df.columns[1:]:
            try:
                df[col] = pd.to_numeric(df[col])
                y_col = col
                break
            except Exception:
                continue
        if y_col is None:
            return None

    if x_col.upper() in PLOT_BLACKLIST or y_col.upper() in PLOT_BLACKLIST:
        return None

    df_plot = df[[x_col, y_col]].copy()
    df_plot = df_plot[(df_plot[y_col].notna()) & (df_plot[y_col] > 0)]
    if df_plot.shape[0] < MIN_PLOT_ROWS or df_plot[y_col].nunique() < MIN_DISTINCT_Y:
        return None

    try:
        df_plot[x_col] = pd.to_datetime(df_plot[x_col])
        is_x_date = True
    except Exception:
        is_x_date = pd.api.types.is_datetime64_any_dtype(df_plot[x_col])

    if is_x_date:
        df_plot = df_plot.sort_values(by=x_col)
    else:
        df_plot = df_plot.sort_values(by=y_col, ascending=False)

    if is_x_date:
        kind = "line"
    elif pd.api.types.is_numeric_dtype(df_plot[x_col]) and pd.api.types.is_numeric_dtype(df_plot[y_col]):
        kind = "scatter"
    elif df_plot[x_col].nunique() <= MAX_PIE_UNIQUE:
        kind = "pie"
    else:
        kind = "barh" if df_plot[x_col].astype(str).str.len().max() > LABEL_LENGTH_THRESHOLD else "bar"

    max_points = {
        "line": MAX_LINE_POINTS,
        "scatter": MAX_SCATTER_POINTS,
        "bar": MAX_BAR_ITEMS,
        "barh": MAX_BAR_ITEMS,
        "pie": MAX_PIE_UNIQUE
    }.get(kind, MAX_BAR_ITEMS)

    df_plot = df_plot.head(max_points)
    print(f"📉 Number of points for {kind} plot (max {max_points}): {df_plot.shape[0]}")

    fig, ax = plt.subplots(figsize=PLOT_FIGSIZE, dpi=PLOT_DPI)

    if kind == "pie":
        pie_data = df_plot.dropna()
        ax.pie(pie_data[y_col], labels=pie_data[x_col], autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
    elif kind == "scatter":
        ax.scatter(df_plot[x_col], df_plot[y_col])
    else:
        df_plot.plot(kind=kind, x=x_col, y=y_col, ax=ax)

    ax.set_title(f"{kind.capitalize()} plot: {y_col} vs {x_col}", fontsize=14)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    return Image.open(buf)
