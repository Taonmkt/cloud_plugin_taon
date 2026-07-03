#!/usr/bin/env python3
"""Parse de CSVs exportados do Google Ads (formato pt-BR).

Resolve: 2 linhas de título antes do cabeçalho, vírgula decimal, '%',
valores ' --', linhas de Total, e agrega linhas duplicadas do mesmo termo.

Uso:
    python parse_gads_csv.py "relatorio.csv" [--col-termo NOME]

Saída: JSON em stdout:
    {"periodo": "...", "colunas": [...], "termos": [{"termo": ..., "cliques": ..., ...}]}
Detecta automaticamente a coluna-chave (Termo de pesquisa ou Palavra-chave)
e colunas de segmentação temporal (Semana/Dia/Mês), agregando por (período, termo).
"""
import csv, json, sys, argparse
from collections import defaultdict

NUM_COLS = {'Cliques': 'cliques', 'Impr.': 'impressoes', 'Custo': 'custo',
            'Conversões': 'conversoes', 'Todas as conv.': 'todas_conv'}
KEY_CANDIDATES = ['Termo de pesquisa', 'Palavra-chave']
TIME_CANDIDATES = ['Semana', 'Dia', 'Mês', 'Data']


def num(s):
    s = str(s).strip().replace('%', '').replace('"', '')
    if s in ('--', '', ' --'):
        return 0.0
    try:
        return float(s.replace('.', '').replace(',', '.'))
    except ValueError:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('arquivo')
    ap.add_argument('--col-termo', default=None)
    args = ap.parse_args()

    with open(args.arquivo, encoding='utf-8-sig') as f:
        lines = f.read().splitlines()
    titulo, periodo = lines[0], lines[1] if len(lines) > 1 else ''
    rows = list(csv.reader(lines[2:]))
    hdr = rows[0]
    key = args.col_termo or next((k for k in KEY_CANDIDATES if k in hdr), None)
    if not key:
        sys.exit(f"Coluna-chave não encontrada. Colunas: {hdr}")
    tcol = next((c for c in TIME_CANDIDATES if c in hdr), None)

    agg = defaultdict(lambda: defaultdict(float))
    extra = {}
    for r in rows[1:]:
        if len(r) != len(hdr):
            continue
        d = dict(zip(hdr, r))
        termo = d.get(key, '').strip()
        if not termo or termo.lower().startswith('total'):
            continue
        gk = (d.get(tcol, '').strip(), termo) if tcol else ('', termo)
        for src, dst in NUM_COLS.items():
            if src in d:
                agg[gk][dst] += num(d[src])
        extra.setdefault(gk, {c: d[c] for c in
                          ('Tipo de corresp.', 'Adicionada/excluída', 'Campanha',
                           'Grupo de anúncios', 'Status da palavra-chave') if c in d})

    termos = []
    for (per, termo), m in sorted(agg.items(), key=lambda kv: -kv[1].get('custo', 0)):
        if m.get('cliques'):
            m['cpc_medio'] = m.get('custo', 0) / m['cliques']
        item = {'termo': termo, **{k: round(v, 2) for k, v in m.items()}, **extra.get((per, termo), {})}
        if tcol:
            item['periodo_seg'] = per
        termos.append(item)
    print(json.dumps({'titulo': titulo, 'periodo': periodo,
                      'coluna_chave': key, 'segmentacao': tcol,
                      'n_termos': len(termos), 'termos': termos},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
