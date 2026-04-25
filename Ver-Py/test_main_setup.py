"""
Project Elements - main.py セットアップ検証テスト

setup() 関数が返すパーティのデータ構造を検証する。
"""
import pytest
from models import Attribute
from main import setup


class TestSetupPartyStructure:
    def test_party_has_three_characters(self):
        """パーティは3名で構成される。"""
        party, _ = setup()
        assert len(party.characters) == 3

    def test_each_character_has_three_cards(self):
        """各キャラクターはカードを3枚装備している。"""
        party, _ = setup()
        for char in party.characters:
            assert len(char.cards) == 3

    def test_deck_has_nine_cards(self):
        """デッキはパーティ全員のカード合計（3×3=9枚）で構成される。"""
        party, _ = setup()
        assert len(party.deck) + len(party.hand) == 9

    def test_card_owner_matches_character_name(self):
        """各カードの owner フィールドが装備キャラクターの名前と一致する。"""
        party, _ = setup()
        for char in party.characters:
            for card in char.cards:
                assert card.owner == char.name

    def test_aria_cards_are_fire(self):
        """アリアのカードはすべて火属性。"""
        party, _ = setup()
        aria = next(c for c in party.characters if c.name == "アリア")
        assert all(card.attribute == Attribute.FIRE for card in aria.cards)

    def test_rin_cards_are_water(self):
        """リンのカードはすべて水属性。"""
        party, _ = setup()
        rin = next(c for c in party.characters if c.name == "リン")
        assert all(card.attribute == Attribute.WATER for card in rin.cards)

    def test_lux_has_light_and_typeless_cards(self):
        """ルクスのカードは光2枚 + 無1枚で構成される。"""
        party, _ = setup()
        lux = next(c for c in party.characters if c.name == "ルクス")
        attrs = [card.attribute for card in lux.cards]
        assert attrs.count(Attribute.LIGHT) == 2
        assert attrs.count(Attribute.TYPELESS) == 1
