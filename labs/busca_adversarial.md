# Perguntas de discussão — `busca_adversarial.py`

As perguntas estão organizadas em blocos temáticos, em ordem crescente de
abstração. Cada grupo deve elaborar respostas justificadas, referenciando
partes do código sempre que possível.

O arquivo acompanha uma implementação jogável de um **Pacman simplificado**,
com alternância de turnos entre Pacman (MAX) e fantasma (MIN), além de suporte
para **Minimax**, **poda alfa-beta**, **H-Minimax** e uma versão com **busca
quiescente**.

---

## Bloco 1 — Representação do jogo

**1.** Quais elementos do problema adversarial aparecem explicitamente na
classe `PacmanAdversarialProblem`? Identifique no código os equivalentes de:

- estado (`State`)
- ações (`ACTIONS`)
- transição (`RESULT`)
- jogador da vez (`PLAYER`)
- teste terminal (`TERMINAL-TEST`)
- utilidade (`UTILITY`)



    ACTIONS = {
        "U": (-1, 0),
        "D": (1, 0),
        "L": (0, -1),
        "R": (0, 1),
        "S": (0, 0),   # ficar parado, útil para inspeção didática
    }

  self.s0 = GameState(
            pacman=self.pacman0,
            ghost=self.ghost0,
            foods=self.foods0,
            turn="MAX",
            score=0,
            ply=0,
        )
 def result(self, state: GameState, action: str) -> GameState:
        """
        Aplica action ao state e retorna o novo GameState resultante.

        A função é pura: não modifica state; sempre cria um novo objeto.

        Semântica por turno
        -------------------
        - Turno MAX (Pacman): move Pacman para a nova célula; se houver
          comida nela, remove do conjunto e incrementa o score em 10.
          O turno passa para "MIN" e ply é incrementado.
        - Turno MIN (Fantasma): move o fantasma para a nova célula.
          O turno passa para "MAX" e ply é incrementado.

        Parâmetros
        ----------
        state : GameState
            Estado atual.
        action : str
            Uma das chaves de ACTIONS ("U", "D", "L", "R", "S").

        Retorna
        -------
        GameState
            Estado resultante da aplicação da ação.
        """
        dr, dc = self.ACTIONS[action]
        if state.turn == "MAX":        ----- aqui ele vê quem é o jogador da vez
            new_pac = (state.pacman[0] + dr, state.pacman[1] + dc)
            foods = set(state.foods)
            score = state.score
            if new_pac in foods:
                foods.remove(new_pac)
                score += 10
            return GameState(
                pacman=new_pac,
                ghost=state.ghost,
                foods=frozenset(foods),
                turn="MIN",
                score=score,
                ply=state.ply + 1,
            )
        else:
            new_ghost = (state.ghost[0] + dr, state.ghost[1] + dc)
            return GameState(
                pacman=state.pacman,
                ghost=new_ghost,
                foods=state.foods,
                turn="MAX",
                score=state.score,
                ply=state.ply + 1,
            )

   def terminal_test(self, state: GameState) -> bool:
        """
        Retorna True se state é um nó terminal da árvore de busca.

        Um estado é terminal quando:
        - há colisão (Pacman perdeu),
        - Pacman coletou toda a comida (Pacman ganhou), ou
        - o limite de jogadas foi atingido (empate).
        """
        return self.collision(state) or self.win(state) or self.draw(state)

    def utility(self, state: GameState) -> float:
        """
        Retorna o valor de utilidade de um estado terminal, na perspectiva de MAX.

        Valores:
        - Colisão (derrota de MAX): -1000.0
        - Vitória de MAX: +1000.0 + pontuação acumulada (incentiva coletar
          comida rapidamente, não apenas "não perder")
        - Empate / estado não terminal: delega para eval() como fallback seguro.

        Nota: utility() só deve ser chamada em estados terminais; para estados
        intermediários, use eval().
        """
        if self.collision(state):
            return -1000.0
        if self.win(state):
            return 1000.0 + state.score
        return self.eval(state)



