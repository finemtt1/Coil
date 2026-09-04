import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from tabulate import tabulate
import gradio as gr
import io

# =================================================================
# 1. IGBT & 鐵芯 & 預設資料庫
# =================================================================
IGBT_DB = {
    "T121": { "Ron_base": 0.323, "Vth_base": 0.576, "v_slope": 0.0058, "r_slope": -0.0081 },
    "J121": { "Ron_base": 0.423, "Vth_base": 0.708, "v_slope": 0.0058, "r_slope": -0.0081 },
    "Typical_15A_IGBT": { "Ron_base": 0.075, "Vth_base": 1.20, "v_slope": 0.0058, "r_slope": -0.0081 }
}

CORE_DB = {
    "J3_Core": {
        "ref_ni": [504, 772, 980, 1036, 1075], "ref_mu_scale": [1.0, 0.82, 0.62, 0.61, 0.58],
        "base_n2": 13012, "description": "J3 Core"
    },
    "SE35S_SE39S_Core": {
        "ref_ni": [240, 480, 720, 960, 1200], "ref_mu_scale": [1.0, 1.0, 0.856, 0.651, 0.450],
        "base_n2": 21000, "description": "SE35S/SE39S Core"
    }
}

PRESETS = {
    "J3": {
        "primary_turns": 280, "primary_cu_diameter_mm": 0.35, "primary_insulation_mm": 0.01,
        "secondary_turns": 13012, "secondary_cu_diameter_mm": 0.05, "secondary_insulation_mm": 0.004,
        "primary_bobbin_diameter_mm": 16.0, "primary_slot_length_mm": 24.0,
        "secondary_bobbin_diameter_mm": 23.0,
        "secondary_slot_widths_string": "1.0, 1.0, 2.4, 2.4, 2.4, 2.4, 2.4, 2.4, 2.4, 1.0",
        "core_length_mm": 30.0, "core_area_mm2": 80.0, "core_mu_r_eff": 20.93,
        "secondary_packing_factor": 0.85, "secondary_length_buffer": 1.05,
        "primary_stacking_factor": 0.866, "primary_length_buffer": 1.00,
        "applied_core": "J3_Core", "efficiency": 0.75
    },
    "SE35S": {
        "primary_turns": 240, "primary_cu_diameter_mm": 0.35, "primary_insulation_mm": 0.01,
        "secondary_turns": 21000, "secondary_cu_diameter_mm": 0.045, "secondary_insulation_mm": 0.004,
        "primary_bobbin_diameter_mm": 14.6, "primary_slot_length_mm": 23.6,
        "secondary_bobbin_diameter_mm": 22.8,
        "secondary_slot_widths_string": "2.8, 2.8, 2.8, 2.8, 2.8, 2.8, 2.8",
        "core_length_mm": 30.0, "core_area_mm2": 100, "core_mu_r_eff": 19.07,
        "secondary_packing_factor": 0.85, "secondary_length_buffer": 1.05,
        "primary_stacking_factor": 0.866, "primary_length_buffer": 1.00,
        "applied_core": "SE35S_SE39S_Core", "efficiency": 0.65
    },
    "SE39S": {
        "primary_turns": 250, "primary_cu_diameter_mm": 0.35, "primary_insulation_mm": 0.01,
        "secondary_turns": 17850, "secondary_cu_diameter_mm": 0.04, "secondary_insulation_mm": 0.003,
        "primary_bobbin_diameter_mm": 14.0, "primary_slot_length_mm": 23.5,
        "secondary_bobbin_diameter_mm": 20.4,
        "secondary_slot_widths_string": "2.8, 2.8, 2.8, 2.8, 2.8, 2.8, 2.8",
        "core_length_mm": 28.95, "core_area_mm2": 100, "core_mu_r_eff": 18.28,
        "secondary_packing_factor": 0.85, "secondary_length_buffer": 1.05,
        "primary_stacking_factor": 0.866, "primary_length_buffer": 1.00,
        "applied_core": "SE35S_SE39S_Core", "efficiency": 0.65
    }
}

