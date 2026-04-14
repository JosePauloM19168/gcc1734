# Perguntas de discussão — `busca_adversarial_mcts.py`

Este laboratório acompanha uma implementação enxuta de **Monte Carlo Tree
Search (MCTS)** no **jogo da velha**. O foco é identificar, no código, os
elementos centrais da aula 05: motivação do MCTS, contadores `N/W`, quatro
passos do algoritmo, UCB1 e política de simulação.

Como o tempo de laboratório é curto, respondam de forma objetiva, sempre
referenciando funções e atributos do código.

---

## Bloco 1 — Representação do jogo e da árvore

**1.** Na classe `TicTacToe`, onde aparecem os equivalentes de:

- estado do jogo
- ações legais
- transição
- teste terminal
- utilidade final

- #R:
- Estado
- board: configuração do tabuleiro
  current: jogador da vez

**2.** Na classe `MCTSNode`, qual é o papel de cada atributo abaixo?

- `children`
- `visits`
- `wins`
- `untried_moves`
- `player_just_moved`

**3.** Por que o nó guarda contadores agregados (`visits` e `wins`) em vez de
guardar o histórico completo de todas as simulações?

---

## Bloco 2 — Os quatro passos do MCTS

**4.** Localize em `mcts_decision()` os quatro passos do MCTS:

- `Select`
- `Expand`
- `Simulate`
- `Back-propagate`

Explique em uma frase o objetivo de cada passo.

**5.** No passo de seleção, por que o algoritmo só desce automaticamente quando
`node.untried_moves` está vazio?

**6.** O passo de simulação executa jogadas aleatórias até o fim da partida.
Por que essas jogadas não viram nós permanentes da árvore?

---

## Bloco 3 — UCB1 e escolha de ações

**7.** A função `ucb1()` combina dois termos. O que representa:

- a parte `wins / visits`
- a parte com `sqrt(log(parent.visits) / visits)`

**8.** Por que `ucb1()` retorna `inf` quando `visits == 0`? O que isso força o
algoritmo a fazer?

**9.** No final de `mcts_decision()`, a ação retornada é o filho da raiz com
maior `visits`, e não necessariamente o maior `Q = wins / visits`. Qual é a
intuição dessa escolha?

---

## Bloco 4 — Experimentos curtos

**10.** Execute alguns testes com:

```bash
python3 labs/busca_adversarial_mcts.py --show-stats --iterations 50
python3 labs/busca_adversarial_mcts.py --show-stats --iterations 500
python3 labs/busca_adversarial_mcts.py --mode-x human --mode-o ai --iterations 300
```

Compare o efeito de aumentar o número de iterações sobre a estabilidade da
decisão e sobre os contadores da raiz.

---

## Comandos úteis

```bash
python3 labs/busca_adversarial_mcts.py
python3 labs/busca_adversarial_mcts.py --show-stats
python3 labs/busca_adversarial_mcts.py --iterations 50 --seed 0
python3 labs/busca_adversarial_mcts.py --iterations 500 --seed 0
python3 labs/busca_adversarial_mcts.py --mode-x human --mode-o ai --iterations 300
```
