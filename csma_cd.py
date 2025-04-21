#!/usr/bin/env python3

import random, math, argparse, numpy as np
import matplotlib.pyplot as plt

# ---------------- Parâmetros ---------------- #
R = 1e5                   # taxa de transmissão (bps)
L = 100                  # tamanho do quadro (bits)
t_quadro = L / R         # tempo de transmissão do quadro
sim_time = 100           # tempo total da simulação (s)
dt_sim = t_quadro / L    # intervalo de simulação

# ---------------- Função de Simulação ---------------- #
def simulate(taxa_geracao, n_est=10, atraso_a=0.02, rodadas=100):
    t_sim = int(sim_time / dt_sim)
    espera_max = int(10 * L)
    atraso = int(atraso_a * L / R / dt_sim)

    entregues = colididos = bloqueios = gerados = 0

    for _ in range(rodadas):
        tx_ativo = [0] * n_est
        tx_fila = [0] * n_est
        tx_cnt = [0] * n_est
        colin = [0] * n_est
        tx_espera = [0] * n_est
        transmis = [[0] * t_sim for _ in range(n_est)]
        tx_ativo_atr = [0] * n_est

        for k in range(t_sim):
            if k >= atraso:
                tx_ativo_atr = [transmis[i][k - atraso] for i in range(n_est)]

            for j in range(n_est):
                if tx_ativo[j] == 1:
                    transmis[j][k] = 1

                if tx_cnt[j] > 0:
                    if colin[j] == 1:
                        tx_cnt[j] = 0
                        tx_ativo[j] = 0
                        tx_espera[j] = random.randint(1, espera_max)
                        tx_fila[j] += 1
                        colin[j] = 0
                        colididos += 1
                    else:
                        tx_cnt[j] -= 1
                        if tx_cnt[j] == 0:
                            tx_ativo[j] = 0
                            entregues += 1
                else:
                    if tx_fila[j] > 0:
                        if tx_espera[j] == 0 and sum(tx_ativo_atr) == 0:
                            tx_ativo[j] = 1
                            tx_cnt[j] = int(L / R / dt_sim)
                            tx_fila[j] -= 1
                        elif tx_espera[j] > 0:
                            tx_espera[j] -= 1
                        elif sum(tx_ativo_atr) > 0:
                            tx_espera[j] = 2 * atraso
                            bloqueios += 1

                if random.random() < taxa_geracao * dt_sim:
                    gerados += 1
                    if tx_ativo[j] == 0 and tx_espera[j] == 0 and sum(tx_ativo_atr) == 0:
                        tx_ativo[j] = 1
                        tx_cnt[j] = int(L / R / dt_sim)
                    else:
                        tx_fila[j] += 1
                        if tx_espera[j] == 0 and sum(tx_ativo_atr) > 0:
                            tx_espera[j] = 2 * atraso
                            bloqueios += 1

            if sum(tx_ativo) > 1:
                for j in range(n_est):
                    if tx_ativo[j]:
                        colin[j] = 1

    return gerados / rodadas, entregues / rodadas, colididos / rodadas, bloqueios / rodadas

# ---------------- Execução Principal ---------------- #
from tqdm import tqdm

def main():
    parser = argparse.ArgumentParser(description="Simulador CSMA/CD com barra de progresso")
    parser.add_argument("--sim_time", type=float, default=1, help="Tempo total da simulação (s)")
    parser.add_argument("--rodadas", type=int, default=10, help="Número de rodadas por ponto")
    args = parser.parse_args()

    global sim_time
    sim_time = args.sim_time

    n_est = 10
    rodadas = args.rodadas
    pontos = 20
    taxa_max = int(R / L / n_est)
    taxas_quadro = [taxa_max * (i + 1) / pontos for i in range(pontos)]

    g_list = []
    s_list = []
    tg_bps = []
    td_bps = []

    for taxa in tqdm(taxas_quadro, desc="Simulando", unit="ponto"):
        gerados, entregues, colididos, bloqueios = simulate(taxa, n_est=n_est, rodadas=rodadas)
        g = gerados * L / sim_time / R
        s = entregues * L / sim_time / R
        g_list.append(g)
        s_list.append(s)
        tg_bps.append(gerados * L / sim_time)
        td_bps.append(entregues * L / sim_time)

    # Gráfico Eficiência vs G
    plt.figure()
    plt.plot(g_list, s_list, 'ro-', label="Simulação (eficiência)")
    max_idx = np.argmax(s_list)
    plt.plot(g_list[max_idx], s_list[max_idx], 'ko', label="Pico simulação")
    G_teo = np.linspace(0, 1, 100)
    for a_teo in [0.01, 0.02, 0.05, 0.1]:
        U_teo = 1 / (1 + 2 * a_teo * math.e)
        S_teo_multi = U_teo * G_teo
        plt.plot(G_teo, S_teo_multi, linestyle='--', label=f"Teórico a={a_teo:.2f}")
    a = 0.02
    U = 1 / (1 + 2 * a * math.e)
    S_teo = U * G_teo
    plt.plot(G_teo, S_teo, 'k--', label="Teórico (1-persistente)")
    plt.grid()
    plt.xlabel("Carga oferecida G")
    plt.ylabel("Eficiência S")
    plt.legend()
    plt.title("CSMA/CD — Eficiência vs G")
    plt.tight_layout()
    plt.savefig("efficiency_vs_G.png", dpi=150)

    # Gráfico Capacidade (bps)
    plt.figure()
    plt.plot(tg_bps, td_bps, 'bo-', label="Simulação")
    max_idx_th = np.argmax(td_bps)
    plt.plot(tg_bps[max_idx_th], td_bps[max_idx_th], 'ko', label="Pico simulação")
    plt.plot(G_teo * R, S_teo * R, 'k--', label="Teórico")
    plt.grid()
    plt.xlabel("Taxa de geração de quadros (bps)")
    plt.ylabel("Taxa de entrega (bps")
    plt.legend()
    plt.title("CSMA/CD — Throughput vs Taxa de Geração")
    plt.tight_layout()
    plt.savefig("throughput_vs_generation.png", dpi=150)

    print("\nFiguras salvas: efficiency_vs_G.png, throughput_vs_generation.png")

if __name__ == "__main__":
    main()