**2.** A classe `GameState` armazena `pacman`, `ghost`, `foods`, `turn`,
`score` e `ply`. Qual é o papel de cada um desses atributos? Por que guardar
`turn` explicitamente simplifica o código?
pacman - posição atual do jogador max na grid
ghost - posição atual do jogador min na grid
foods -  foods=state.foods - células que ainda contêm comida. (o frozen garante a imutabilidade da comida ao passar o jogador min)
turn - Indica de quem é a vez: "MAX" para Pacman, "MIN" para o fantasma.
score - Pontuação acumulada.
ply - Número de jogadas já realizadas desde o estado inicial. Corresponde ao turno de um jogador 

---

## Bloco 2 — Regras do jogo e topologia do mapa

**3.** O método `legal_actions()` consulta a posição do jogador ativo. Por que
isso é suficiente para definir as ações legais neste domínio?
Porque ele verifica a posição do jogador, as ações possíveis, se possui paredes e se o movimento está dentro do limite do grid.

def legal_actions(self, state: GameState) -> List[str]:
        """
        Retorna a lista de ações legais para o jogador que tem a vez em state.

        O jogador ativo é Pacman se state.turn == "MAX", fantasma se "MIN".
        A ação "S" (parar) é excluída das ações legais para forçar movimento
        contínuo — isso evita que agentes fujam de decisões difíceis ficando parados.
        """
        actions: List[str] = []
        pos = state.pacman if state.turn == "MAX" else state.ghost
        for a, (dr, dc) in self.ACTIONS.items():
            nxt = (pos[0] + dr, pos[1] + dc)
            if self.in_bounds(nxt) and self.passable(nxt):
                actions.append(a)
        return actions

**4.** A função `neighbors()` é usada em vários pontos do código. Onde ela é
usada apenas para movimentação imediata e onde ela é usada para raciocínio mais
estrutural sobre o mapa?
Ela é usada na shortest_path_distance para calcular a distância real em numeros de passos 
        if src == dst:
            return 0
        q = deque([(src, 0)])
        seen = {src}
        while q:
            cur, d = q.popleft()
            for nxt in self.neighbors(cur, include_stop=False):
                if nxt == dst:
                    return d + 1
                if nxt not in seen:
                    seen.add(nxt)
                    q.append((nxt, d + 1))
        return None

Enquanto que na def mobility ela retornar o numero de direções livres a partir da posição atual.
   def mobility(self, pos: Pos) -> int:
        """
        Retorna o número de direções livres a partir de pos (grau de liberdade local).

        Valores típicos:
        - 1 → beco sem saída (dead end)
        - 2 → corredor
        - 3 ou 4 → cruzamento / espaço aberto
        """
        return len(self.neighbors(pos, include_stop=False))
E na def neighbors ela lista as posições vizinhas alcançáveis a partir da posição em um passo.

---

## Bloco 3 — Terminal, utilidade e avaliação

**5.** O método `terminal_test()` considera três condições: colisão, vitória e
limite de plies. Explique o papel de cada uma delas.

colisão-Derrota que ocorre ao colidir com os fantasmas
vitória-Coleta todas as pilulas sem colidir com os fantasmas
limite de plis- limite de jogadas atingidas

**6.** Quais componentes contribuem para `eval()`? Explique a intuição de cada
um deles:

