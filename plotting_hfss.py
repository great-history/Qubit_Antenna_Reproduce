"""Plot HFSS impedance and S11 curves from arrays or exported CSV files.

Notebook example:
    from plotting_hfss import load_hfss_csv, plot_hfss_curves
    f, z, s11_db = load_hfss_csv(s_path, z_path)
    plot_hfss_curves(f, [z.real, z.imag], labels=["Re(Z)", "Im(Z)"],
                     ylabel="Impedance [ohms]")

Run this file directly to plot the loop_slot CSV files beside it.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


# Importing this module does not change Matplotlib settings.
PLOT_CONFIG = {
    "figure.dpi": 120,
    "savefig.dpi": 300,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "font.family": "sans-serif",
    "mathtext.fontset": "dejavusans",
}

Z_COLORS = ("red", "#00cc00")
S11_COLORS = ("red", "black")


def _prepare_data(frequency, *curves):
    """Validate one-dimensional arrays and sort them together by frequency."""
    frequency = np.asarray(frequency, dtype=float)
    curves = [np.asarray(curve) for curve in curves]
    if frequency.ndim != 1 or frequency.size == 0:
        raise ValueError("frequency must be a nonempty one-dimensional array.")
    if any(curve.shape != frequency.shape for curve in curves):
        raise ValueError("Each curve must have the same shape as frequency.")
    if not all(np.isfinite(a).all() for a in [frequency, *curves]):
        raise ValueError("Input arrays must contain only finite values.")
    order = np.argsort(frequency, kind="stable")
    if np.any(np.diff(frequency[order]) == 0):
        raise ValueError("Frequency values must be unique.")
    return frequency[order], *(curve[order] for curve in curves)


def _finish_plot(fig, axes, frequency, xlim, save_path, flag_show):
    """Apply common axes styling and optionally save or show the figure."""
    for ax in axes:
        ax.set_xlim(xlim if xlim is not None else (frequency[0], frequency[-1]))
        ax.set_axisbelow(True)
        ax.minorticks_on()
        ax.grid(which="major", alpha=0.5)
        ax.grid(which="minor", alpha=0.2)
    if save_path is not None:
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
    if flag_show:
        plt.show()


def load_hfss_csv(s_path, z_path):
    """Return frequency (GHz), complex Z (ohms), and S11 (dB).

    Expected columns: frequency/S11 dB and frequency/Re(Z)/Im(Z),
    respectively, with one header row. Matching grids are required;
    no interpolation or smoothing is applied.
    """
    s = np.loadtxt(s_path, delimiter=",", skiprows=1, ndmin=2)
    z = np.loadtxt(z_path, delimiter=",", skiprows=1, ndmin=2)
    if s.shape[1] != 2 or z.shape[1] != 3:
        raise ValueError("Expected two S CSV columns and three Z CSV columns.")
    f_s, s11_db = _prepare_data(s[:, 0], s[:, 1])
    f_z, z_in = _prepare_data(z[:, 0], z[:, 1] + 1j * z[:, 2])
    if not np.array_equal(f_s, f_z):
        raise ValueError("S and Z CSV frequency grids must match.")
    return f_s, z_in, s11_db


def plot_hfss_curves(
    frequency, curves, ax=None, labels=None, title=None,
    xlabel="Frequency [GHz]", ylabel="", xlim=None, ylim=None,
    figsize=(9, 4.5), colors=None, linestyles=None, linewidth=1.5,
    legend=True, save_path=None, flag_show=True,
):
    """Plot one or more real curves; return (fig, ax).

    curves has shape (n_points,) or (n_curves, n_points): each ROW is
    one curve. For complex data, explicitly pass real, imag, abs or angle.
    labels, colors and linestyles each accept one entry per curve.
    Frequency and curves are sorted together; no conversion is performed.
    Pass ax to draw on an existing subplot. flag_show=False skips show()
    and leaves the figure open for further editing or additional subplots.
    save_path supports PNG/PDF/SVG, using savefig.dpi in PLOT_CONFIG.
    """
    curves = np.asarray(curves)
    if np.iscomplexobj(curves):
        raise ValueError("Select real, imag, abs or angle before plotting complex data.")
    if curves.ndim == 1:
        curves = curves[None, :]
    if curves.ndim != 2 or curves.shape[0] == 0:
        raise ValueError("curves must have shape (n_points,) or (n_curves, n_points).")
    frequency, *curves = _prepare_data(frequency, *curves)
    count = len(curves)

    def per_curve(values, default, name):
        if values is None:
            return [default] * count
        if isinstance(values, str):
            values = [values]
        if len(values) != count:
            raise ValueError(f"{name} must have one entry per curve.")
        return values

    labels = per_curve(labels, None, "labels")
    colors = per_curve(colors, None, "colors")
    linestyles = per_curve(linestyles, "-", "linestyles")
    with plt.rc_context(PLOT_CONFIG):
        if ax is None:
            _, ax = plt.subplots(figsize=figsize, constrained_layout=True)
        fig = ax.figure
        for curve, label, color, style in zip(curves, labels, colors, linestyles):
            ax.plot(frequency, curve, label=label, color=color,
                    linestyle=style, linewidth=linewidth)
        ax.set(xlabel=xlabel, ylabel=ylabel)
        if title is not None:
            ax.set_title(title)
        if ylim is not None:
            ax.set_ylim(ylim)
        if legend and any(label is not None for label in labels):
            ax.legend()
        _finish_plot(fig, [ax], frequency, xlim, save_path, flag_show)
    return fig, ax


if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent
    frequency, z_in, s11_db = load_hfss_csv(
        data_dir / "loop_slot_S_Parameter_Plot_1.csv",
        data_dir / "loop_slot_Z_Parameter_Plot_1.csv",
    )
    plot_hfss_curves(
        frequency, [z_in.real, z_in.imag], labels=["Re(Z11)", "Im(Z11)"],
        colors=Z_COLORS, title="Z Parameter Plot", ylabel="Impedance [ohms]",
        flag_show=False,
    )

    # Calculate physical quantities separately from plotting.
    z0 = 50.0
    calculated_db = 20 * np.log10(np.abs((z_in - z0) / (z_in + z0)))
    error = calculated_db - s11_db
    with plt.rc_context(PLOT_CONFIG):
        fig, (ax, residual) = plt.subplots(
            2, 1, figsize=(9, 6), sharex=True, height_ratios=[2, 1],
            constrained_layout=True,
        )
    plot_hfss_curves(
        frequency, [s11_db, calculated_db], ax=ax,
        labels=["HFSS CSV", f"From Z ({z0:g} ohms)"],
        colors=S11_COLORS, linestyles=["-", "--"],
        title="S11: HFSS vs. Impedance Formula", xlabel="", ylabel="S11 [dB]",
        flag_show=False,
    )
    plot_hfss_curves(
        frequency, error, ax=residual, title="Residual: Formula - HFSS",
        ylabel="Difference [dB]", flag_show=False,
    )
    residual.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    print(f"Maximum absolute error: {np.max(np.abs(error)):.3e} dB")
    print(f"RMS error: {np.sqrt(np.mean(error**2)):.3e} dB")
    plt.show()
