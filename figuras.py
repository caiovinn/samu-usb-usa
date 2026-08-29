import json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

FIG = Path("figs"); FIG.mkdir(exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 130,
                     "font.size": 9, "axes.grid": True, "grid.alpha": .25,
                     "axes.spines.top": False, "axes.spines.right": False})
C_USB, C_USA, C_OUT = "#2E7D9A", "#C1442E", "#B9BDC1"

df = pd.read_parquet("frota.parquet")
m = pd.read_parquet("municipal.parquet")
a = df[df.ativo]
pub = a[a.setor.isin(["publico", "sem_fins_lucrativos"])]
P = m.populacao.sum()
R = {}

# ---------------------------------------------------------------- 1 composicao
ordem = ["USB", "USA", "MOTOLANCIA", "RESGATE/OUTROS", "INDETERMINADO",
         "AEREA", "AQUATICA", "VIR"]
cnt = pub.modalidade.value_counts().reindex(ordem).fillna(0)
fig, ax = plt.subplots(figsize=(6.4, 3.2))
cores = [C_USB, C_USA] + [C_OUT] * 6
ax.barh(range(len(cnt))[::-1], cnt.values, color=cores)
ax.set_yticks(range(len(cnt))[::-1]); ax.set_yticklabels(cnt.index)
for i, v in enumerate(cnt.values):
    ax.text(v + 40, len(cnt) - 1 - i, f"{int(v):,}".replace(",", "."),
            va="center", fontsize=8)
ax.set_xlim(0, cnt.max() * 1.18); ax.set_xlabel("unidades ativas")
ax.set_title("Composição da frota pública móvel de urgência (CNES tipo 42)",
             fontsize=10, fontweight="bold")
fig.tight_layout(); fig.savefig(FIG / "01_composicao.png"); plt.close(fig)

# ------------------------------------------------- 2 curva de cobertura x limiar
lims = np.arange(0, 121, 2.5)
fig, ax = plt.subplots(figsize=(6.4, 3.6))
for mod, cor in [("USB", C_USB), ("USA", C_USA)]:
    y = [m.loc[m[f"t_{mod}"] <= L, "populacao"].sum() / P * 100 for L in lims]
    ax.plot(lims, y, color=cor, lw=2, label=mod)
    R[f"cob20_{mod}"] = float(m.loc[m[f"t_{mod}"] <= 20, "populacao"].sum() / P * 100)
ax.axvline(20, color="#555", ls="--", lw=1)
ax.text(21, 8, "limiar de 20 min", fontsize=8, color="#555")
ax.fill_between(lims,
                [m.loc[m.t_USA <= L, "populacao"].sum() / P * 100 for L in lims],
                [m.loc[m.t_USB <= L, "populacao"].sum() / P * 100 for L in lims],
                color=C_USA, alpha=.10)
ax.set_xlabel("tempo estimado até a unidade mais próxima (min)")
ax.set_ylabel("% da população")
ax.set_title("A lacuna entre suporte básico e suporte avançado",
             fontsize=10, fontweight="bold")
ax.legend(); ax.set_ylim(0, 100)
fig.tight_layout(); fig.savefig(FIG / "02_curva_cobertura.png"); plt.close(fig)

# ------------------------------------------------------------- 3 taxas por UF
pop_uf = m.groupby("uf_sigla").populacao.sum()
u = (pub.pivot_table(index="uf_sigla", columns="modalidade",
                     values="codigo_cnes", aggfunc="count").fillna(0))
tx = pd.DataFrame({"USB": u.USB / pop_uf * 1e5, "USA": u.USA / pop_uf * 1e5}).dropna()
tx = tx.sort_values("USA")
fig, ax = plt.subplots(figsize=(6.4, 6.2))
y = np.arange(len(tx))
ax.hlines(y, tx.USA, tx.USB, color="#D6D9DC", lw=2, zorder=1)
ax.scatter(tx.USB, y, color=C_USB, s=28, zorder=2, label="USB")
ax.scatter(tx.USA, y, color=C_USA, s=28, zorder=2, label="USA")
ax.set_yticks(y); ax.set_yticklabels(tx.index)
ax.set_xlabel("unidades por 100 mil habitantes")
ax.set_title("Frota por 100 mil habitantes, por UF", fontsize=10, fontweight="bold")
ax.legend(loc="lower right")
fig.tight_layout(); fig.savefig(FIG / "03_taxas_uf.png"); plt.close(fig)

