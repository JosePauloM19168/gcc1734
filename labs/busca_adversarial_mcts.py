from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

Move = Tuple[int, int]


# ============================================================================
# Estado do jogo
# ============================================================================

class TicTacToe:
    """
    Jogo da velha 3×3 com interface mínima para integração com o MCTS.

    O tabuleiro é representado como uma lista de listas de strings,
    onde cada célula pode conter ``'X'``, ``'O'`` ou ``' '`` (vazio).
    A classe é intencionalmente enxuta: fornece apenas as operações
    primitivas necessárias para o laço de busca do MCTS — cópia de estado,
    enumeração de jogadas legais, aplicação de jogada, verificação de
    vencedor e detecção de fim de jogo.

    Atributos
    ---------
    board : List[List[str]]
        Tabuleiro 3×3; ``board[r][c]`` é a célula na linha r, coluna c.
        Células vazias contêm ``' '``; ocupadas contêm ``'X'`` ou ``'O'``.
    current : str
        Identificador do jogador que tem a vez: ``'X'`` ou ``'O'``.
        X sempre começa; os jogadores alternam a cada jogada.
    """

    def __init__(self) -> None:
        self.board = [[" "] * 3 for _ in range(3)]
        self.current = "X"

    def copy(self) -> "TicTacToe":
        """
        Retorna uma cópia profunda do estado atual do jogo.

        Garante que modificações no clone não afetam o objeto original —
        propriedade essencial para o MCTS, que precisa explorar múltiplos
        futuros hipotéticos a partir do mesmo estado.

        Retorna
        -------
        TicTacToe
            Nova instância com tabuleiro e jogador ativo idênticos ao original.
        """
        new = TicTacToe()
        new.board = [row.copy() for row in self.board]
        new.current = self.current
        return new

    def available_moves(self) -> List[Move]:
        """
        Retorna a lista de jogadas legais no estado atual.

        Uma jogada é legal se a célula correspondente ainda estiver vazia.
        A ordem retornada segue a varredura linha-por-linha, da esquerda
        para a direita — não implica nenhuma ordem de preferência.

        Retorna
        -------
        List[Move]
            Lista de tuplas ``(linha, coluna)`` com as células disponíveis.
        """
        return [
            (r, c)
            for r in range(3)
            for c in range(3)
            if self.board[r][c] == " "
        ]

    def make_move(self, move: Move) -> bool:
        """
        Aplica ``move`` ao estado atual, modificando-o in-place.

        Se a célula já estiver ocupada, a jogada é rejeitada e o estado
        permanece inalterado. Caso contrário, a célula recebe a marca do
        jogador ativo e a vez passa para o adversário.

        Parâmetros
        ----------
        move : Move
            Tupla ``(linha, coluna)`` indicando a célula-alvo.

        Retorna
        -------
        bool
            ``True`` se a jogada foi aplicada com sucesso; ``False`` se
            a célula já estava ocupada.
        """
        r, c = move
        if self.board[r][c] != " ":
            return False
        self.board[r][c] = self.current
        self.current = "O" if self.current == "X" else "X"
        return True

    def winner(self) -> Optional[str]:
        """
        Verifica se há um vencedor no estado atual.

        Examina todas as oito linhas vencedoras possíveis: três linhas
        horizontais, três colunas verticais e as duas diagonais.

        Retorna
        -------
        Optional[str]
            ``'X'`` ou ``'O'`` se houver vencedor; ``None`` caso contrário.
        """
        lines: List[List[str]] = []
        lines.extend(self.board)                                              # linhas horizontais
        lines.extend([[self.board[r][c] for r in range(3)] for c in range(3)])  # colunas
        lines.append([self.board[i][i] for i in range(3)])                   # diagonal principal
        lines.append([self.board[i][2 - i] for i in range(3)])               # diagonal secundária
        for line in lines:
            if line[0] != " " and all(cell == line[0] for cell in line):
                return line[0]
        return None

    def full(self) -> bool:
        """
        Retorna ``True`` se todas as células do tabuleiro estão ocupadas.

        Um tabuleiro cheio sem vencedor corresponde a um empate.
        """
        return all(cell != " " for row in self.board for cell in row)

    def game_over(self) -> bool:
        """
        Retorna ``True`` se o jogo chegou ao fim.

        O jogo termina quando há um vencedor ou quando o tabuleiro
        está completamente preenchido (empate).
        """
        return self.winner() is not None or self.full()

    def render(self) -> str:
        """
        Converte o tabuleiro em uma representação textual para exibição no terminal.

        Exemplo de saída para um tabuleiro parcialmente preenchido::

             X |   | O
            ---+---+---
               | X |
            ---+---+---
             O |   | X

        Retorna
        -------
        str
            String com as linhas do tabuleiro separadas por ``'\\n'``.
        """
        rows = []
        for i, row in enumerate(self.board):
            rows.append(" " + " | ".join(row) + " ")
            if i < 2:
                rows.append("---+---+---")
        return "\n".join(rows)