# =================================================================
# 2. 核心運算邏輯
# =================================================================
def calculate_mu_r(L_measured_mH, N_turns, core_length_mm, core_area_mm2):
    L_H, l_m, a_m2 = L_measured_mH/1000, core_length_mm/1000, core_area_mm2*1e-6
    mu_0 = 4 * math.pi * 1e-7
    try: mu_r = (L_H * l_m) / (mu_0 * a_m2 * N_turns**2)
    except: return "輸入參數有誤"
    return f"### **📊 鐵芯有效導磁率 (μr) 反推結果**\n- **實測 L1**：`{L_measured_mH:.2f} mH`\n- **推算有效導磁率 (μr)** ≈ `{mu_r:.2f}`\n\n*(💡 請將此導磁率數值填入主畫面的「有效導磁率 (Effective μr)」)*"

def generate_n2_scan_range(n2):
    base = int(n2); steps = [base - 1500, base - 1000, base - 500, base, base + 500, base + 1000, base + 1500]
    return ", ".join(map(str, [s for s in steps if s > 0]))

def load_preset_data(m):
    if m not in PRESETS: return gr.update()
    d = PRESETS[m]
    return (
        d["primary_turns"], d["primary_cu_diameter_mm"], d["primary_insulation_mm"],
        d["secondary_turns"], d["secondary_cu_diameter_mm"], d["secondary_insulation_mm"],
        d["primary_bobbin_diameter_mm"], d["primary_slot_length_mm"], d["secondary_bobbin_diameter_mm"],
        d["core_length_mm"], d["core_area_mm2"], d["core_mu_r_eff"], d["secondary_slot_widths_string"],
        d["secondary_packing_factor"], d["secondary_length_buffer"],
        d["primary_stacking_factor"], d["primary_length_buffer"],
        d["applied_core"], d["efficiency"], generate_n2_scan_range(d["secondary_turns"])
    )

def generate_n1_scan_range(n1):
    base = int(n1); vals = [base - 30, base - 20, base - 10, base, base + 10, base + 20, base + 30]
    return ", ".join(map(str, [s for s in vals if s > 0]))

