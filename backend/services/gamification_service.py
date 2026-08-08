"""Regras de XP e streak. Mantido isolado dos routers para que a pontuação
possa evoluir (ex.: multiplicadores por dificuldade) sem tocar na camada HTTP.
"""
from backend.models.question import DifficultyLevel

_XP_BY_DIFFICULTY: dict[DifficultyLevel, int] = {
    DifficultyLevel.EASY: 5,
    DifficultyLevel.MEDIUM: 10,
    DifficultyLevel.HARD: 15,
}

_CEBRASPE_PENALTY_MULTIPLIER = -1  # 1 erro anula 1 acerto no modo Cebraspe


def calculate_xp(
    *, is_correct: bool, difficulty_level: DifficultyLevel, is_cebraspe_mode: bool
) -> int:
    base_xp = _XP_BY_DIFFICULTY[difficulty_level]

    if is_correct:
        return base_xp

    if is_cebraspe_mode:
        return base_xp * _CEBRASPE_PENALTY_MULTIPLIER

    return 0