# ============================================================================
# Árvore MCTS
# ============================================================================

@dataclass
class MCTSNode:
    """
    Nó persistente da árvore de busca Monte Carlo (MCTS).

    Cada nó armazena um estado do jogo, estatísticas acumuladas ao longo
    das iterações e referências estruturais (pai, filhos, jogadas ainda
    não exploradas). A árvore cresce incrementalmente: a cada iteração,
    um novo nó filho é inserido (fase de expansão) e as estatísticas são
    atualizadas de volta até a raiz (fase de retropropagação).

    Atributos
    ---------
    game : TicTacToe
        Estado do jogo associado a este nó.
    parent : Optional[MCTSNode]
        Nó pai; ``None`` para a raiz da árvore.
    move : Optional[Move]
        Jogada que levou do pai até este nó; ``None`` na raiz.
    player_just_moved : Optional[str]
        Identificador (``'X'`` ou ``'O'``) do jogador que realizou ``move``
        para chegar a este nó. Usado na retropropagação para creditar a
        vitória ao jogador correto.
    children : List[MCTSNode]
        Filhos já expandidos deste nó.
    visits : int
        Número total de vezes que este nó foi visitado (N na fórmula UCB1).
    wins : float
        Soma dos resultados dos playouts que passaram por este nó,
        **do ponto de vista de** ``player_just_moved``:

        - ``1.0`` → esse jogador venceu o playout;
        - ``0.5`` → empate;
        - ``0.0`` → esse jogador perdeu.
    untried_moves : List[Move]
        Jogadas legais do estado ``game`` que ainda não foram expandidas.
        Quando esta lista esvazia, o nó está *totalmente expandido* e a
        seleção desce para os filhos usando UCB1.
    """

    game: TicTacToe
    parent: Optional["MCTSNode"] = None
    move: Optional[Move] = None
    player_just_moved: Optional[str] = None
    children: List["MCTSNode"] = field(default_factory=list)
    visits: int = 0
    wins: float = 0.0
    untried_moves: List[Move] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.untried_moves:
            self.untried_moves = self.game.available_moves()

    def q(self) -> float:
        """
        Retorna a taxa de vitória estimada deste nó (Q na literatura MCTS).

        Calculada como ``wins / visits``; retorna ``0.0`` se o nó ainda
        não foi visitado, evitando divisão por zero.

        Retorna
        -------
        float
            Valor entre 0.0 e 1.0 representando a qualidade média dos playouts.
        """
        return 0.0 if self.visits == 0 else self.wins / self.visits

    def ucb1(self, exploration: float = math.sqrt(2.0)) -> float:
        """
        Calcula o valor UCB1 (Upper Confidence Bound 1) deste nó.

        A fórmula equilibra exploração de ramos pouco visitados com a
        explotação de ramos historicamente fortes::

            UCB1 = W/N + C × √(ln(N_pai) / N)

        onde ``W`` é a soma de vitórias, ``N`` o número de visitas deste nó,
        ``N_pai`` o número de visitas do pai e ``C`` a constante de exploração.

        Nós nunca visitados recebem ``+∞`` para garantir que sejam
        expandidos antes de qualquer nó já visitado.

        Parâmetros
        ----------
        exploration : float
            Constante de exploração ``C`` da fórmula UCB1. O valor teórico
            padrão é ``√2``; valores maiores favorecem exploração, menores
            favorecem explotação.

        Retorna
        -------
        float
            Valor UCB1; ``float('inf')`` se o nó nunca foi visitado.
        """
        if self.visits == 0:
            return float("inf")
        assert self.parent is not None and self.parent.visits > 0
        exploit = self.wins / self.visits
        explore = exploration * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploit + explore

    def best_ucb_child(self, exploration: float) -> "MCTSNode":
        """
        Retorna o filho com o maior valor UCB1.

        Usado na fase de **seleção** do MCTS: desce na árvore pelo caminho
        com melhor trade-off entre exploração e explotação.

        Parâmetros
        ----------
        exploration : float
            Constante de exploração repassada para cada cálculo de UCB1.

        Retorna
        -------
        MCTSNode
            Filho com UCB1 máximo.
        """
        return max(self.children, key=lambda child: child.ucb1(exploration))

    def expand(self, rng: random.Random) -> "MCTSNode":
        """
        Escolhe uma jogada ainda não tentada, cria o nó filho correspondente
        e o adiciona à árvore.

        Implementa a fase de **expansão** do MCTS: retira aleatoriamente
        uma jogada de ``untried_moves``, aplica-a a uma cópia do jogo e
        instancia um novo ``MCTSNode`` filho.

        Parâmetros
        ----------
        rng : random.Random
            Gerador pseudoaleatório; permite reprodutibilidade ao fixar a semente.

        Retorna
        -------
        MCTSNode
            O nó filho recém-criado e adicionado a ``self.children``.
        """
        move = rng.choice(self.untried_moves)
        self.untried_moves.remove(move)
        new_game = self.game.copy()
        player = new_game.current
        new_game.make_move(move)
        child = MCTSNode(
            game=new_game,
            parent=self,
            move=move,
            player_just_moved=player,
        )
        self.children.append(child)
        return child

    def update(self, winner: Optional[str]) -> None:
        """
        Atualiza as estatísticas deste nó com o resultado de um playout.

        Implementa a fase de **retropropagação** do MCTS: incrementa o
        contador de visitas e acumula o resultado do playout, convertido
        para a perspectiva de ``player_just_moved``.

        Convenção de pontuação
        ----------------------
        - ``1.0`` se ``winner == player_just_moved`` (vitória);
        - ``0.5`` em caso de empate (``winner is None``);
        - ``0.0`` se o adversário venceu (nenhuma soma ao contador de vitórias).

        Parâmetros
        ----------
        winner : Optional[str]
            ``'X'`` ou ``'O'`` indicando o vencedor do playout; ``None``
            em caso de empate.
        """
        self.visits += 1
        if winner is None:
            self.wins += 0.5
        elif winner == self.player_just_moved:
            self.wins += 1.0


