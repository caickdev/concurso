"""Popula o banco com dados de demonstração: taxonomia (estados, bancas,
matérias, um concurso de exemplo por banca) e um conjunto de questões —
todas de autoria original deste projeto, escritas para demonstrar o formato
de cada banca (CEBRASPE Certo/Errado; FGV, FCC e VUNESP A-E/A-D).
Nenhum conteúdo foi extraído de prova real.

Não substitui o scraper (services/scraper_service.py) — é só para o site
sair do ar com conteúdo navegável antes de uma fonte real ser configurada.

Uso:
    cd meu-app-concursos
    .venv\\Scripts\\python.exe -m scripts.seed_demo_data
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import select

from backend.crud.crud_question import crud_question
from backend.database import dispose_engine, get_db_context
from backend.models.question import DifficultyLevel
from backend.models.taxonomy import Board, Exam, State, Subject
from backend.services.scraper_service import compute_content_hash

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("seed_demo_data")

# --- Questões de demonstração (autoria original) ---------------------------

_QUESTIONS: list[dict[str, Any]] = [
    # --- CEBRASPE (Certo/Errado) — Direito Constitucional ---
    {
        "board": "cebraspe", "subject": "direito-constitucional",
        "difficulty": DifficultyLevel.MEDIUM,
        "content": (
            "À luz da Constituição Federal de 1988, julgue o item a seguir: o direito "
            "à vida, previsto no caput do art. 5º da CF/88, é considerado um direito "
            "absoluto, não comportando qualquer relativização pelo ordenamento "
            "jurídico brasileiro."
        ),
        "options": {"C": "Certo", "E": "Errado"},
        "correct_option": "E",
    },
    {
        "board": "cebraspe", "subject": "direito-constitucional",
        "difficulty": DifficultyLevel.EASY,
        "content": (
            "Consoante a organização político-administrativa da República Federativa "
            "do Brasil, julgue o item: os municípios são entes federativos dotados de "
            "autonomia, competindo-lhes legislar sobre assuntos de interesse local."
        ),
        "options": {"C": "Certo", "E": "Errado"},
        "correct_option": "C",
    },
    {
        "board": "cebraspe", "subject": "direito-constitucional",
        "difficulty": DifficultyLevel.HARD,
        "content": (
            "Acerca do processo legislativo, julgue o item: a iniciativa de lei sobre "
            "matéria tributária é privativa do presidente da República, sendo vedada "
            "a apresentação de projetos de lei sobre esse tema por parlamentares."
        ),
        "options": {"C": "Certo", "E": "Errado"},
        "correct_option": "E",
    },
    {
        "board": "cebraspe", "subject": "direito-constitucional",
        "difficulty": DifficultyLevel.MEDIUM,
        "content": (
            "Julgue o item, referente aos remédios constitucionais: o mandado de "
            "segurança é o instrumento processual adequado para proteger direito "
            "líquido e certo violado por ato de autoridade pública, desde que não "
            "amparado por habeas corpus ou habeas data."
        ),
        "options": {"C": "Certo", "E": "Errado"},
        "correct_option": "C",
    },
    # --- FGV (A-E) — Direito Administrativo ---
    {
        "board": "fgv", "subject": "direito-administrativo",
        "difficulty": DifficultyLevel.MEDIUM,
        "content": "Segundo a doutrina majoritária, são atributos do ato administrativo, EXCETO:",
        "options": {
            "A": "Presunção de legitimidade",
            "B": "Autoexecutoriedade",
            "C": "Imperatividade",
            "D": "Tipicidade",
            "E": "Onerosidade",
        },
        "correct_option": "E",
    },
    {
        "board": "fgv", "subject": "direito-administrativo",
        "difficulty": DifficultyLevel.EASY,
        "content": (
            "Sobre os princípios da Administração Pública previstos no art. 37, caput, "
            "da Constituição Federal, assinale a alternativa que apresenta corretamente "
            "os princípios expressos:"
        ),
        "options": {
            "A": "Legalidade, impessoalidade, moralidade, publicidade e eficiência",
            "B": "Legalidade, moralidade, finalidade, publicidade e razoabilidade",
            "C": "Impessoalidade, proporcionalidade, moralidade, publicidade e eficiência",
            "D": "Legalidade, impessoalidade, economicidade, publicidade e eficiência",
            "E": "Moralidade, legalidade, finalidade, motivação e eficiência",
        },
        "correct_option": "A",
    },
    {
        "board": "fgv", "subject": "direito-administrativo",
        "difficulty": DifficultyLevel.HARD,
        "content": (
            "A respeito das modalidades de licitação previstas na Lei nº 14.133/2021 "
            "(Nova Lei de Licitações), assinale a alternativa correta:"
        ),
        "options": {
            "A": "Tomada de preços e convite são modalidades vigentes da nova lei",
            "B": "Pregão e concorrência são modalidades previstas na nova lei",
            "C": "A nova lei extinguiu a modalidade concorrência",
            "D": "O convite passou a ser obrigatório para todas as contratações públicas",
            "E": "A tomada de preços substituiu o pregão na nova lei",
        },
        "correct_option": "B",
    },
    # --- FGV (A-E) — Português ---
    {
        "board": "fgv", "subject": "portugues",
        "difficulty": DifficultyLevel.MEDIUM,
        "content": (
            "Assinale a alternativa em que a concordância verbal está de acordo com a "
            "norma-padrão da língua portuguesa:"
        ),
        "options": {
            "A": "Fazem dois anos que ele não comparece às audiências",
            "B": "Aluga-se apartamentos no centro da cidade",
            "C": "Houveram muitos problemas na organização do evento",
            "D": "Mais de um candidato apresentou recurso administrativo",
            "E": "A maioria dos servidores votaram a favor da proposta",
        },
        "correct_option": "D",
    },
    {
        "board": "fgv", "subject": "portugues",
        "difficulty": DifficultyLevel.MEDIUM,
        "content": (
            "Assinale a alternativa em que a regência verbal está correta, conforme a "
            "norma-padrão:"
        ),
        "options": {
            "A": "Ele assistiu o filme atentamente",
            "B": "Prefiro café do que chá",
            "C": "O réu obedeceu ao mandado judicial",
            "D": "Ela namora com o colega de trabalho há dois anos",
            "E": "Chegamos no tribunal antes do horário marcado",
        },
        "correct_option": "C",
    },
    {
        "board": "fgv", "subject": "portugues",
        "difficulty": DifficultyLevel.EASY,
        "content": (
            "Leia o trecho a seguir: \"A administração pública, ao longo das últimas "
            "décadas, tem buscado incorporar mecanismos de transparência e "
            "participação social em seus processos decisórios. Iniciativas como "
            "portais de dados abertos, audiências públicas e canais de ouvidoria "
            "refletem esse movimento, ainda que sua efetividade varie conforme a "
            "estrutura institucional de cada órgão.\" Com base no texto, é correto "
            "afirmar que:"
        ),
        "options": {
            "A": "A transparência na administração pública é um fenômeno recente, surgido nas últimas décadas",
            "B": "Todos os órgãos públicos aplicam com igual eficácia os mecanismos de participação social mencionados",
            "C": "A efetividade dos mecanismos de transparência depende da estrutura institucional de cada órgão",
            "D": "Audiências públicas substituíram integralmente os portais de dados abertos",
            "E": "O texto conclui que a participação social é dispensável para a administração pública moderna",
        },
        "correct_option": "C",
    },
    # --- FCC (A-E) — Raciocínio Lógico ---
    {
        "board": "fcc", "subject": "raciocinio-logico",
        "difficulty": DifficultyLevel.MEDIUM,
        "content": (
            "Considere a proposição composta: \"Se chove, então a rua fica molhada.\" "
            "Assinale a alternativa que apresenta a negação lógica correta dessa "
            "proposição:"
        ),
        "options": {
            "A": "Se não chove, então a rua não fica molhada",
            "B": "Chove e a rua não fica molhada",
            "C": "Não chove ou a rua fica molhada",
            "D": "A rua fica molhada e não chove",
            "E": "Se a rua fica molhada, então chove",
        },
        "correct_option": "B",
    },
    {
        "board": "fcc", "subject": "raciocinio-logico",
        "difficulty": DifficultyLevel.HARD,
        "content": (
            "Observe a sequência numérica: 2, 6, 12, 20, 30, ... Assinale a "
            "alternativa que apresenta o próximo termo da sequência:"
        ),
        "options": {"A": "36", "B": "40", "C": "42", "D": "44", "E": "48"},
        "correct_option": "C",
    },
    {
        "board": "fcc", "subject": "raciocinio-logico",
        "difficulty": DifficultyLevel.MEDIUM,
        "content": (
            "Em uma turma de concurseiros, sabe-se que todo aluno que estuda Direito "
            "Constitucional também estuda Português, e sabe-se que João não estuda "
            "Português. É correto concluir que:"
        ),
        "options": {
            "A": "João estuda Direito Constitucional",
            "B": "João não estuda Direito Constitucional",
            "C": "João estuda todas as matérias, exceto Português",
            "D": "Não é possível concluir nada sobre os estudos de João",
            "E": "Todos os alunos da turma estudam Direito Constitucional",
        },
        "correct_option": "B",
    },
    # --- VUNESP (A-D) — Informática ---
    {
        "board": "vunesp", "subject": "informatica", "state_uf": "SP",
        "difficulty": DifficultyLevel.EASY,
        "content": (
            "No Microsoft Excel, a fórmula =SE(A1>10;\"Alto\";\"Baixo\") foi inserida "
            "em uma célula, e a célula A1 contém o valor 15. Assinale a alternativa "
            "que apresenta o resultado exibido:"
        ),
        "options": {"A": "Alto", "B": "Baixo", "C": "#VALOR!", "D": "15"},
        "correct_option": "A",
    },
    {
        "board": "vunesp", "subject": "informatica", "state_uf": "SP",
        "difficulty": DifficultyLevel.MEDIUM,
        "content": (
            "Assinale a alternativa que apresenta corretamente a função de um "
            "firewall em uma rede de computadores:"
        ),
        "options": {
            "A": "Armazenar cópias de segurança dos dados da rede",
            "B": "Controlar o tráfego de rede com base em regras de segurança predefinidas",
            "C": "Aumentar a velocidade de conexão à internet",
            "D": "Traduzir nomes de domínio em endereços IP",
        },
        "correct_option": "B",
    },
    {
        "board": "vunesp", "subject": "informatica", "state_uf": "SP",
        "difficulty": DifficultyLevel.HARD,
        "content": (
            "Em relação aos modelos de computação em nuvem, aquele em que o usuário "
            "contrata apenas a infraestrutura (servidores, armazenamento e rede), "
            "ficando responsável por instalar e gerenciar o sistema operacional e as "
            "aplicações, é denominado:"
        ),
        "options": {
            "A": "SaaS (Software as a Service)",
            "B": "PaaS (Platform as a Service)",
            "C": "IaaS (Infrastructure as a Service)",
            "D": "DaaS (Desktop as a Service)",
        },
        "correct_option": "C",
    },
    # --- VUNESP (A-D) — Administração Pública ---
    {
        "board": "vunesp", "subject": "administracao-publica", "state_uf": "SP",
        "difficulty": DifficultyLevel.MEDIUM,
        "content": (
            "Segundo a classificação clássica da doutrina administrativista, os "
            "órgãos públicos que atuam com autonomia técnica e decisória, mas sem "
            "personalidade jurídica própria distinta do ente a que pertencem, são "
            "denominados:"
        ),
        "options": {
            "A": "Entidades da administração indireta",
            "B": "Órgãos públicos",
            "C": "Empresas públicas",
            "D": "Autarquias",
        },
        "correct_option": "B",
    },
    {
        "board": "vunesp", "subject": "administracao-publica", "state_uf": "SP",
        "difficulty": DifficultyLevel.MEDIUM,
        "content": "Sobre os poderes administrativos, assinale a alternativa correta:",
        "options": {
            "A": "O poder disciplinar permite à Administração aplicar sanções a qualquer cidadão que descumpra normas administrativas",
            "B": "O poder hierárquico decorre da relação de subordinação entre os órgãos e agentes do Poder Executivo",
            "C": "O poder de polícia é exclusivo do Poder Judiciário",
            "D": "O poder regulamentar é exercido exclusivamente pelo Poder Legislativo",
        },
        "correct_option": "B",
    },
    # --- CEBRASPE (Certo/Errado) — Direito Penal ---
    {
        "board": "cebraspe", "subject": "direito-penal",
        "difficulty": DifficultyLevel.HARD,
        "content": (
            "Acerca dos princípios do Direito Penal, julgue o item: o princípio da "
            "legalidade penal veda a criação de crimes e penas por meio de analogia, "
            "ainda que em benefício do réu."
        ),
        "options": {"C": "Certo", "E": "Errado"},
        "correct_option": "E",
    },
    {
        "board": "cebraspe", "subject": "direito-penal",
        "difficulty": DifficultyLevel.MEDIUM,
        "content": (
            "Julgue o item: para a configuração do crime de furto, é indispensável "
            "que a subtração da coisa alheia móvel ocorra mediante violência ou "
            "grave ameaça à pessoa."
        ),
        "options": {"C": "Certo", "E": "Errado"},
        "correct_option": "E",
    },
    # --- CEBRASPE (Certo/Errado) — Matemática Financeira ---
    {
        "board": "cebraspe", "subject": "matematica-financeira",
        "difficulty": DifficultyLevel.EASY,
        "content": (
            "Julgue o item: no regime de juros simples, os juros incidem sempre "
            "sobre o capital inicial, não havendo incidência de juros sobre juros "
            "já acumulados."
        ),
        "options": {"C": "Certo", "E": "Errado"},
        "correct_option": "C",
    },
    {
        "board": "cebraspe", "subject": "matematica-financeira",
        "difficulty": DifficultyLevel.HARD,
        "content": (
            "Julgue o item: em um financiamento pelo Sistema de Amortização "
            "Constante (SAC), o valor das prestações mensais permanece constante ao "
            "longo de todo o período de pagamento."
        ),
        "options": {"C": "Certo", "E": "Errado"},
        "correct_option": "E",
    },
    # --- FGV (A-E) — Administração Pública ---
    {
        "board": "fgv", "subject": "administracao-publica",
        "difficulty": DifficultyLevel.MEDIUM,
        "content": (
            "Segundo o ciclo PDCA (Plan-Do-Check-Act), amplamente utilizado na "
            "gestão de processos organizacionais, a etapa em que se compara o "
            "resultado obtido com a meta planejada é denominada:"
        ),
        "options": {
            "A": "Plan (Planejar)",
            "B": "Do (Executar)",
            "C": "Check (Verificar)",
            "D": "Act (Agir)",
            "E": "Nenhuma das etapas anteriores",
        },
        "correct_option": "C",
    },
    {
        "board": "fgv", "subject": "administracao-publica",
        "difficulty": DifficultyLevel.MEDIUM,
        "content": "Sobre os tipos de planejamento organizacional, assinale a alternativa correta:",
        "options": {
            "A": "O planejamento estratégico é de curto prazo e envolve apenas o nível operacional",
            "B": "O planejamento tático traduz as diretrizes do planejamento estratégico em objetivos específicos por departamento ou área",
            "C": "O planejamento operacional define a missão e a visão da organização",
            "D": "O planejamento estratégico é elaborado exclusivamente pelo nível operacional",
            "E": "Não há relação entre os níveis estratégico, tático e operacional de planejamento",
        },
        "correct_option": "B",
    },
]

_BOARD_NAMES = {"cebraspe": "CEBRASPE", "fgv": "FGV", "fcc": "FCC", "vunesp": "VUNESP"}
_SUBJECT_NAMES = {
    "direito-constitucional": "Direito Constitucional",
    "direito-administrativo": "Direito Administrativo",
    "portugues": "Português",
    "raciocinio-logico": "Raciocínio Lógico",
    "informatica": "Informática",
    "administracao-publica": "Administração Pública",
    "direito-penal": "Direito Penal",
    "matematica-financeira": "Matemática Financeira",
}
_STATE_NAMES = {"BR": "Federal", "SP": "São Paulo"}
_EXAM_YEAR = 2026
_EXAM_ORG = "Órgão de Exemplo (dados de demonstração)"


async def _get_or_create_state(db, uf: str) -> State:
    state = (await db.execute(select(State).where(State.uf == uf))).scalar_one_or_none()
    if state is None:
        state = State(name=_STATE_NAMES[uf], uf=uf)
        db.add(state)
        await db.flush()
    return state


async def _get_or_create_board(db, slug: str) -> Board:
    board = (await db.execute(select(Board).where(Board.slug == slug))).scalar_one_or_none()
    if board is None:
        board = Board(name=_BOARD_NAMES[slug], slug=slug, aliases=[slug])
        db.add(board)
        await db.flush()
    return board


async def _get_or_create_subject(db, slug: str) -> Subject:
    subject = (await db.execute(select(Subject).where(Subject.slug == slug))).scalar_one_or_none()
    if subject is None:
        subject = Subject(name=_SUBJECT_NAMES[slug], slug=slug)
        db.add(subject)
        await db.flush()
    return subject


async def _get_or_create_exam(db, board: Board) -> Exam:
    exam = (
        await db.execute(
            select(Exam).where(Exam.organization == _EXAM_ORG, Exam.year == _EXAM_YEAR, Exam.role == board.name)
        )
    ).scalar_one_or_none()
    if exam is None:
        exam = Exam(
            name=f"Concurso de Exemplo — estilo {board.name}",
            organization=_EXAM_ORG,
            role=board.name,
            year=_EXAM_YEAR,
        )
        db.add(exam)
        await db.flush()
    return exam


async def seed() -> int:
    inserted = 0
    async with get_db_context() as db:
        rows: list[dict[str, Any]] = []
        for item in _QUESTIONS:
            board = await _get_or_create_board(db, item["board"])
            subject = await _get_or_create_subject(db, item["subject"])
            exam = await _get_or_create_exam(db, board)
            state = await _get_or_create_state(db, item.get("state_uf", "BR"))

            content_hash = compute_content_hash(item["content"], item["options"])
            rows.append(
                {
                    "content": item["content"],
                    "options": item["options"],
                    "correct_option": item["correct_option"],
                    "year": _EXAM_YEAR,
                    "difficulty_level": item["difficulty"],
                    "content_hash": content_hash,
                    "source_url": None,
                    "board_id": board.id,
                    "subject_id": subject.id,
                    "exam_id": exam.id,
                    "state_id": state.id,
                }
            )

        inserted = await crud_question.bulk_insert_questions(db, rows)
    return inserted


async def main() -> None:
    try:
        inserted = await seed()
        logger.info("Seed concluído: %d questão(ões) inserida(s) (duplicatas ignoradas).", inserted)
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