- score acumulado
- distância à comida mais próxima
- distância ao fantasma
- mobilidade
- penalidade por beco/corredor sob pressão
score - Pontuação já acumulada.
food_bonus - Incentiva Pacman a se aproximar de comidas.
mobility_bonus - Recompensa posições abertas (mais opções de movimento).
danger_penalty - Penaliza estar perto do fantasma; cresce rapidamente quando a distância diminui.
remaining_food_penalty - Incentiva Pacman a reduzir o número de comidas pendentes.
trap_penalty - Penalidade adicional quando Pacman está em posição desfavorável com o fantasma próximo.
        
  if self.collision(state):
            return -1000.0
        if self.win(state):
            return 1000.0 + state.score

        score = float(state.score)

        # Comida mais próxima
        if state.foods:
            food_dist = min(self.shortest_path_distance(state.pacman, f) or 999 for f in state.foods)
        else:
            food_dist = 0

        ghost_dist = self.shortest_path_distance(state.pacman, state.ghost)
        if ghost_dist is None:
            ghost_dist = 999

        mobility_bonus = 2.0 * self.mobility(state.pacman)
        food_bonus = 12.0 / (food_dist + 1)
        danger_penalty = 18.0 / (ghost_dist + 1)
        remaining_food_penalty = 4.0 * len(state.foods)

        trap_penalty = 0.0
        if self.dead_end(state.pacman) and ghost_dist <= 2:
            trap_penalty += 40.0
        elif self.corridor_like(state.pacman) and ghost_dist <= 2:
            trap_penalty += 18.0

        return score + food_bonus + mobility_bonus - danger_penalty - remaining_food_penalty - trap_penalty
---

## Bloco 4 — Minimax

**7.** Explique o papel das funções internas de `minimax_decision()`:

- `value` - Verifica de quem é o turno e chama a função referente a max e a min.
- `max_value` - Inicia com o pior valor de max e decide o melhor valor para max
- `min_value` Inicia com o pior valor para min e decide e melhor valor para min

def value(s: GameState) -> float:
        counter.nodes += 1
        if problem.terminal_test(s):
            return problem.utility(s)
        if s.turn == "MAX":
            return max_value(s)
        return min_value(s)

    def max_value(s: GameState) -> float:
        v = -math.inf
        for a in problem.legal_actions(s):
            v = max(v, value(problem.result(s, a)))
        return v

    def min_value(s: GameState) -> float:
        v = math.inf
        for a in problem.legal_actions(s):
            v = min(v, value(problem.result(s, a)))
        return v
        
Como elas implementam diretamente a definição recursiva do Minimax?



**8.** A função `minimax_decision()` retorna uma `SearchResult` com três
campos. O que significa cada um deles?

best_action- melhor ação possivel
best_value- melhor valor
counter.nodes - melhor quantidade de tentativas exploradas


---

## Bloco 5 — Poda alfa-beta

**9.** Em `alphabeta_decision()`, o que representam `alpha` e `beta`? Explique
sem usar fórmulas, apenas em termos de “melhor valor já garantido”.

**10.** Onde exatamente ocorre a poda em `max_value()` e `min_value()`? Explique
por que a decisão de interromper a expansão é segura.

---

## Bloco 6 — H-Minimax e profundidade limitada

**11.** O que muda quando passamos de `minimax` para `hminimax`?

**12.** O método `value()` em `alphabeta_decision()` usa `eval()` quando o
limite de profundidade é atingido. Por que isso é necessário?


---

## Bloco 7 — Busca quiescente

**13.** O método `non_quiescent()` tenta detectar estados taticamente instáveis.
Quais sinais locais ele usa?

**14.** Por que `non_quiescent()` não tenta provar formalmente que existe uma
sequência forçada de derrota?

---

## Bloco 8 — Interação e modos de execução

**15.** O comando abaixo roda Pacman humano contra fantasma controlado por IA:

```bash
python3 busca_adversarial.py --pacman-mode human --ghost-mode ai --algorithm quiescent
```

Explique passo a passo o que ocorrerá em cada turno.

---

## Comandos úteis

```bash
python3 busca_adversarial.py
python3 busca_adversarial.py --grid beco --algorithm hminimax --depth 3
python3 busca_adversarial.py --grid beco --algorithm quiescent --depth 2
python3 busca_adversarial.py --pacman-mode human --ghost-mode ai --algorithm quiescent
python3 busca_adversarial.py --pacman-mode ai --ghost-mode random --algorithm hminimax
```