# ============================================================================
# Busca MCTS
# ============================================================================

def mcts_decision(
    game: TicTacToe,
    iterations: int = 200,
    exploration: float = math.sqrt(2.0),
    seed: int = 0,
) -> Tuple[Move, MCTSNode]:
    """
    Executa o algoritmo MCTS a partir de ``game`` e retorna a melhor jogada.

    O MCTS itera ``iterations`` vezes o ciclo de quatro fases:

    1. **Seleção** — desce na árvore usando UCB1 enquanto o nó corrente
       já estiver totalmente expandido e o jogo não tiver terminado.
    2. **Expansão** — se ainda houver jogadas não tentadas no nó corrente,
       cria um novo filho para uma delas (escolhida aleatoriamente).
    3. **Simulação** (*rollout*) — completa a partida fora da árvore com
       jogadas aleatórias até atingir um estado terminal.
    4. **Retropropagação** — percorre o caminho de volta à raiz, atualizando
       ``visits`` e ``wins`` em cada nó pelo resultado do rollout.

    Após todas as iterações, a jogada escolhida é a do filho da raiz com
    o maior número de visitas — critério mais robusto que o maior Q porque
    é menos sensível a outliers estatísticos.

    Parâmetros
    ----------
    game : TicTacToe
        Estado do jogo a partir do qual a busca é realizada.
        O objeto original não é modificado.
    iterations : int
        Número de rollouts executados. Mais iterações aumentam a qualidade
        da decisão à custa de tempo de CPU.
    exploration : float
        Constante de exploração ``C`` da UCB1. Valor padrão: ``√2``.
    seed : int
        Semente para o gerador pseudoaleatório interno, garantindo que
        execuções com a mesma semente produzam o mesmo resultado.

    Retorna
    -------
    Tuple[Move, MCTSNode]
        - A jogada escolhida (filho com mais visitas na raiz).
        - A raiz da árvore MCTS, para inspeção dos contadores após a busca.

    Lança
    -----
    ValueError
        Se não houver nenhuma jogada legal disponível na raiz.
    """
    rng = random.Random(seed)
    root = MCTSNode(game.copy(), player_just_moved=None)

    for _ in range(iterations):
        node = root
        rollout_game = game.copy()

        # 1. Seleção: desce pela árvore enquanto o nó já estiver totalmente expandido.
        while not node.untried_moves and node.children and not rollout_game.game_over():
            node = node.best_ucb_child(exploration)
            assert node.move is not None
            rollout_game.make_move(node.move)

        # 2. Expansão: adiciona um novo filho se ainda houver ações não tentadas.
        if node.untried_moves and not rollout_game.game_over():
            node = node.expand(rng)
            rollout_game = node.game.copy()

        # 3. Simulação: completa a partida fora da árvore com playout aleatório.
        while not rollout_game.game_over():
            rollout_game.make_move(rng.choice(rollout_game.available_moves()))

        # 4. Retropropagação: atualiza N e W ao longo do caminho até a raiz.
        winner = rollout_game.winner()
        while node is not None:
            node.update(winner)
            node = node.parent

    if not root.children:
        raise ValueError("Nenhuma jogada legal disponível a partir da raiz.")

    # Critério de seleção final: filho mais visitado (mais robusto que maior Q).
    best_child = max(root.children, key=lambda child: child.visits)
    assert best_child.move is not None
    return best_child.move, root


