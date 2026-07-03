---
name: analise-termos-google-ads
description: "Analisa relatórios de Google Ads (termos de pesquisa e palavras-chave, CSV exportado da conta) classificando cada termo por intenção de busca e gerando listas de palavras negativas prontas para aplicar, além de planilha Excel com diagnóstico completo. Use este skill sempre que o usuário enviar um CSV do Google Ads, mencionar 'termos de pesquisa', 'palavras-chave', 'palavras negativas', 'negativar', 'search terms', quiser entender queda de resultado em campanha de pesquisa, auditar desperdício de verba, ou pedir análise de desempenho de anúncios do Google — mesmo que não use a palavra 'relatório'."
---

# Análise de termos de pesquisa do Google Ads por intenção

Este skill transforma um export bruto do Google Ads em: diagnóstico de desperdício, classificação de cada termo por intenção de busca, listas de negativas seguras para colar na conta, e uma planilha Excel organizada. O produto final é sempre acionável — o usuário deve conseguir aplicar as negativas em minutos.

## Passo 0 — Entender o negócio antes de classificar

A classificação de intenção depende inteiramente do contexto do negócio. O mesmo termo pode ser ouro para um cliente e lixo para outro. Antes de classificar, descubra (perguntando ao usuário ou pelo histórico da conversa):

1. **O que a empresa vende exatamente** (produto/serviço e o que ela NÃO vende — ex.: vende coroas de flores, mas não vende buquês).
2. **Nome da marca** e variações — buscas pela marca nunca podem ser negativadas.
3. **Área de atuação** (cidade/região) — termos com a cidade costumam ser transacionais.
4. **Concorrentes conhecidos** e empresas adjacentes que aparecem nas buscas (no nicho funerário: funerárias; no nicho de advocacia: outros escritórios; etc.).
5. **Qual é a conversão configurada na conta** (clique no WhatsApp? formulário? ligação?). Isso muda a leitura: clique em botão é conversão fraca — curioso também clica.

Se o usuário já deu esse contexto na conversa, não pergunte de novo.

## Passo 1 — Ler o CSV do Google Ads corretamente

Exports do Google Ads em português têm armadilhas conhecidas. Use o script `scripts/parse_gads_csv.py` para fazer o parsing (ele resolve tudo isso), ou trate manualmente:

- As **2 primeiras linhas** são título e período — o cabeçalho real é a linha 3.
- Números em formato BR: vírgula decimal, ponto de milhar, `%` embutido (`"14,55%"`).
- Valores vazios aparecem como ` --`.
- Linhas de **Total** no fim devem ser excluídas das somas (senão duplica tudo).
- O **mesmo termo pode aparecer em várias linhas** (grupos de anúncios/correspondências diferentes) — agregue por termo antes de analisar.
- Guarde o período do relatório (linha 2) e cite-o na análise.

```bash
python scripts/parse_gads_csv.py "relatorio.csv"   # imprime JSON agregado por termo
```

## Passo 2 — Classificar cada termo por intenção de busca

Use esta taxonomia (conceito clássico de search intent, adaptado para negativação):

| Categoria | O que é | Ação |
|---|---|---|
| **Transacional** | Quer comprar agora o que a empresa vende ("comprar X", "X + cidade", "X entrega") | MANTER |
| **Comercial — preço** | Pesquisa preço/valor ("quanto custa", "valor de") | MANTER — está perto de comprar |
| **Navegacional — marca própria** | Busca pela marca do cliente | MANTER (nunca negativar) |
| **Navegacional — concorrente** | Busca por empresa específica que não é o cliente | NEGATIVAR |
| **Informacional** | Quer aprender, não comprar ("como fazer", "significado", "o que escrever", "modelos", "frases") | NEGATIVAR |
| **Genérico — produto adjacente** | Produto parecido que a empresa não vende | AVALIAR com o usuário |
| **Fora de escopo** | Idioma errado, região errada, "atacado", "curso", "artificial" etc. | NEGATIVAR |

Regras práticas de classificação:
- Termo que contém o produto principal + cidade/compra/entrega → transacional, mesmo com erro de digitação.
- Nomes próprios desconhecidos (ex.: "floricultura sueli", "funerária X") → pesquise ou pergunte: provavelmente concorrente ou empresa adjacente.
- Termos ambíguos com conversões registradas: olhe o custo/conversão antes de condenar. Conversão fraca (clique em botão) com custo alto ainda pode merecer negativação.

## Passo 3 — Gerar negativas com regras de segurança

Este é o passo onde mais se erra. Uma negativa mal pensada bloqueia clientes. Antes de sugerir cada negativa, simule mentalmente: "que buscas BOAS essa negativa bloquearia?"

