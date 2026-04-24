"""
Project Elements - Hate & Target System Unit Tests (Phase 3)

仕様書 §3 「後衛優先ヘイトアルゴリズム」を検証する。
"""
import pytest
from models import Attribute, Card, Character, Position
from hate_system import HateSystem, POSITION_ORDER


# ---------------------------------------------------------------------------
# テスト用ヘルパー
# ---------------------------------------------------------------------------

def make_char(
    name: str,
    position: Position,
    base_hate: float = 10.0,
    hp: int = 100,
    current_hp: int | None = None,
) -> Character:
    """テスト用キャラクターを生成する。"""
    cards = [Card(Attribute.FIRE, 10.0)] * 3
    char = Character(
        name=name,
        attribute=Attribute.FIRE,
        max_hp=hp,
        position=position,
        cards=cards,
        base_hate=base_hate,
    )
    if current_hp is not None:
        char.current_hp = current_hp
    return char


# ---------------------------------------------------------------------------
# §3-2: ポジション補正倍率（正常系）
# ---------------------------------------------------------------------------

class TestPositionOrder:
    def test_position_order_back_is_highest(self):
        assert POSITION_ORDER[Position.BACK] > POSITION_ORDER[Position.MID]
        assert POSITION_ORDER[Position.MID] > POSITION_ORDER[Position.FRONT]


class TestGetDynamicMultiplier:
    def test_back_gets_2x_when_all_alive(self):
        chars = [
            make_char("front", Position.FRONT),
            make_char("mid", Position.MID),
            make_char("back", Position.BACK),
        ]
        assert HateSystem.get_dynamic_multiplier(chars[2], chars) == 2.0

    def test_mid_gets_1x_when_all_alive(self):
        chars = [
            make_char("front", Position.FRONT),
            make_char("mid", Position.MID),
            make_char("back", Position.BACK),
        ]
        assert HateSystem.get_dynamic_multiplier(chars[1], chars) == 1.0

    def test_front_gets_0_5x_when_all_alive(self):
        chars = [
            make_char("front", Position.FRONT),
            make_char("mid", Position.MID),
            make_char("back", Position.BACK),
        ]
        assert HateSystem.get_dynamic_multiplier(chars[0], chars) == 0.5


# ---------------------------------------------------------------------------
# §3-3: ポジション繰り上げ（Promotion）
# ---------------------------------------------------------------------------

class TestPromotionWhenBackDies:
    def test_mid_promoted_to_2x_when_back_dead(self):
        """後衛が死亡した後、中衛の補正倍率が 2.0x に繰り上がる。"""
        front = make_char("front", Position.FRONT)
        mid = make_char("mid", Position.MID)
        # back は死亡（alive_chars に含めない）
        alive = [front, mid]

        assert HateSystem.get_dynamic_multiplier(mid, alive) == 2.0
        assert HateSystem.get_dynamic_multiplier(front, alive) == 0.5

    def test_front_promoted_to_2x_when_back_and_mid_dead(self):
        """後衛・中衛が全滅した後、前衛の補正倍率が 2.0x になる。"""
        front = make_char("front", Position.FRONT)
        alive = [front]

        assert HateSystem.get_dynamic_multiplier(front, alive) == 2.0

    def test_no_promotion_while_back_still_alive(self):
        """後衛が生存している限り中衛は 1.0x のまま。"""
        front = make_char("front", Position.FRONT)
        mid = make_char("mid", Position.MID)
        back = make_char("back", Position.BACK)
        alive = [front, mid, back]

        assert HateSystem.get_dynamic_multiplier(mid, alive) == 1.0

    def test_empty_alive_falls_back_to_natural_multiplier(self):
        """生存者リストが空の場合は Position の固定倍率を返す。"""
        char = make_char("back", Position.BACK)
        assert HateSystem.get_dynamic_multiplier(char, []) == 2.0

        char_mid = make_char("mid", Position.MID)
        assert HateSystem.get_dynamic_multiplier(char_mid, []) == 1.0


# ---------------------------------------------------------------------------
# §3-1: 実効ヘイト計算
# ---------------------------------------------------------------------------

class TestGetEffectiveHate:
    def test_effective_hate_normal(self):
        """実効ヘイト = 基礎ヘイト × ポジション倍率"""
        back = make_char("back", Position.BACK, base_hate=10.0)
        mid = make_char("mid", Position.MID, base_hate=10.0)
        front = make_char("front", Position.FRONT, base_hate=10.0)
        alive = [front, mid, back]

        assert HateSystem.get_effective_hate(back, alive) == pytest.approx(20.0)
        assert HateSystem.get_effective_hate(mid, alive) == pytest.approx(10.0)
        assert HateSystem.get_effective_hate(front, alive) == pytest.approx(5.0)

    def test_effective_hate_after_back_dies(self):
        """後衛死亡後: 中衛の実効ヘイトが 2.0x 分になる。"""
        front = make_char("front", Position.FRONT, base_hate=10.0)
        mid = make_char("mid", Position.MID, base_hate=10.0)
        alive = [front, mid]

        assert HateSystem.get_effective_hate(mid, alive) == pytest.approx(20.0)
        assert HateSystem.get_effective_hate(front, alive) == pytest.approx(5.0)

    def test_higher_base_hate_gives_higher_score(self):
        """同じポジションでも基礎ヘイトが高い方が実効ヘイトも高い。"""
        a = make_char("a", Position.MID, base_hate=20.0)
        b = make_char("b", Position.MID, base_hate=5.0)
        alive = [a, b]

        assert HateSystem.get_effective_hate(a, alive) > HateSystem.get_effective_hate(b, alive)