# ============================================================================
# Utilitários de exibição
# ============================================================================

def print_root_stats(root: MCTSNode, exploration: float) -> None:
    """
    Exibe no terminal as estatísticas dos filhos diretos da raiz.

    Para cada filho, imprime:

    - ``move``   : a jogada que leva à raiz até esse filho;
    - ``N``      : número de visitas acumuladas;
    - ``W``      : soma de vitórias acumuladas;
    - ``Q``      : taxa de vitória estimada (``W / N``);
    - ``UCB1``   : valor UCB1 calculado com a constante ``exploration``.

    Os filhos são ordenados em ordem decrescente de visitas e,
    em caso de empate, pela própria jogada.

    Parâmetros
    ----------
    root : MCTSNode
        Raiz da árvore MCTS após a execução de ``mcts_decision``.
    exploration : float
        Constante de exploração usada no cálculo do UCB1 exibido.
    """
    print("Estatísticas dos filhos da raiz:")
    for child in sorted(root.children, key=lambda c: (-c.visits, c.move)):
        print(
            f"  move={child.move}  N={child.visits:3d}  "
            f"W={child.wins:6.1f}  Q={child.q():.3f}  UCB1={child.ucb1(exploration):.3f}"
        )


# ============================================================================
# Entrada do jogador humano
# ============================================================================

def parse_human_move(game: TicTacToe) -> Move:
    """
    Solicita e valida a jogada do jogador humano via entrada no terminal.

    Exibe as jogadas legais disponíveis e repete a solicitação até receber
    uma coordenada válida no formato ``linha,coluna`` (por exemplo: ``1,2``).

    Parâmetros
    ----------
    game : TicTacToe
        Estado atual do jogo (para determinar as jogadas legais).

    Retorna
    -------
    Move
        Tupla ``(linha, coluna)`` com a jogada escolhida pelo usuário,
        garantidamente legal no estado atual.
    """
    legal = set(game.available_moves())
    print("Jogadas legais:", sorted(legal))
    while True:
        raw = input("Sua jogada [linha,coluna]: ").strip()
        try:
            r_str, c_str = raw.split(",")
            move = (int(r_str), int(c_str))
        except ValueError:
            print("Formato inválido. Use, por exemplo: 1,2")
            continue
        if move in legal:
            return move
        print("Jogada ilegal.")


# ============================================================================
# Loop principal do jogo
# ============================================================================