Primeiro, as regras oficiais de correspondência negativa (support.google.com/google-ads/answer/12437241), que são diferentes das positivas:
- **Frase negativa** bloqueia qualquer busca que CONTENHA a sequência, mesmo com palavras a mais. `"funerária"` bloqueia "coroa de flores funerária ethernus" — um comprador pedindo entrega.
- **Exata negativa** bloqueia só a busca idêntica, sem palavras extras. `[funerária ethernus]` barra o navegacional puro e libera "coroa de flores funerária ethernus".
- **Ampla negativa** só bloqueia se TODOS os termos estiverem na busca (qualquer ordem).
- **Negativa não cobre variações**: plural, acento e derivação são termos diferentes ("funerária" ≠ "funeraria" ≠ "funerárias"). Cada variação precisa ser adicionada.

Regras de segurança obrigatórias:
1. **Nunca negativar palavra contida no nome da marca** do cliente (ex.: se a marca é "La Fleur Floricultura", não negativar "floricultura" sozinha).
2. **Nomes de locais de entrega/atuação e empresas adjacentes onde o cliente presta serviço → sempre EXATA, nunca frase/ampla.** Se o cliente entrega coroas em funerárias e cemitérios, quem busca "coroa de flores funerária X" é comprador; a frase `"funerária X"` (e até `"funerária"` sozinha) o bloquearia. Negative as buscas navegacionais completas que apareceram no relatório: `[funerária X]`, `[funerária perto de mim]`, `[funerária]`. O custo dessa escolha: exata não cobre variações novas, então o relatório de termos precisa de revisão recorrente para alimentar a lista — diga isso ao usuário.
3. **Pares em ampla para intenção navegacional**: combinações que nunca aparecem numa compra ("funerária telefone", "funerária endereço", "funerária perto") bloqueiam famílias de busca ruins sem afetar "produto + local".
4. **Concorrentes diretos (mesmo produto) podem ficar em frase** — ninguém busca "produto + nome do concorrente" querendo comprar do cliente. A distinção-chave: concorrente direto = frase; empresa adjacente/local de entrega = exata.
5. **Não negativar termos de preço** — quem pergunta preço compra.
6. **Vocabulário que nunca aparece numa compra** (informacional: "significado", "frases", "curso"; produto errado: "artificial", "atacado"; idioma errado) pode ir em frase/ampla de 1 palavra sem medo.
7. Cobrir **variações com e sem acento e plural** de toda negativa mantida.
8. Organizar a saída em colunas por tipo de correspondência e categoria, indicando a sintaxe de cada uma (aspas = frase, colchetes = exata).

Ao analisar o relatório de termos, observe também a coluna **Tipo de correspondência**:
- Termos marcados como **"AI Max"** vieram da expansão por IA do Google (que ignora as palavras-chave da campanha). O Google pode ativar a IA Max sozinho via "experimentos automáticos" ou recomendações autoaplicadas — sem registro no histórico de alterações. Se os termos AI Max forem ruins, recomende desativar a IA Max nas configurações da campanha, encerrar experimentos ativos e desligar as recomendações autoaplicadas.
- Muitos termos de **correspondência ampla** com CTR baixo indicam palavra ampla vazando — candidata a virar frase/exata.

## Passo 4 — Análise temporal (se houver segmentação)

Se o relatório tiver coluna de semana/dia, ou se o usuário relatar queda de resultado:
- Monte a série por período: custo, impressões, cliques, CTR, CPC, conversões, CPA, parcela de impressões.
- Procure o ponto de inflexão: queda de CTR com salto de impressões = entrou tráfego ruim (geralmente correspondência ampla expandindo); queda de impressões = pausa/orçamento/leilão.
- Se as conversões no painel estão OK mas o usuário diz que os leads reais caíram, a suspeita nº 1 é conversão fraca (clique em botão) sendo inflada por tráfego sem intenção — recomende migrar o rastreamento para um evento mais profundo (conversa iniciada, formulário enviado, conversão offline).
- Se o relatório não tem segmentação, avise o usuário que a visão agregada esconde a evolução e ensine a exportar segmentado (Segmentar > Semana antes de baixar).
- **Sempre peça também o Histórico de alterações** (Ferramentas > Histórico de alterações > exportar CSV, cobrindo o período da queda). É frequentemente a prova definitiva: cruze a data de cada alteração (palavras adicionadas/pausadas, mudanças de lance/CPA desejado, orçamento) com o ponto de inflexão das métricas. Atenção especial a: palavras amplas adicionadas pouco antes da queda, saltos grandes de CPA desejado/orçamento (mudanças de lance saudáveis são graduais, 10-15% por vez), e alterações feitas por outros usuários da conta — o dono nem sempre sabe o que outro acesso mudou. Lembre que recursos ativados automaticamente pelo Google (IA Max, recomendações autoaplicadas) NÃO aparecem no histórico.

## Passo 5 — Campanhas paralelas (pergunte sempre)