# ---------------------------------------------------------------------------
# §3-2: ターゲット選定（基本）
# ---------------------------------------------------------------------------

class TestSelectTarget:
    def test_highest_hate_is_targeted(self):
        """実効ヘイトが最大のキャラがターゲットになる。"""
        front = make_char("front", Position.FRONT, base_hate=100.0)
        mid = make_char("mid", Position.MID, base_hate=1.0)
        back = make_char("back", Position.BACK, base_hate=1.0)

        # front: 100 * 0.5 = 50, mid: 1 * 1.0 = 1, back: 1 * 2.0 = 2
        target = HateSystem.select_target([front, mid, back])
        assert target == front

    def test_back_targeted_in_typical_equal_hate(self):
        """全員同ヘイト値なら後衛がターゲット。"""
        front = make_char("front", Position.FRONT, base_hate=10.0)
        mid = make_char("mid", Position.MID, base_hate=10.0)
        back = make_char("back", Position.BACK, base_hate=10.0)

        # front: 5, mid: 10, back: 20 → back が最大
        target = HateSystem.select_target([front, mid, back])
        assert target == back

    def test_no_alive_returns_none(self):
        """生存者がいない場合は None を返す。"""
        dead = make_char("dead", Position.BACK, current_hp=0)
        assert HateSystem.select_target([dead]) is None

    def test_only_alive_characters_are_considered(self):
        """死亡キャラは候補から外れる。"""
        dead_back = make_char("dead_back", Position.BACK, current_hp=0)
        alive_mid = make_char("alive_mid", Position.MID, base_hate=1.0)

        target = HateSystem.select_target([dead_back, alive_mid])
        assert target == alive_mid


# ---------------------------------------------------------------------------
# §3-3 エッジケース: 同値タイブレーク
# ---------------------------------------------------------------------------

class TestTieBreaking:
    def test_tiebreak_by_position_back_wins(self):
        """実効ヘイトが同値なら後ろのポジションを優先。"""
        # mid と back に同じ実効ヘイトを持たせる:
        # mid: 20 * 1.0 = 20,  back: 10 * 2.0 = 20
        mid = make_char("mid", Position.MID, base_hate=20.0)
        back = make_char("back", Position.BACK, base_hate=10.0)

        target = HateSystem.select_target([mid, back])
        assert target == back

    def test_tiebreak_by_hp_ratio_lower_hp_wins(self):
        """ポジションも同値なら HP 割合が低い方を優先。"""
        # 同ポジション・同実効ヘイトで HP だけ異なる
        char_high_hp = make_char("high_hp", Position.MID, base_hate=10.0, hp=100, current_hp=80)
        char_low_hp = make_char("low_hp", Position.MID, base_hate=10.0, hp=100, current_hp=20)

        target = HateSystem.select_target([char_high_hp, char_low_hp])
        assert target == char_low_hp

    def test_tiebreak_position_takes_priority_over_hp(self):
        """ヘイト同値の場合、HP より先にポジションで判断する。"""
        # back: base=10, eff=20, HP=100%
        # mid: base=20, eff=20, HP=1%
        back = make_char("back", Position.BACK, base_hate=10.0, hp=100, current_hp=100)
        mid = make_char("mid", Position.MID, base_hate=20.0, hp=100, current_hp=1)

        target = HateSystem.select_target([back, mid])
        # 実効ヘイトが同値 → ポジションで判定 → back が勝つ
        assert target == back


# ---------------------------------------------------------------------------
# §3: ヘイト蓄積
# ---------------------------------------------------------------------------

class TestAddHate:
    def test_add_hate_increases_base_hate(self):
        char = make_char("char", Position.MID, base_hate=10.0)
        HateSystem.add_hate(char, 5.0)
        assert char.base_hate == pytest.approx(15.0)

    def test_add_hate_affects_target_selection(self):
        """ヘイト蓄積後にターゲットが変わることを確認。"""
        front = make_char("front", Position.FRONT, base_hate=100.0)
        back = make_char("back", Position.BACK, base_hate=10.0)
        # front: 100*0.5=50, back: 10*2.0=20 → front がターゲット

        target_before = HateSystem.select_target([front, back])
        assert target_before == front

        # back のヘイトを増やす
        HateSystem.add_hate(back, 200.0)
        # back: 210*2.0=420 → back がターゲット
        target_after = HateSystem.select_target([front, back])
        assert target_after == back


# ---------------------------------------------------------------------------
# 複合シナリオ: 後衛が死んだ後のターゲット変化
# ---------------------------------------------------------------------------

class TestPromotionAndTargetScenario:
    def test_mid_becomes_target_after_back_dies(self):
        """後衛が死亡した後、中衛が最高ヘイトとしてターゲット化される。"""
        front = make_char("front", Position.FRONT, base_hate=10.0)
        mid = make_char("mid", Position.MID, base_hate=10.0)
        back = make_char("back", Position.BACK, base_hate=10.0, current_hp=0)  # 死亡

        target = HateSystem.select_target([front, mid, back])
        assert target == mid  # 中衛が繰り上がり後衛扱い

    def test_front_becomes_target_after_all_others_die(self):
        """後衛・中衛が全滅したら前衛がターゲット。"""
        front = make_char("front", Position.FRONT, base_hate=10.0)
        mid = make_char("mid", Position.MID, base_hate=10.0, current_hp=0)
        back = make_char("back", Position.BACK, base_hate=10.0, current_hp=0)

        target = HateSystem.select_target([front, mid, back])
        assert target == front