# ----------------------------------------------- 4 presenca por faixa de tamanho
faixas = [0, 5e3, 1e4, 2e4, 5e4, 1e5, 2e5, 5e5, 1e10]
rot = ["<5k", "5–10k", "10–20k", "20–50k", "50–100k", "100–200k", "200–500k", "≥500k"]
m["faixa"] = pd.cut(m.populacao, faixas, labels=rot, right=False)
g = m.groupby("faixa", observed=True).agg(usb=("tem_usb", "mean"),
                                          usa=("tem_usa", "mean"))
fig, ax = plt.subplots(figsize=(6.4, 3.4))
x = np.arange(len(g)); w = .38
ax.bar(x - w/2, g.usb * 100, w, color=C_USB, label="tem ao menos 1 USB")
ax.bar(x + w/2, g.usa * 100, w, color=C_USA, label="tem ao menos 1 USA")
ax.set_xticks(x); ax.set_xticklabels(g.index)
ax.set_ylabel("% dos municípios da faixa"); ax.set_ylim(0, 105)
ax.set_xlabel("população do município")
ax.set_title("Quem tem ambulância na própria cidade", fontsize=10, fontweight="bold")
ax.legend()
fig.tight_layout(); fig.savefig(FIG / "04_presenca_faixa.png"); plt.close(fig)

# ------------------------------------------------------------------ 5 Lorenz
def lorenz(x, w):
    o = np.argsort(x / np.where(w == 0, np.nan, w))
    x, w = np.asarray(x)[o], np.asarray(w)[o]
    return np.r_[0, np.cumsum(w) / w.sum()], np.r_[0, np.cumsum(x) / x.sum()]

fig, ax = plt.subplots(figsize=(4.6, 4.4))
ax.plot([0, 1], [0, 1], color="#999", ls="--", lw=1, label="proporcional")
for mod, cor in [("USB", C_USB), ("USA", C_USA)]:
    cw, cx = lorenz(m[mod].values, m.populacao.values)
    ax.plot(cw, cx, color=cor, lw=2, label=mod)
ax.set_xlabel("proporção acumulada da população")
ax.set_ylabel("proporção acumulada das unidades")
ax.set_title("Curva de Lorenz da frota", fontsize=10, fontweight="bold")
ax.legend(loc="upper left")
fig.tight_layout(); fig.savefig(FIG / "05_lorenz.png"); plt.close(fig)

# --------------------------------------------------------------------- 6 mapa
fig, axes = plt.subplots(1, 2, figsize=(9.6, 5.0), sharex=True, sharey=True)
for ax, (mod, cor) in zip(axes, [("USB", C_USB), ("USA", C_USA)]):
    ax.scatter(m.lon_sede, m.lat_sede, s=1.2, color="#E3E6E8", zorder=1)
    s = pub[pub.modalidade == mod]
    ax.scatter(s.lon, s.lat, s=5, color=cor, alpha=.65, zorder=2)
    ax.set_title(f"{mod} — {len(s)} unidades", fontsize=10, fontweight="bold")
    ax.set_aspect(1.0); ax.grid(alpha=.15); ax.set_xlabel("longitude")
axes[0].set_ylabel("latitude")
fig.suptitle("Onde estão as bases (cinza = sedes municipais)", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "06_mapa.png"); plt.close(fig)

# ------------------------------------------------------------------ 7 log-log
c = m[m.total > 0]
fig, ax = plt.subplots(figsize=(5.4, 4.2))
ax.scatter(c.populacao, c.total, s=6, color=C_USB, alpha=.35, edgecolor="none")
b, a0 = np.polyfit(np.log(c.populacao), np.log(c.total), 1)
xs = np.logspace(np.log10(c.populacao.min()), np.log10(c.populacao.max()), 50)
ax.plot(xs, np.exp(a0) * xs ** b, color=C_USA, lw=2,
        label=f"ajuste: elasticidade {b:.2f}")
ax.plot(xs, np.exp(a0) * xs.min() ** b * (xs / xs.min()), color="#555", ls="--",
        lw=1.2, label="proporcional (elasticidade 1)")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("população do município"); ax.set_ylabel("unidades móveis")
ax.set_title("A frota cresce muito menos que a população",
             fontsize=10, fontweight="bold")
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(FIG / "07_elasticidade.png"); plt.close(fig)

R["elasticidade_total"] = float(b)
json.dump(R, open("resultados_fig.json", "w"), indent=2)
print("figuras em", FIG.resolve())
print(json.dumps(R, indent=2))