def choose_move(
    game: TicTacToe,
    mode_x: str,
    mode_o: str,
    iterations: int,
    exploration: float,
    seed: int,
    show_stats: bool,
) -> Move:
    """
    Obtém a próxima jogada para o jogador ativo, respeitando o modo configurado.

    Despacha para ``parse_human_move`` (modo ``"human"``) ou para
    ``mcts_decision`` (modo ``"ai"``), dependendo do controlador atribuído
    ao jogador atual (``game.current``).

    Parâmetros
    ----------
    game : TicTacToe
        Estado atual do jogo.
    mode_x : str
        Modo de controle do jogador X: ``"human"`` ou ``"ai"``.
    mode_o : str
        Modo de controle do jogador O: ``"human"`` ou ``"ai"``.
    iterations : int
        Número de iterações do MCTS (ignorado no modo ``"human"``).
    exploration : float
        Constante de exploração UCB1 (ignorada no modo ``"human"``).
    seed : int
        Semente para o MCTS (ignorada no modo ``"human"``).
    show_stats : bool
        Se ``True``, exibe as estatísticas dos filhos da raiz após a
        decisão do MCTS.

    Retorna
    -------
    Move
        Jogada escolhida pelo controlador ativo.
    """
    mode = mode_x if game.current == "X" else mode_o
    if mode == "human":
        return parse_human_move(game)
    move, root = mcts_decision(
        game,
        iterations=iterations,
        exploration=exploration,
        seed=seed,
    )
    print(f"MCTS escolheu {move} para {game.current}")
    if show_stats:
        print_root_stats(root, exploration)
    return move


def run_game(
    mode_x: str,
    mode_o: str,
    iterations: int,
    exploration: float,
    seed: int,
    show_stats: bool,
) -> None:
    """
    Executa o loop principal de uma partida completa de jogo da velha.

    A cada turno:

    1. Exibe o tabuleiro atual no terminal.
    2. Verifica se o jogo terminou; se sim, anuncia o resultado e encerra.
    3. Obtém a jogada do jogador ativo (humano ou IA).
    4. Aplica a jogada e avança para o próximo turno.

    A semente do MCTS é incrementada a cada turno (``seed + turn``) para
    que decisões em turnos diferentes usem sequências pseudoaleatórias
    distintas, evitando correlações entre os playouts de turnos sucessivos
    e mantendo a reprodutibilidade global da partida.

    Parâmetros
    ----------
    mode_x : str
        Controlador do jogador X: ``"human"`` ou ``"ai"``.
    mode_o : str
        Controlador do jogador O: ``"human"`` ou ``"ai"``.
    iterations : int
        Número de iterações do MCTS por jogada.
    exploration : float
        Constante de exploração ``C`` da UCB1.
    seed : int
        Semente base para o gerador pseudoaleatório do MCTS.
    show_stats : bool
        Se ``True``, exibe N, W, Q e UCB1 dos filhos da raiz após cada
        decisão do MCTS.
    """
    game = TicTacToe()
    turn = 0

    while not game.game_over():
        print()
        print(game.render())
        print(f"Vez de {game.current}")
        move = choose_move(
            game,
            mode_x=mode_x,
            mode_o=mode_o,
            iterations=iterations,
            exploration=exploration,
            seed=seed + turn,
            show_stats=show_stats,
        )
        game.make_move(move)
        turn += 1

    print()
    print(game.render())
    winner = game.winner()
    if winner is None:
        print("Resultado: empate")
    else:
        print(f"Resultado: vitória de {winner}")


# ============================================================================
# CLI
# ============================================================================

