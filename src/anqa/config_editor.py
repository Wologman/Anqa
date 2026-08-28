"""Minimal settings editor for config.yaml - no coding required to use."""
import tkinter as tk
from tkinter import filedialog, messagebox
import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"

DEFAULTS = {
    "source_dataset_path": None,
    "reviewed_data_destn": None,
    "naming_csv": None,
    "author": "",
    "reviewer": None,
    "map_extents": "new_zealand",
    "display_width": 16,
}


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f) or {}
    else:
        print(f'Warning:  No config file was found at {CONFIG_PATH}')
        cfg = {}
    return {**DEFAULTS, **cfg}


def save_config(cfg):
    # Write blank fields back as null rather than empty string, so the
    # notebook's `cfg.get(...) or default` fallback logic keeps working.
    clean = {k: (v if v not in ("", None) else None) for k, v in cfg.items()}
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(clean, f, sort_keys=False)


class ConfigEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Annotator Settings")
        self.resizable(False, False)
        self.cfg = load_config()
        self.vars = {}

        self._build_path_row("source_dataset_path", "Source audio folder", is_dir=True)
        self._build_path_row("reviewed_data_destn", "Reviewed data folder", is_dir=True)
        self._build_path_row("naming_csv", "Bird names CSV", is_dir=False)
        self._build_text_row("author", "Author | Name if first to annotate")
        self._build_text_row("reviewer", "Reviewer | Leave blank unless reviewing")
        self._build_text_row("display_width", "Display Width | Adjust for your screen size")
        self._build_dropdown_row("map_extents", "Map region",
                          options=list(self.cfg.get("geographic_extents", {}).keys()))

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=99, column=0, columnspan=3, pady=12)
        tk.Button(btn_frame, text="Save settings and run", command=self.on_save, width=16).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Cancel", command=self.destroy, width=10).pack(side="left", padx=6)

        help_text = (
                    "Fill in the folders and settings above, then click 'Save settings and run' to run the annotation notebook.\n\n"
                    "To set up a new region for the basemap you can manually edit config.yaml, or you can do it interactively with the explore_data notebook"
                    )
        tk.Label(
            self,
            text=help_text,
            justify="left",
            wraplength=420,
            fg="gray30",
        ).grid(row=98, column=0, columnspan=3, sticky="w", padx=8, pady=(12, 0))
        

    def _build_dropdown_row(self, key, label, options):
        row = len(self.vars)
        tk.Label(self, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=4)

        current = self.cfg.get(key)
        if current not in options:
            current = options[0]

        var = tk.StringVar(value=current)
        self.vars[key] = var

        tk.OptionMenu(self, var, *options).grid(row=row, column=1, sticky="ew", padx=6, pady=4)


    def _row(self):
        row = getattr(self, "_next_row", 0)
        self._next_row = row + 1
        return row

    def _build_text_row(self, key, label):
        row = self._row()
        tk.Label(self, text=label, anchor="w").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        var = tk.StringVar(value="" if self.cfg[key] is None else str(self.cfg[key]))
        tk.Entry(self, textvariable=var, width=45).grid(row=row, column=1, padx=4)
        self.vars[key] = var


    def _build_path_row(self, key, label, is_dir):
        row = self._row()
        tk.Label(self, text=label, anchor="w").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        var = tk.StringVar(value="" if self.cfg[key] is None else str(self.cfg[key]))
        tk.Entry(self, textvariable=var, width=80).grid(row=row, column=1, padx=4)

        def browse():
            if is_dir:
                chosen = filedialog.askdirectory(title=f"Select: {label}")
            else:
                chosen = filedialog.askopenfilename(title=f"Select: {label}")
            if chosen:
                var.set(chosen)

        tk.Button(self, text="Browse...", command=browse).grid(row=row, column=2, padx=4)
        self.vars[key] = var

    def on_save(self):
        try:
            new_cfg = {**self.cfg, **{k: v.get() for k, v in self.vars.items()}}
            if new_cfg["display_width"]:
                new_cfg["display_width"] = int(new_cfg["display_width"])
            save_config(new_cfg)
        except Exception as e:
            messagebox.showerror("Couldn't save settings", str(e))
            return
        self.destroy()


if __name__ == "__main__":
    ConfigEditor().mainloop()