#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易經起卦 — macOS 應用程式入口
"""
import sys
import os

# 讓 app bundle 也能找到快取
os.environ.setdefault("KANGXI_CACHE", os.path.expanduser("~/.kangxi_strokes_cache.pkl"))

import customtkinter as ctk
from kangxi_strokes import (
    load_data, mod8, get_dizhi,
    KANGXI_RADICALS, BAGUA, DIZHI, HEXAGRAMS,
    TRIGRAM_BITS, BITS_TO_TRIGRAM, YAO_SYM,
)
import datetime

# ── 載入 decoding-iching 吉凶預測 ──────────────────────────
import importlib.util as _ilu

def _load_hex_lookup() -> dict:
    _mod_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "decoding-iching", "scripts", "core",
                             "iching_lookup_predictor.py")
    spec = _ilu.spec_from_file_location("iching_lookup_predictor", _mod_path)
    if spec is None or spec.loader is None:
        return {}
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[arg-type]
    return getattr(mod, "HEXAGRAM_LOOKUP", {})

_HEX_LOOKUP: dict = _load_hex_lookup()
_ICHING_AVAILABLE = bool(_HEX_LOOKUP)

_PRED_LABEL = {1: "吉", 0: "中", -1: "凶"}
_PRED_COLOR = {1: "#82C882", 0: "#C8A96E", -1: "#E06060"}
_SCORE_LABEL = [
    (4,  "大吉卦"),
    (2,  "吉卦"),
    (0,  "平卦"),
    (-2, "小凶卦"),
    (-99,"凶卦"),
]

def _hex_score_label_from(positions: list[int]) -> tuple[int, str]:
    total = sum(positions)
    for threshold, label in _SCORE_LABEL:
        if total >= threshold:
            return total, label
    return total, "凶卦"


# ── 顏色與字型 ───────────────────────────────────────────────
GOLD   = "#C8A96E"
DARK   = "#1A1A1A"
PANEL  = "#242424"
CARD   = "#2E2E2E"
DIM    = "#888888"
WHITE  = "#EFEFEF"
RED    = "#E06060"
GREEN  = "#82C882"

FONT_TITLE  = ("Songti SC", 22, "bold")
FONT_BODY   = ("Songti SC", 15)
FONT_SMALL  = ("Songti SC", 13)
FONT_GUA    = ("Songti SC", 28, "bold")
FONT_YAO    = ("Menlo", 14)
FONT_INPUT  = ("Songti SC", 28)


def compute(char: str, data: dict) -> dict | None:
    cp = ord(char)
    if cp not in data:
        return None

    radical_num, additional, is_simplified = data[cp]
    rad_strokes, rad_char = KANGXI_RADICALS.get(radical_num, (0, "?"))
    total = rad_strokes + additional
    upper_num = mod8(total)
    upper_name, upper_sym = BAGUA[upper_num]

    dz_idx, dz_name, dz_period = get_dizhi()
    dz_mod = mod8(dz_idx)
    lower_num = mod8(upper_num + dz_mod)
    lower_name, lower_sym = BAGUA[lower_num]

    hex_no, hex_name = HEXAGRAMS[(upper_num, lower_num)]

    # 之卦
    raw_sum = total + dz_idx
    yao_pos = raw_sum % 6 or 6
    all_yao = list(TRIGRAM_BITS[lower_num]) + list(TRIGRAM_BITS[upper_num])
    original_yao = all_yao[yao_pos - 1]
    all_yao[yao_pos - 1] = 1 - original_yao
    zhi_lower_num = BITS_TO_TRIGRAM[tuple(all_yao[0:3])]
    zhi_upper_num = BITS_TO_TRIGRAM[tuple(all_yao[3:6])]
    zhi_hex_no, zhi_hex_name = HEXAGRAMS[(zhi_upper_num, zhi_lower_num)]
    _, zhi_upper_sym = BAGUA[zhi_upper_num]
    _, zhi_lower_sym = BAGUA[zhi_lower_num]

    return dict(
        char=char, cp=cp,
        radical_num=radical_num, rad_char=rad_char,
        rad_strokes=rad_strokes, additional=additional, total=total,
        is_simplified=is_simplified,
        upper_num=upper_num, upper_name=upper_name, upper_sym=upper_sym,
        dz_idx=dz_idx, dz_name=dz_name, dz_period=dz_period, dz_mod=dz_mod,
        lower_num=lower_num, lower_name=lower_name, lower_sym=lower_sym,
        hex_no=hex_no, hex_name=hex_name,
        yao_pos=yao_pos, original_yao=original_yao,
        zhi_hex_no=zhi_hex_no, zhi_hex_name=zhi_hex_name,
        zhi_upper_sym=zhi_upper_sym, zhi_lower_sym=zhi_lower_sym,
        all_yao_before=list(TRIGRAM_BITS[lower_num]) + list(TRIGRAM_BITS[upper_num]),
        all_yao_after=all_yao,
    )


def yao_lines(bits: list[int], mark: int | None = None) -> list[tuple[str, bool]]:
    """從第6爻到第1爻，回傳 (爻線文字, 是否為變爻)。"""
    rows = []
    for i in range(5, -1, -1):
        sym = "────────" if bits[i] == 1 else "────  ────"
        is_mark = (mark is not None) and (i + 1 == mark)
        rows.append((sym, is_mark))
    return rows


class App(ctk.CTk):
    def __init__(self, data: dict):
        super().__init__()
        self.data = data
        self.title("易經起卦")
        self.geometry("760x700")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.configure(fg_color=DARK)
        self._build_ui()

    def _build_ui(self):
        # ── 標題列 ───────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0, height=64)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="易  經  起  卦", font=FONT_TITLE,
                     text_color=GOLD).pack(side="left", padx=24, pady=14)

        self.clock_lbl = ctk.CTkLabel(hdr, text="", font=FONT_SMALL,
                                      text_color=DIM)
        self.clock_lbl.pack(side="right", padx=20)
        self._tick()

        # ── 輸入區 ───────────────────────────────
        inp_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        inp_frame.pack(fill="x", padx=20, pady=(16, 0))

        ctk.CTkLabel(inp_frame, text="輸入漢字", font=FONT_SMALL,
                     text_color=DIM).pack(anchor="w", padx=16, pady=(10, 0))

        row = ctk.CTkFrame(inp_frame, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(4, 12))

        self.entry = ctk.CTkEntry(row, font=FONT_INPUT, width=120, height=56,
                                  placeholder_text="字", justify="center",
                                  fg_color=CARD, border_color=GOLD,
                                  text_color=WHITE)
        self.entry.pack(side="left")
        self.entry.bind("<Return>", lambda _: self._on_query())

        btn = ctk.CTkButton(row, text="起卦", font=("Songti SC", 16, "bold"),
                            width=100, height=56, fg_color=GOLD,
                            text_color=DARK, hover_color="#A8893E",
                            command=self._on_query)
        btn.pack(side="left", padx=(12, 0))

        self.err_lbl = ctk.CTkLabel(row, text="", font=FONT_SMALL,
                                    text_color=RED)
        self.err_lbl.pack(side="left", padx=12)

        # ── 結果捲動區 ───────────────────────────
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=DARK,
                                             scrollbar_button_color=PANEL)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=12)

    # ── 時鐘 ─────────────────────────────────────
    def _tick(self):
        now = datetime.datetime.now()
        _, dz_name, dz_period = get_dizhi()
        self.clock_lbl.configure(
            text=f"{now.strftime('%H:%M:%S')}　{dz_name}時 {dz_period}"
        )
        self.after(1000, self._tick)

    # ── 清空結果區 ───────────────────────────────
    def _clear_results(self):
        for w in self.scroll.winfo_children():
            w.destroy()

    # ── 起卦 ─────────────────────────────────────
    def _on_query(self):
        self.err_lbl.configure(text="")
        text = self.entry.get().strip()
        if not text:
            return
        self._clear_results()
        for ch in text:
            cp = ord(ch)
            if not (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF
                    or 0x20000 <= cp <= 0x2A6DF or 0xF900 <= cp <= 0xFAFF):
                self.err_lbl.configure(text=f"「{ch}」不是漢字")
                continue
            r = compute(ch, self.data)
            if r is None:
                self.err_lbl.configure(text=f"「{ch}」查無資料")
                continue
            self._render_result(r)

    # ── 渲染單字結果 ─────────────────────────────
    def _render_result(self, r: dict):
        outer = ctk.CTkFrame(self.scroll, fg_color=PANEL, corner_radius=14)
        outer.pack(fill="x", pady=(0, 16))

        # 字 + 筆畫資訊
        top = ctk.CTkFrame(outer, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(14, 6))

        ctk.CTkLabel(top, text=r["char"], font=("Songti SC", 52, "bold"),
                     text_color=GOLD, width=72).pack(side="left")

        info = ctk.CTkFrame(top, fg_color="transparent")
        info.pack(side="left", padx=16)
        simplified = "（省略形）" if r["is_simplified"] else ""
        self._lbl(info, f"康熙部首　第 {r['radical_num']} 部「{r['rad_char']}」{simplified}", DIM)
        self._lbl(info,
                  f"部首 {r['rad_strokes']} 畫 ＋ 部首外 {r['additional']} 畫 ＝ 共 {r['total']} 畫",
                  WHITE)
        self._lbl(info,
                  f"{r['total']} ÷ 8 餘 {r['upper_num']}　上卦 → {r['upper_sym']} {r['upper_name']}",
                  GOLD)
        self._lbl(info,
                  f"時辰 {r['dz_name']}（{r['dz_period']}）編號 {r['dz_idx']}，"
                  f"÷ 8 餘 {r['dz_mod']}　下卦 → {r['lower_sym']} {r['lower_name']}",
                  DIM)

        sep = ctk.CTkFrame(outer, fg_color="#3A3A3A", height=1)
        sep.pack(fill="x", padx=20)

        # 本卦 & 之卦 並排
        body = ctk.CTkFrame(outer, fg_color="transparent")
        body.pack(fill="x", padx=20, pady=12)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)
        body.columnconfigure(2, weight=1)

        # 計算本卦 / 之卦的六爻吉凶
        ben_pred = zhi_pred = None
        if _ICHING_AVAILABLE:
            inner_tri = r['lower_name']
            outer_tri = r['upper_name']
            ben_pred = _HEX_LOOKUP.get((inner_tri, outer_tri), [0] * 6)

            zhi_lower_num = BITS_TO_TRIGRAM[tuple(r['all_yao_after'][0:3])]
            zhi_upper_num = BITS_TO_TRIGRAM[tuple(r['all_yao_after'][3:6])]
            zhi_inner = BAGUA[zhi_lower_num][0]
            zhi_outer = BAGUA[zhi_upper_num][0]
            zhi_pred = _HEX_LOOKUP.get((zhi_inner, zhi_outer), [0] * 6)

        self._render_hex_card(body, col=0,
                              title="本  卦",
                              sym=f"{r['upper_sym']}{r['lower_sym']}",
                              no=r['hex_no'], name=r['hex_name'],
                              bits=r['all_yao_before'],
                              mark=r['yao_pos'],
                              yao_pred=ben_pred)

        # 中間變爻說明
        mid = ctk.CTkFrame(body, fg_color="transparent")
        mid.grid(row=0, column=1, padx=10, sticky="ns")
        yao_type = "陽爻" if r["original_yao"] == 1 else "陰爻"
        yao_new  = "陰爻" if r["original_yao"] == 1 else "陽爻"
        ctk.CTkLabel(mid, text="→", font=("Menlo", 26), text_color=GOLD
                     ).pack(expand=True)
        self._lbl(mid,
                  f"({r['total']}+{r['dz_idx']}) ÷ 6\n餘 {r['yao_pos']}",
                  DIM, center=True)
        self._lbl(mid, f"第{r['yao_pos']}爻", WHITE, center=True)
        self._lbl(mid, f"{yao_type}→{yao_new}", GOLD, center=True)

        self._render_hex_card(body, col=2,
                              title="之  卦",
                              sym=f"{r['zhi_upper_sym']}{r['zhi_lower_sym']}",
                              no=r['zhi_hex_no'], name=r['zhi_hex_name'],
                              bits=r['all_yao_after'],
                              yao_pred=zhi_pred)

    def _render_hex_card(self, parent, col: int, title: str,
                         sym: str, no: int, name: str,
                         bits: list[int], mark: int | None = None,
                         yao_pred: list[int] | None = None):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=10)
        card.grid(row=0, column=col, sticky="nsew", padx=4)

        ctk.CTkLabel(card, text=title, font=FONT_SMALL,
                     text_color=DIM).pack(pady=(10, 0))
        ctk.CTkLabel(card, text=sym, font=("Songti SC", 36),
                     text_color=GOLD).pack()
        ctk.CTkLabel(card, text=f"第 {no:02d} 卦", font=FONT_SMALL,
                     text_color=DIM).pack()
        ctk.CTkLabel(card, text=name, font=("Songti SC", 17, "bold"),
                     text_color=WHITE).pack(pady=(0, 8))

        # 爻線（第6爻在頂，i=0 對應第6爻）
        for i, (sym_yao, is_mark) in enumerate(yao_lines(bits, mark)):
            pos = 6 - i          # 爻位 6→1
            row_f = ctk.CTkFrame(card, fg_color="transparent")
            row_f.pack(pady=1)
            line_color = RED if is_mark else (GOLD if bits[pos - 1] == 1 else "#7090C0")
            ctk.CTkLabel(row_f, text=sym_yao, font=FONT_YAO,
                         text_color=line_color, width=130).pack(side="left")
            lbl_txt = f"第{pos}爻" + (" ←" if is_mark else "")
            ctk.CTkLabel(row_f, text=lbl_txt, font=("Menlo", 11),
                         text_color=RED if is_mark else DIM,
                         width=52).pack(side="left", padx=4)
            if yao_pred is not None:
                val = yao_pred[pos - 1]
                ctk.CTkLabel(row_f, text=_PRED_LABEL[val],
                             font=("Songti SC", 13, "bold"),
                             text_color=_PRED_COLOR[val],
                             width=22).pack(side="left")

        # 整體評分
        if yao_pred is not None:
            score, score_lbl = _hex_score_label_from(yao_pred)
            ji  = sum(1 for v in yao_pred if v == 1)
            xng = sum(1 for v in yao_pred if v == -1)
            sep2 = ctk.CTkFrame(card, fg_color="#3A3A3A", height=1)
            sep2.pack(fill="x", padx=8, pady=(6, 4))
            score_color = _PRED_COLOR[1 if score > 0 else (-1 if score < 0 else 0)]
            ctk.CTkLabel(card,
                         text=f"{score_lbl}　吉{ji} 中{6-ji-xng} 凶{xng}（{score:+d}）",
                         font=("Songti SC", 12), text_color=score_color).pack(pady=(0, 8))
        else:
            ctk.CTkFrame(card, fg_color="transparent", height=8).pack()

    def _lbl(self, parent, text: str, color: str, center: bool = False):
        anchor = "center" if center else "w"
        justify = "center" if center else "left"
        ctk.CTkLabel(parent, text=text, font=FONT_SMALL,
                     text_color=color, anchor=anchor, justify=justify
                     ).pack(anchor=anchor, pady=1)


def main():
    ctk.set_appearance_mode("dark")
    root_placeholder = ctk.CTk()
    root_placeholder.withdraw()

    # 載入資料（顯示進度視窗）
    loading = ctk.CTkToplevel()
    loading.title("")
    loading.geometry("320x100")
    loading.resizable(False, False)
    loading.configure(fg_color=DARK)
    loading.lift()
    loading.focus_force()
    ctk.CTkLabel(loading, text="載入漢字資料庫中…",
                 font=FONT_BODY, text_color=GOLD).pack(expand=True)
    loading.update()

    data = load_data()
    loading.destroy()
    root_placeholder.destroy()

    app = App(data)
    app.mainloop()


if __name__ == "__main__":
    main()