def build_argparser() -> argparse.ArgumentParser:
    """
    Define e constrói o parser de argumentos de linha de comando.

    Parâmetros configuráveis
    ------------------------
    --mode-x : str
        Controlador do jogador X (``"human"`` ou ``"ai"``; padrão: ``"ai"``).
    --mode-o : str
        Controlador do jogador O (``"human"`` ou ``"ai"``; padrão: ``"ai"``).
    --iterations : int
        Número de iterações MCTS por jogada (padrão: 200).
        Valores maiores produzem decisões melhores a custo de mais CPU.
    --exploration : float
        Constante ``C`` da fórmula UCB1 (padrão: ``√2 ≈ 1.414``).
        Aumente para explorar mais ramos; diminua para focar nos melhores.
    --seed : int
        Semente pseudoaleatória para reproduzir os playouts (padrão: 0).
        Partidas com a mesma semente e os mesmos parâmetros são idênticas.
    --show-stats : flag
        Se presente, exibe N, W, Q e UCB1 dos filhos da raiz após cada
        jogada da IA — útil para inspecionar o comportamento do MCTS.

    Retorna
    -------
    argparse.ArgumentParser
        Parser configurado, pronto para chamada a ``parse_args()``.
    """
    parser = argparse.ArgumentParser(
        description="Laboratório de busca adversarial com MCTS no jogo da velha."
    )
    parser.add_argument(
        "--mode-x",
        choices=["human", "ai"],
        default="ai",
        help="Controlador do jogador X.",
    )
    parser.add_argument(
        "--mode-o",
        choices=["human", "ai"],
        default="ai",
        help="Controlador do jogador O.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=200,
        help="Número de iterações do MCTS por jogada.",
    )
    parser.add_argument(
        "--exploration",
        type=float,
        default=math.sqrt(2.0),
        help="Constante C da UCB1.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Semente pseudoaleatória para reproduzir os playouts.",
    )
    parser.add_argument(
        "--show-stats",
        action="store_true",
        help="Exibe N, W, Q e UCB1 dos filhos da raiz em cada jogada.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    """
    Ponto de entrada do script. Lê os argumentos da linha de comando e
    inicia uma partida de jogo da velha com as configurações fornecidas.

    ─────────────────────────────────────────────────────────────────────────
    EXEMPLOS DE USO
    ─────────────────────────────────────────────────────────────────────────

    1. Execução padrão — IA vs IA com 200 iterações:

        python3 tictactoe_mcts.py

        Ambos os jogadores são controlados pelo MCTS com os parâmetros
        padrão. A partida roda sem pausas e exibe apenas o tabuleiro
        final e o resultado.

    ─────────────────────────────────────────────────────────────────────────

    2. Você controla X; IA controla O:

        python3 tictactoe_mcts.py --mode-x human --mode-o ai

        Insira suas jogadas no formato ``linha,coluna`` (ex.: ``1,1``
        para o centro). O MCTS responde com a melhor jogada encontrada
        em 200 iterações. Bom para sentir na prática o nível de jogo
        do agente.

    ─────────────────────────────────────────────────────────────────────────

    3. IA vs IA com mais iterações e estatísticas detalhadas:

        python3 tictactoe_mcts.py --iterations 1000 --show-stats

        Aumentar as iterações melhora a qualidade das decisões (o jogo
        da velha tem solução ótima conhecida: empate com jogo perfeito).
        A flag ``--show-stats`` exibe, para cada jogada, o valor N, W, Q
        e UCB1 de todos os filhos da raiz — útil para entender como o
        MCTS distribui visitas entre as opções.

    ─────────────────────────────────────────────────────────────────────────

    4. Exploração elevada para forçar diversidade de playouts:

        python3 tictactoe_mcts.py --exploration 2.5 --iterations 500 --show-stats

        Com ``C = 2.5`` (acima do padrão ``√2``), o MCTS privilegia ramos
        menos visitados, explorando mais amplamente a árvore. Compare os
        contadores N com a configuração padrão para ver como a constante
        afeta a distribuição de visitas.

    ─────────────────────────────────────────────────────────────────────────

    5. Reprodução de uma partida específica:

        python3 tictactoe_mcts.py --seed 42 --iterations 300

        Fixar a semente garante que a mesma sequência de jogadas seja
        reproduzida em qualquer máquina. Use para comparar variações de
        parâmetros de forma isolada, sem interferência de aleatoriedade.

    ─────────────────────────────────────────────────────────────────────────

    Parâmetros
    ----------
    argv : Optional[Sequence[str]]
        Lista de argumentos a processar; se ``None``, lê ``sys.argv[1:]``.
    """
    args = build_argparser().parse_args(argv)
    run_game(
        mode_x=args.mode_x,
        mode_o=args.mode_o,
        iterations=args.iterations,
        exploration=args.exploration,
        seed=args.seed,
        show_stats=args.show_stats,
    )


if __name__ == "__main__":
    main()