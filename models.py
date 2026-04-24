"""
Project Elements - Core Data Models (Phase 1)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import random


class Attribute(Enum):
    FIRE = "fire"
    WATER = "water"
    LIGHT = "light"
    TYPELESS = "typeless"


class Position(Enum):
    FRONT = "front"
    MID = "mid"
    BACK = "back"

    @property
    def hate_multiplier(self) -> float:
        multipliers = {
            Position.FRONT: 0.5,
            Position.MID: 1.0,
            Position.BACK: 2.0,
        }
        return multipliers[self]


@dataclass
class Card:
    attribute: Attribute
    base_power: float

    def __repr__(self) -> str:
        return f"Card({self.attribute.value}, {self.base_power})"


@dataclass
class Character:
    name: str
    attribute: Attribute
    max_hp: int
    position: Position
    cards: List[Card]
    current_hp: int = field(init=False)
    base_hate: float = field(default=10.0)

    def __post_init__(self) -> None:
        self.current_hp = self.max_hp
        if len(self.cards) != 3:
            raise ValueError(f"キャラクター '{self.name}' のカードは3枚必要です（現在: {len(self.cards)}枚）")

    @property
    def is_alive(self) -> bool:
        return self.current_hp > 0

    @property
    def hp_ratio(self) -> float:
        return self.current_hp / self.max_hp

    @property
    def effective_hate(self) -> float:
        return self.base_hate * self.position.hate_multiplier

    def take_damage(self, damage: float) -> None:
        self.current_hp = max(0, self.current_hp - int(damage))

    def __repr__(self) -> str:
        return (
            f"Character({self.name}, {self.attribute.value}, "
            f"HP:{self.current_hp}/{self.max_hp}, {self.position.value})"
        )


@dataclass
class Party:
    characters: List[Character]
    leader_attribute: Attribute = Attribute.FIRE

    deck: List[Card] = field(init=False)
    hand: List[Card] = field(init=False)

    def __post_init__(self) -> None:
        if len(self.characters) != 3:
            raise ValueError(f"パーティは3名必要です（現在: {len(self.characters)}名）")
        self.deck = [card for char in self.characters for card in char.cards]
        random.shuffle(self.deck)
        self.hand = []
        self.draw_to_fill()

    def draw_to_fill(self) -> None:
        """手札が3枚になるまでデッキから補充する。デッキ切れの場合はリシャッフル。"""
        while len(self.hand) < 3:
            if not self.deck:
                self.reshuffle()
            self.hand.append(self.deck.pop(0))

    def reshuffle(self) -> None:
        """デッキを9枚に戻してシャッフルする。"""
        self.deck = [card for char in self.characters for card in char.cards]
        random.shuffle(self.deck)

    def play_hand(self) -> List[Card]:
        """手札3枚を全てプレイして返す。次のターン用に手札を補充する。"""
        played = self.hand[:]
        self.hand = []
        self.draw_to_fill()
        return played

    @property
    def alive_characters(self) -> List[Character]:
        return [c for c in self.characters if c.is_alive]

    def update_position_after_death(self) -> None:
        """
        後衛が全滅した際、生存キャラの最後尾ポジションの倍率を2.0xに引き上げる。
        Position自体は変更できないため、Character.base_hateを調整する方式ではなく、
        動的倍率を管理するため、Character.positionをそのまま使いつつ
        hate_multiplierを上書きする仕組みはフェーズ3で実装する。
        """
        pass

    def __repr__(self) -> str:
        chars = ", ".join(c.name for c in self.characters)
        return f"Party([{chars}], hand={self.hand})"