def run_simulation(
    mag_circuit_type,
    core_selection, efficiency, op_temp, igbt_model, V_in, chargetime_ms,
    core_length_mm, core_area_mm2, mu_r_eff,
    cu_diameter_mm_p, insulation_mm_p, turns_p, bobbin_diameter_mm_p, bobbin_slot_length_mm_p,
    primary_stacking_factor, primary_length_buffer,
    cu_diameter_mm_s, insulation_mm_s, turns_s, bobbin_diameter_mm_s,
    slot_widths_mm_s_str, turns_s_range_str, turns_p_range_str,
    packing_factor_s, length_buffer_ratio_s, ext_cap_pf
):
    if not (0 < packing_factor_s <= 1.0) or V_in <= 0 or chargetime_ms <= 0:
        return "❌ 參數錯誤 (請檢查緊密度或電壓輸入)", None
        
    core_length_m, core_area_m2 = core_length_mm/1000, core_area_mm2*1e-6
    chargetime, mu_0 = chargetime_ms/1000, 4*math.pi*1e-7
    
    # 工作溫度修正銅阻抗
    rho_copper = 1.724e-8 * (1 + 0.00393*(op_temp-20)) # honda規範
    slot_widths_mm_s = [float(x.strip()) for x in slot_widths_mm_s_str.split(',') if x.strip()]
    turns_s_range = [int(x.strip()) for x in turns_s_range_str.split(',') if x.strip()]
    turns_p_range = [int(x.strip()) for x in turns_p_range_str.split(',') if x.strip()]

    # ==========================
    # calc_pri: 一次側幾何 + RL 積分
    # ==========================
    core_char = CORE_DB.get(core_selection, CORE_DB["J3_Core"])
    ref_ni = core_char["ref_ni"]; ref_mu_scale = core_char["ref_mu_scale"]
    igbt_base = IGBT_DB.get(igbt_model, IGBT_DB["T121"])
    v_th_dyn = igbt_base["Vth_base"] + igbt_base["v_slope"] * (V_in - 14.0)
    r_on_dyn = igbt_base["Ron_base"] + igbt_base["r_slope"] * (V_in - 14.0)
    
    def calc_pri(N1_in):
        total_dia = cu_diameter_mm_p + 2*insulation_mm_p
        n_base = max(1, math.floor(bobbin_slot_length_mm_p / total_dia))
        rem = N1_in; lyr = 0; l_wire = 0; hf = primary_stacking_factor
        while rem > 0:
            lyr += 1
            t_lay = min(n_base if lyr % 2 == 1 else max(1, n_base - 1), rem)
            r_mm = (bobbin_diameter_mm_p / 2) + (total_dia / 2) + (lyr - 1) * total_dia * hf
            l_wire += t_lay * 2 * math.pi * (r_mm / 1000)
            rem -= t_lay
        l_wire *= primary_length_buffer
        r1 = rho_copper * l_wire / (math.pi * ((cu_diameter_mm_p/2)/1000)**2)
        thick = total_dia + (lyr - 1) * total_dia * hf if lyr > 0 else 0
        od = bobbin_diameter_mm_p + 2 * thick
        l1 = (N1_in**2) * mu_0 * mu_r_eff * core_area_m2 / core_length_m
        
        steps_i = 500; dt_i = chargetime / steps_i
        t_ax = np.linspace(0, chargetime, steps_i)
        i_crv = np.zeros(steps_i); vce_crv = np.zeros(steps_i); ci = 0.0
        for k in range(1, steps_i):
            vd = max(0.5, ci * r_on_dyn + v_th_dyn)
            vce_crv[k] = vd; ve = max(0, V_in - vd)
            dms = np.interp(N1_in * ci, ref_ni, ref_mu_scale) if mag_circuit_type == "閉磁路 (Closed-Circuit, 動態飽和)" else 1.0
            ci += ((ve - ci * r1) / max(l1 * dms, 1e-6)) * dt_i
            i_crv[k] = max(0, ci)
        return l1, i_crv[-1], i_crv, vce_crv, r1, l_wire, lyr, od, t_ax

    # 用目前匝數跑主模擬
    steps = 500; t_axis = np.linspace(0, chargetime, steps)
    L1_nom, I_peak, I_curve, Vce_curve, R1, len_p, layers_p, estimated_OD_p, _ = calc_pri(turns_p)

    # ==========================
    # 二次側幾何與物理計算
    # ==========================
    def calc_sec(N2_in):
        wire_full_dia_s = cu_diameter_mm_s + 2*insulation_mm_s
        total_width = sum(slot_widths_mm_s)
        turns_per_slot = [math.floor(N2_in*(w/total_width)) for w in slot_widths_mm_s]
        turns_per_slot[-1] += N2_in - sum(turns_per_slot)
        len_s_total, max_h_accum, total_layers = 0, 0, 0
        
        for i, ns in enumerate(turns_per_slot):
            slot_w = slot_widths_mm_s[i]
            wire_total_dia = max(wire_full_dia_s, 1e-9)
            turns_per_layer = max(1, math.floor(slot_w / wire_total_dia))
            layers_in_slot = math.ceil(ns / turns_per_layer)
            total_layers += layers_in_slot
            for lay in range(layers_in_slot):
                layer_dia = bobbin_diameter_mm_s + 2 * (lay * wire_full_dia_s / packing_factor_s)
                len_s_total += min(turns_per_layer, ns - lay * turns_per_layer) * math.pi * (layer_dia / 1000)
            max_h_accum = max(max_h_accum, (layers_in_slot * wire_full_dia_s) / packing_factor_s)
            
        R2 = rho_copper * len_s_total * length_buffer_ratio_s / (math.pi*((cu_diameter_mm_s/2)/1000)**2)
        estimated_OD = bobbin_diameter_mm_s + 2 * max_h_accum
        final_mu_scale = np.interp(turns_p*I_peak, ref_ni, ref_mu_scale) if mag_circuit_type == "閉磁路 (Closed-Circuit, 動態飽和)" else 1.0
        L1_eff = L1_nom * final_mu_scale
        L2_nom = (N2_in**2)*mu_0*mu_r_eff*core_area_m2/core_length_m
        
        area_scale = (bobbin_diameter_mm_s * total_width) / (23.0 * sum([1.0, 1.0, 2.4, 2.4, 2.4, 2.4, 2.4, 2.4, 2.4, 1.0]))
        # 修正：使用 400.0 作為整體線圈層數的縮放基準錨點
        layer_scale = 400.0 / max(total_layers, 1)
        
        # 💡 解放極限：使用 22.5pF 純物理本質基準
        cs_final = max(15.0, 22.5 * area_scale * layer_scale + ((cu_diameter_mm_s - 0.04) / 0.005 * 5.0))
        
        C_total_F = (cs_final + ext_cap_pf) * 1e-12
        
        # 💡 線性效率修正：先求理論極大值，再乘以 Efficiency 折損係數
        ideal_V2 = I_peak * math.sqrt(L1_eff / C_total_F)
        V2 = ideal_V2 * efficiency
        
        return R2, V2, estimated_OD, f"{cs_final:.1f}", final_mu_scale, len_s_total, total_layers, L2_nom

    # ==========================
    # 生成 Markdown 數據表
    # ==========================
    output = io.StringIO(); p = lambda t: print(t, file=output)
    main_res = calc_sec(turns_s)
    R2_val, V2_val, OD_s, cs_val, mu_scale, len_s, layers_s, L2_val = main_res
    primary_energy_mj = 0.5 * (L1_nom * mu_scale) * (I_peak**2) * 1000
    
    # --- 1. 電氣特性 ---
    p("### ⚡ 1. 電氣特性 (Electrical)")
    elec_data = [
        ["工作溫度 (Temp)",       f"{op_temp:.1f} °C",              "反映純銅在當下溫度的真實阻抗"],
        ["一次蓄積能量 (Energy)", f"{primary_energy_mj:.1f} mJ",    "決定火花強度"],
        ["一次峰值電流 (I_peak)", f"{I_peak:.3f} A",                "充磁結束瞬間的峰值"],
        ["一次電阻 (R1)",         f"{R1:.3f} Ω",                    "工作溫度修正後之純銅阻抗"],
        ["一次電感 (L1)",         f"{L1_nom * 1000:.3f} mH",        "由鐵芯面積與有效導磁率算出"],
        ["二次電阻 (R2)",         f"{R2_val/1000:.2f} kΩ",          "工作溫度修正後之純銅阻抗"],
        ["二次電感 (L2)",         f"{L2_val:.3f} H",                "理想磁耦合下的等效值"],
        ["二次峰值電壓 (V2)",     f"{abs(V2_val)/1000:.2f} kV",     "理論最高崩潰電壓"],
        ["二次寄生電容 (Cs)",     f"{cs_val} pF",                   "數值越高衰減的 V2 就越多"],
    ]
    p(tabulate(elec_data, headers=["參數", "數值", "說明"], tablefmt="pipe"))

    # --- 2. 幾何特性 ---
    p("\n### 📏 2. 幾何特性 (Mechanical)")
    mech_data = [
        ["繞線層數",                   f"{layers_p} 層",                                      f"{layers_s} 層"],
        ["銅線長度",                   f"{len_p:.2f} m",                                      f"{len_s:.1f} m"],
        ["線輪架外徑 (Bobbin OD)",     f"{bobbin_diameter_mm_p:.2f} mm",                      f"{bobbin_diameter_mm_s:.2f} mm"],
        ["單側繞線厚度 (Thickness)",   f"{(estimated_OD_p - bobbin_diameter_mm_p)/2:.2f} mm", f"{(OD_s - bobbin_diameter_mm_s)/2:.2f} mm"],
        ["完成總外徑 (Total OD)",      f"{estimated_OD_p:.2f} mm",                            f"{OD_s:.2f} mm"],
    ]
    p(tabulate(mech_data, headers=["項目", "🟢 一次側", "🔴 二次側"], tablefmt="pipe", stralign="center"))
    
    # --- 3. N1 掃描 ---
    if turns_p_range:
        p("\n### 🔍 3. N1 掃描 — 電氣特性")
        tbl_p_e, tbl_p_m = [], []
        for n1 in turns_p_range:
            l1, ipk, _, _, r1_s, lw, ly, od_p, _ = calc_pri(n1)
            energy = 0.5 * l1 * (ipk**2) * 1000
            tbl_p_e.append([n1, f"{r1_s:.3f}", f"{l1*1000:.2f}", f"{ipk:.3f}", f"{energy:.1f}"])
            tbl_p_m.append([n1, f"{ly}", f"{od_p:.2f}", f"{lw:.2f}"])
        p(tabulate(tbl_p_e, headers=["N1", "R1 (Ω)", "L1 (mH)", "I_peak (A)", "Energy (mJ)"], tablefmt="pipe", stralign="center"))
        
        p("\n### 🔍 4. N1 掃描 — 幾何尺寸")
        p(tabulate(tbl_p_m, headers=["N1", "層數", "OD (mm)", "總線長 (m)"], tablefmt="pipe", stralign="center"))
        
    # --- N2 掃描 ---
    if turns_s_range:
        p(f"\n### 🔍 5. N2 掃描 — 電氣特性 (一次側規格：{cu_diameter_mm_p:.2f}mm × {int(turns_p)}T)")
        tbl_e, tbl_m = [], []
        for t in turns_s_range:
            r = calc_sec(t)
            if r:
                tbl_e.append([t, f"{r[0]/1000:.2f}", f"{r[3]}", f"{abs(r[1])/1000:.2f}", f"{r[7]:.3f}"])
                tbl_m.append([t, f"{r[6]}", f"{r[2]:.2f}", f"{r[5]:.1f}"])
        p(tabulate(tbl_e, headers=["N2", "R2 (kΩ)", "Cs (pF)", "V2 (kV)", "L2 (H)"], tablefmt="pipe", stralign="center"))
        
        p("\n### 🔍 6. N2 掃描 — 幾何尺寸")
        p(tabulate(tbl_m, headers=["N2", "層數", "OD (mm)", "總線長 (m)"], tablefmt="pipe", stralign="center"))
        
    fig = Figure(figsize=(10, 6))
    ax1, ax2 = fig.subplots(2, 1, sharex=True)
    ax1.plot(t_axis*1000, I_curve, color='tab:blue', linewidth=2)
    ax1.text(t_axis[-1]*1000, I_peak, f" {I_peak:.2f} A", color='tab:blue', verticalalignment='bottom', fontweight='bold')
    ax1.set_ylabel('Current (A)'); ax1.grid(True, alpha=0.3)
    ax1.set_title(f"Primary Current Rise ({mag_circuit_type.split(',')[0]})")
    ax2.plot(t_axis*1000, np.full(steps, V_in), color='gold', linewidth=2)
    ax2.plot(t_axis*1000, Vce_curve, color='#ff00ff', linewidth=2)
    ax2.text(t_axis[-1]*1000, Vce_curve[-1], f" {Vce_curve[-1]:.2f} V", color='#ff00ff', verticalalignment='bottom', fontweight='bold')
    ax2.fill_between(t_axis*1000, Vce_curve, V_in, color='green', alpha=0.1)
    ax2.set_ylabel("Voltage (V)"); ax2.set_xlabel("Time (ms)"); ax2.grid(True, alpha=0.3)
    fig.tight_layout()
    
    return output.getvalue(), fig