Pergunte se existem outras campanhas para o mesmo produto (é comum: "uma para topo", "uma de cliques", "uma de teste"). Se sim, peça o relatório de campanhas com as colunas Estratégia de lances, Orçamento, parcela de impressões e % de impressões em 1ª posição, mais o relatório de palavras-chave de todas com a coluna Campanha. Então verifique:
- **Sobreposição de palavras**: o Google exibe só um anúncio por conta em cada leilão — campanhas com as mesmas palavras não somam presença, apenas disputam internamente, e vence a de maior lance (a conta paga mais caro pelo mesmo clique). Compare o CPC entre elas: se a campanha "agressiva" tem CPC muito maior e % de 1ª posição igual ou menor, ela só está leiloando contra a própria conta.
- **Justificativa comum "é para garantir o topo"**: mostre os dados de % de impressões em 1ª posição de cada uma. Se a estratégia cara não entrega mais topo, recomende consolidar na de melhor CPA e, se topo for crítico, subir o CPA desejado gradualmente ou usar "Parcela de impressões desejada" como último recurso.
- **Produtos distintos na mesma conta** (ex.: coroas e buquês): confirme a cross-negativação — cada campanha deve negativar o vocabulário da outra para não disputarem leilão nem exibirem anúncio errado ao público errado.

## Passo 6 — Landing page (se o usuário quiser ir além da mídia)

Ofereça analisar a página de destino contra os termos que mais convertem. Se o site for renderizado via JavaScript (Lovable, React etc.), o fetch simples retorna vazio — use o navegador. Avalie a primeira dobra pelo olhar de quem busca o termo campeão:
- O H1 casa com a palavra que mais converte?
- A promessa mais forte do negócio (prazo de entrega, disponibilidade 24h) está visível sem rolar, ou enterrada?
- Há âncora de preço ("a partir de R$ X")? Preço visível qualifica o clique — importante quando a conversão é rasa (clique em botão).
- O CTA é ação de compra ("Pedir X") ou de dúvida ("Fale conosco")?
- Prova de confiança (anos de mercado, avaliações) aparece na primeira dobra?
- Mobile-first: esse tráfego é majoritariamente celular; o bloco todo precisa caber na primeira tela.
Ao propor mudanças, sempre alerte: se a conversão é rastreada por clique em botão (GTM), qualquer alteração estrutural na página pode quebrar a tag — instrua o usuário a testar a conversão após publicar.

## Passo 7 — Entregar a planilha

Gere um Excel (use o skill xlsx se disponível; fonte Arial, cabeçalhos com fundo escuro, cores por ação: verde=manter, vermelho=negativar, amarelo=avaliar) com 5 abas:

1. **Resumo** — categorias × (nº termos, cliques, custo, conversões, custo/conv com fórmula, % do custo com fórmula). Linha de total com SUM. Inclua uma linha explicando o conceito de intenção de busca.
2. **Termos classificados** — todos os termos com categoria, ação e métricas; com auto-filtro e painel congelado.
3. **Negativas para colar** — colunas por tipo, com cada termo JÁ FORMATADO na sintaxe do Google Ads: `"termo"` com aspas quando frase, `[termo]` com colchetes quando exata, sem nada quando ampla. O usuário deve poder selecionar a coluna, copiar e colar direto no campo de negativas sem editar nada.
4. **Palavras-chave sugeridas** — estrutura de grupos de anúncios construída a partir dos termos que CONVERTERAM (não inventadas do zero). Método: agrupe os termos convertidos por tema (núcleo do serviço, fornecedor/contratação, serviço+segmento de cliente, serviço+localidade, comercial/preço); cada grupo vira uma coluna com título citando o dado que o justifica (ex.: "base: 14 conv, CPA R$ 2-32"). Palavras já na sintaxe pronta (frase com aspas, exata com colchetes), com variações com/sem acento como entradas separadas. Grupos validados pelos dados entram com prioridade; grupos de expansão (segmentos que a LP menciona mas ainda têm pouco volume) entram com nota de "orçamento pequeno + anúncio específico do segmento". Nunca sugerir correspondência ampla. Incluir nota de que os genéricos rasos negativados em exata não conflitam com as frases sugeridas.
5. **Recomendações** — numeradas por impacto, cada uma explicando o porquê. Sempre incluir: os cuidados de segurança aplicados (o que NÃO negativar e por quê), a recomendação de revisar termos semanalmente, e — se a conversão da conta for clique em botão — a recomendação de melhorar o rastreamento.

Use fórmulas do Excel para os cálculos derivados (custo/conv, % do custo, totais), não valores fixos. Recalcule e verifique zero erros de fórmula antes de entregar.

No chat, entregue junto um resumo curto: o número-chave do desperdício (R$ e % do custo em termos sem intenção) e as 2-3 ações de maior impacto. Não repita o conteúdo da planilha.