# =================================================================
# 3. 介面與排版
# =================================================================
with gr.Blocks(title="Ignition Coil V16") as demo:
    gr.Markdown("# ⚡ Ignition Coil Designer (V16)")
    
    with gr.Tabs():
        with gr.TabItem("📖 使用教學"):
            gr.Markdown("""
            ### 🛠️ 點火線圈反推步驟
            **📍 情境：您手上有一顆未知的點火線圈，想透過軟體反推它的機制或測試不同設計。**
            
            #### 步驟 1：量測基準實物資料
            1. **量測鐵芯**：拆開鐵芯，量測「鐵芯面積(mm²)」與「磁路長度(mm)」。填入左側「1. 鐵芯與環境」區塊。
            2. **量測一次側**：量出一次側的「線輪架外徑」、「槽寬」，以及「銅線徑」。填入中間「2. 一次側配置 (Primary)」區塊。
            3. **取得 L1**：用 LCR Meter (1kHz) 實測這顆線圈的 L1。
            *(💡 提示：如果您不知道鐵芯有效 μr，請切換到上方 `🧰 μr 反推工具` 分頁，輸入量測結果反推，再將它填入「⚙️進階參數」內。)*
            
            #### 步驟 2：選擇磁路物理並驗證鐵芯
            確認樣品是 **開磁路** (如直筆狀) 還是 **閉磁路** (如口字/日字型)。開磁路請選「線性」，閉磁路請選「動態飽和」。設定完畢後按下「🚀 執行反推模擬」，即可觀察右側電流爬升波形。
            
            #### 步驟 3：二次繞線與高壓極值反推
            1. **量測二次側**：量測二次線輪架「外徑」，並記錄「各個槽寬」。填入右側「3. 二次側配置 (Secondary)」區塊。
            2. **設定轉換效率**：展開「⚙️進階參數」，在 `線性修正效率 (Efficiency)` 中填入折損係數 (例如：0.75)。1.0 代表絕對物理極限。
            3. **效能比對**：比對模擬跑出的 V2 是否符合預期。若實際產生的高壓低於模擬值，代表樣品漏磁或損耗嚴重，請微調降低 Efficiency 參數。
            
            #### 步驟 4：進行幾何逆向實驗
            - **測試槽寬與層數**：嘗試改變「各槽寬明細」 (例如：把 10 個窄槽改成 2 個大寬槽)。您會在報表中看到**「總繞線層數」大減**，導致「寄生電容」大幅升高，進而吃掉 V2 產生嚴重衰退。
            """)
            
        with gr.TabItem("🎛️ 模擬計算"):
            with gr.Row():
                with gr.Column(variant="panel"):
                    gr.Markdown("### 🧲 1. 鐵芯與環境")
                    mag_circuit_type = gr.Radio(["開磁路 (Open-Circuit, 線性不飽和)", "閉磁路 (Closed-Circuit, 動態飽和)"], value="開磁路 (Open-Circuit, 線性不飽和)", label="📐 行為物理模型 (Physics Model)")
                    preset_dropdown = gr.Dropdown(list(PRESETS.keys()), label="📁 選擇機種 (Select Model)", value="J3")
                    core_select = gr.Dropdown(list(CORE_DB.keys()), label="🧲 選擇鐵芯特性 (Core Material)", value="J3_Core", info="不同鐵芯材質決定了飽和膝點 (Knee Point)")
                    core_length_mm = gr.Number(30.0, label="磁路長度 (Magnetic Path Length) [mm]")
                    core_area_mm2 = gr.Number(80.0, label="鐵芯面積 (Core Area) [mm²]")
                    V_in = gr.Number(14, label="輸入電壓 (Input Voltage) [V]")
                    chargetime_ms = gr.Number(2.5, label="充磁時間 (Dwell Time) [ms]")
                    
                with gr.Column(variant="panel"):
                    gr.Markdown("### 🟢 2. 一次側配置 (Primary)")
                    turns_p = gr.Number(280, label="一次側匝數 (Primary Turns N1)")
                    cu_diameter_mm_p = gr.Number(0.35, label="一次裸銅線徑 (Primary Wire Φ) [mm]")
                    bobbin_diameter_mm_p = gr.Number(16.0, label="一次線輪架外徑 (Pri. Bobbin OD) [mm]")
                    bobbin_slot_length_mm_p = gr.Number(24.0, label="一次線輪架槽寬 (Pri. Net Slot Width) [mm]")
                    turns_p_range = gr.Textbox("250, 260, 270, 280, 290, 300, 310", label="N1 匝數掃描範圍 (N1 Scan Range)")
                    
                with gr.Column(variant="panel"):
                    gr.Markdown("### 🔴 3. 二次側配置 (Secondary)")
                    turns_s = gr.Number(13012, label="二次側匝數 (Secondary Turns N2)")
                    cu_diameter_mm_s = gr.Number(0.05, label="二次裸銅線徑 (Secondary Wire Φ) [mm]")
                    bobbin_diameter_mm_s = gr.Number(23.0, label="二次線輪架外徑 (Sec. Bobbin OD) [mm]")
                    slot_widths_mm_s = gr.Textbox("1.0, 1.0, 2.4, 2.4, 2.4, 2.4, 2.4, 2.4, 2.4, 1.0", label="二次側槽寬 (Sec. Slot Widths) [mm]")
                    turns_s_range = gr.Textbox("11512, 12012, 12512, 13012, 13512, 14012, 14512", label="N2 匝數掃描範圍 (Turns Scan Range)")
                    
            with gr.Accordion("⚙️ 進階參數 (Advanced Params)", open=False):
                with gr.Row():
                    mu_r_eff = gr.Number(20.93, label="有效導磁率 (Effective μr)")
                    efficiency = gr.Number(0.75, label="線性修正效率 (Efficiency)", info="1.0為理想物理極限。填入 0.6~0.9 來對齊實測電壓")
                    ext_cap_pf = gr.Number(0, label="外部負載電容 (Load Cap) [pF]", info="範圍 0~100pF，模擬積碳或負載")
                with gr.Row():
                    op_temp = gr.Number(25.0, label="工作溫度 (Operating Temp) [°C]", info="影響電阻值 (R1, R2)")
                    primary_stacking_factor = gr.Number(0.866, label="一次側堆疊係數 (Pri. Stacking Factor)", info="1.0=一般疊加; 0.866 ( √3 / 2)=正交堆疊")
                    packing_factor_s = gr.Number(0.85, label="二次繞線緊密度 (Sec. Packing Factor)", info="數值越小=繞線越鬆散。調小線圈外徑增加、總電阻(R2)變大。")
                with gr.Row():
                    primary_length_buffer = gr.Number(1.00, label="一次側線長補正 (Pri. Length Buffer)")
                    length_buffer_ratio_s = gr.Number(1.05, label="二次線長補正係數 (Sec. Length Buffer)")
                with gr.Row():
                    insulation_mm_p = gr.Number(0.01, label="一次皮膜厚度 (Pri. Insulation) [mm]")
                    insulation_mm_s = gr.Number(0.004, label="二次絕緣層 (Sec. Insulation) [mm]")
                igbt_model = gr.Dropdown(list(IGBT_DB.keys()), value="T121", visible=False)
                
            btn = gr.Button("🚀 執行反推模擬 (Run Simulation)", variant="primary")
            report_out = gr.Markdown()
            plot_out = gr.Plot()
            
            btn.click(
                run_simulation,
                inputs=[
                    mag_circuit_type,
                    core_select, efficiency, op_temp, igbt_model, V_in, chargetime_ms,
                    core_length_mm, core_area_mm2, mu_r_eff,
                    cu_diameter_mm_p, insulation_mm_p, turns_p, bobbin_diameter_mm_p, bobbin_slot_length_mm_p,
                    primary_stacking_factor, primary_length_buffer,
                    cu_diameter_mm_s, insulation_mm_s, turns_s, bobbin_diameter_mm_s,
                    slot_widths_mm_s, turns_s_range, turns_p_range, packing_factor_s, length_buffer_ratio_s, ext_cap_pf
                ],
                outputs=[report_out, plot_out]
            )
            
            turns_s.change(lambda v: generate_n2_scan_range(v), inputs=[turns_s], outputs=[turns_s_range])
            turns_p.change(lambda v: generate_n1_scan_range(v), inputs=[turns_p], outputs=[turns_p_range])
            
            preset_dropdown.change(
                load_preset_data,
                preset_dropdown,
                [
                    turns_p, cu_diameter_mm_p, insulation_mm_p, turns_s, cu_diameter_mm_s, insulation_mm_s,
                    bobbin_diameter_mm_p, bobbin_slot_length_mm_p, bobbin_diameter_mm_s,
                    core_length_mm, core_area_mm2, mu_r_eff, slot_widths_mm_s,
                    packing_factor_s, length_buffer_ratio_s,
                    primary_stacking_factor, primary_length_buffer,
                    core_select, efficiency, turns_s_range
                ]
            )
            
        with gr.TabItem("🧰 μr 反推工具"):
            gr.Markdown("### 🧲 鐵芯有效導磁率 (μr) 反推計算機\n當您用 LCR Meter 實測出一次側 L1 電感時，請用此工具反推它的有效 μr。")
            
            with gr.Row(variant="panel"):
                with gr.Column():
                    t1_N = gr.Number(label="一次側匝數 N1 (Turns)", value=280)
                    t1_len = gr.Number(label="磁路長度 (Magnetic Path Length) [mm]", value=30.0)
                with gr.Column():
                    t1_area = gr.Number(label="鐵芯面積 (Core Area) [mm²]", value=80.0)
                    t1_L = gr.Number(label="📌 實測 L1 (Measured L1) [mH]", value=5.5)
                    
            btn_calc = gr.Button("執行 μr 反推", variant="secondary")
            t1_output = gr.Markdown()
            btn_calc.click(calculate_mu_r, [t1_L, t1_N, t1_len, t1_area], t1_output)
            
            with gr.Accordion("💡 為什麼需要反推？ (原理與使用心法)", open=False):
                gr.Markdown(r"""
                ### 1. 痛點：理論值與現實的落差
                鐵芯材質的**理論導磁率**通常極高（例如 1000 以上）。但當鐵芯被加工、組裝，尤其是**「開磁路（如筆型線圈）」**或**「有氣隙的閉磁路」**時，磁力線必須穿透空氣，導致整體的**「有效導磁率 (Effective μr)」**大幅下降（通常落在 15 ~ 40 之間）。
                
                ### 2. 物理反推原理
                我們不靠經驗猜測，而是利用實測的電感值 L1 來讓物理公式說話。
                
                * **標準電感公式：**
                $$ L_1 = \frac{N_1^2 \cdot \mu_0 \cdot \mu_r \cdot A}{l_{path}} $$
                
                * **移項後的反推公式：**
                $$ \mu_r = \frac{L_1 \cdot l_{path}}{N_1^2 \cdot \mu_0 \cdot A} $$
                
                ### 3. 使用心法 🎯
                這個反推出來的 μr 包含了所有的**物理現實（氣隙、漏磁、組裝公差）**。
                請將這裡算出的數值，填入主畫面左下方的**「⚙️ 進階參數 ➔ 有效導磁率」**中，您的模擬器就能 100% 貼近這顆真實的樣品體質！
                """)
            
        with gr.TabItem("📐 物理公式 (Formulas)"):
            gr.Markdown(r"""
            ### 1. 繞線幾何與直流電阻計算 (Winding & Resistance)
            
            **一次繞線層數與圈數邏輯**：
            實務上漆包線在繞捲時，偶數層的線會卡在奇數層相鄰銅線的「凹槽」縫隙裡，因此偶數層在排滿時，通常會比奇數層少 1 圈。
            
            ```python
            if layers_p % 2 == 1:
                t_in_this_layer = min(N_base, rem_turns)               # 奇數層：正常塞滿 N_base 圈
            else:
                t_in_this_layer = min(max(1, N_base - 1), rem_turns)   # 偶數層：容量強制扣 1 圈
            ```
            
            **直流阻抗 (R1, R2)**：
            
            $$ R = \rho_T \times \frac{\text{總線長} \times \text{線長寬裕度 (Buffer)}}{\pi \times (r_{wire})^2} $$
            
            * 溫度補償率 **ρ_T** 為純銅在工作溫度下的電阻率。公式為：
            
            $$ \rho_T = 1.724 \times 10^{-8} \times [1 + 0.00393 \times (T_{op} - 20)] $$
            
            ---
            
            ### 2. 電感計算模型 (Inductance L1, L2)
            
            **理論空載標稱值 (L1, L2)**：
            依據鐵芯面積、空心磁路長度與有效導磁率決定：
            
            $$ L_1 = \frac{N_1^2 \cdot \mu_0 \cdot \mu_{r,eff} \cdot A}{l_{path}} \quad,\quad L_2 = \frac{N_2^2 \cdot \mu_0 \cdot \mu_{r,eff} \cdot A}{l_{path}} $$
            
            **時域動態飽和折減 (核心特色，僅限閉磁路)**：
            
            $$ L_{1(dynamic)} = L_{1(nom)} \times \mu_{scale}(I) $$
            
            ---
            
            ### 3. 一次側充磁極值電流 (I_peak)
            
            本質為 RL 暫態電路，加上 IGBT 動態壓降 (**Vce**)。以數值微分法逼近真實曲線：
            
            $$ \frac{di}{dt} = \frac{V_{in} - V_{ce}(I) - I \times R_1}{L_{1(dynamic)}} $$
            
            ---
            
            ### 4. 二次側崩潰電壓極值 (V2)
            
            切斷電源瞬間，鐵芯磁能衝去充飽寄生電容 (Cs)。由能量守恆推導：
            
            $$ \frac{1}{2} L_1 I_{peak}^2 = \frac{1}{2} C_{total} V_{ideal}^2 $$
            
            將理想 V2 拉出，並透過線性係數修正後的實用公式為：
            
            $$ V_2 = \left( I_{peak} \times \sqrt{\frac{L_{1,eff}}{C_{total}}} \right) \times \text{Efficiency} $$
            
            * **C_total**：二次寄生電容 (Cs) + 積碳負載。Cs 會依照「線架極板面積」與「繞線總層數」進行動態縮放。
            * **Efficiency**：此處作為電壓的線性修正係數 (1.0 為理想無損狀態)，用以對齊實際漏磁與測量衰減。
            
            ---
            
            ### 5. 二次側動態寄生電容模型 (Dynamic Parasitic Capacitance)
            
            本系統捨棄傳統定值 (如 70pF) 假設，採用基於線輪架幾何與繞線層數的動態膨脹模型。
            
            * **K_area**：極板面積係數。外徑越大、槽寬越寬，等效極板面積越大。
            
            $$ K_{area} = \frac{OD_{sec} \times W_{total}}{23.0 \times 19.8} $$
            
            * **K_layer**：層數串聯衰減係數。繞線層數越多，微小電容串聯效應越強，總電容越小。
            
            $$ K_{layer} = \frac{400}{\text{Total Layers}} $$
            
            * **Cs**：寄生電容總和。結合純幾何本質電容 (22.5pF) 與線徑表面積補償，並設定 15pF 的物理極限底板。
            
            $$ C_s = \max\left(15.0,\; 22.5 \times K_{area} \times K_{layer} + \frac{d_{wire} - 0.04}{0.005} \times 5.0\right) $$
            """)

if __name__ == "__main__":
    demo.launch()