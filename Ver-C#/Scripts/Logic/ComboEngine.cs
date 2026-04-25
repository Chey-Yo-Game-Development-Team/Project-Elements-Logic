// Ver-C#/Scripts/Logic/ComboEngine.cs
// combo_engine.py の移植。
// ジョーカー（無属性）の自動最適化、コンボ役判定、最終ダメージ計算を担う。

using System;
using System.Collections.Generic;
using System.Linq;
using ProjectElements.Core;
using ProjectElements.Data;
using ProjectElements.Models;

namespace ProjectElements.Logic
{
    // =========================================================
    // ComboResult: コンボ判定の結果を保持するデータクラス
    // =========================================================

    /// <summary>
    /// ジョーカー変換後の属性リストと成立したコンボ種別を保持する。
    /// Python の ComboResult dataclass に相当。
    /// </summary>
    public class ComboResult
    {
        /// <summary>成立したコンボ役。</summary>
        public ComboType ComboType { get; }

        /// <summary>
        /// ジョーカー変換済みの属性配列（要素数=3、Typeless なし）。
        /// インデックスはプレイされたカードの順序と対応している。
        /// </summary>
        public Attribute[] ResolvedAttributes { get; }

        public ComboResult(ComboType comboType, Attribute[] resolvedAttributes)
        {
            ComboType          = comboType;
            ResolvedAttributes = resolvedAttributes;
        }

        /// <summary>
        /// 各カード（インデックス順）に対するダメージ倍率を返す。
        /// Flash/Rainbow は全カード均等、Pair はペア2枚に1.2x・残り1枚に1.0x。
        /// </summary>
        public float[] GetMultipliers()
        {
            switch (ComboType)
            {
                case ComboType.Flash:
                    return new[] { 2.5f, 2.5f, 2.5f };

                case ComboType.Rainbow:
                    return new[] { 1.5f, 1.5f, 1.5f };

                case ComboType.Pair:
                    // 2回登場する属性がペアの属性
                    Attribute pairAttr = ResolvedAttributes
                        .GroupBy(a => a)
                        .OrderByDescending(g => g.Count())
                        .First().Key;
                    return ResolvedAttributes
                        .Select(a => a == pairAttr ? 1.2f : 1.0f)
                        .ToArray();

                default:
                    return new[] { 1.0f, 1.0f, 1.0f };
            }
        }

        /// <summary>
        /// コンボ種別の代表倍率。ジョーカー最適化の優先度比較に使用する。
        /// Flash=2.5 > Rainbow=1.5 > Pair=1.2 > None=1.0
        /// </summary>
        public float TotalMultiplier
        {
            get
            {
                switch (ComboType)
                {
                    case ComboType.Flash:   return 2.5f;
                    case ComboType.Rainbow: return 1.5f;
                    case ComboType.Pair:    return 1.2f;
                    default:                return 1.0f;
                }
            }
        }
    }

    // =========================================================
    // DamageResult: ダメージ計算結果を保持するデータクラス
    // =========================================================

    /// <summary>
    /// 各キャラクターの最終ダメージとコンボ結果をまとめて保持する。
    /// Python の DamageResult dataclass に相当。
    /// </summary>
    public class DamageResult
    {
        /// <summary>
        /// キャラクターごとの最終ダメージ。
        /// インデックスは CalculateDamage に渡した characters 配列と対応している。
        /// </summary>
        public float[] CharacterDamages { get; }

        /// <summary>今ターンのコンボ判定結果。</summary>
        public ComboResult ComboResult { get; }

        /// <summary>全キャラクターのダメージ合計。</summary>
        public float TotalDamage => CharacterDamages.Sum();

        public DamageResult(float[] characterDamages, ComboResult comboResult)
        {
            CharacterDamages = characterDamages;
            ComboResult      = comboResult;
        }
    }

    // =========================================================
    // ComboEngine: コンボ処理のメインロジック（静的ユーティリティ）
    // =========================================================

    /// <summary>
    /// 無属性ジョーカーの最適化、コンボ役判定、ダメージ計算をまとめた静的クラス。
    /// Python の combo_engine.py 全体に相当。
    /// </summary>
    public static class ComboEngine
    {
        // 基本属性リスト（Typeless を除く）
        // Python の BASIC_ATTRIBUTES に相当
        private static readonly Attribute[] BasicAttributes =
            { Attribute.Fire, Attribute.Water, Attribute.Light };

        // ---------------------------------------------------------
        // ① コンボ役の純粋判定（Typeless なし前提）
        // ---------------------------------------------------------

        /// <summary>
        /// Typeless を含まない3属性の配列からコンボ役を判定して返す。
        /// Python の _judge_combo() に相当。
        /// </summary>
        private static ComboResult JudgeCombo(Attribute[] attrs)
        {
            var unique = new HashSet<Attribute>(attrs);

            // フラッシュ: 3枚すべて同属性
            if (unique.Count == 1)
                return new ComboResult(ComboType.Flash, attrs);

            // レインボー: 3種類すべて異なる（Typeless 除去済みなので Fire/Water/Light の3色確定）
            if (unique.Count == 3)
                return new ComboResult(ComboType.Rainbow, attrs);

            // ペア: 2種類（2枚 + 1枚）
            if (unique.Count == 2)
                return new ComboResult(ComboType.Pair, attrs);

            return new ComboResult(ComboType.None, attrs);
        }

        // ---------------------------------------------------------
        // ② ジョーカー全置換パターンの列挙
        //    Python の itertools.product(BASIC_ATTRIBUTES, repeat=n) に相当
        // ---------------------------------------------------------

        /// <summary>
        /// count 個の置換スロットに対して、基本属性の全組み合わせを列挙する。
        /// count=1 → 3通り、count=2 → 9通り（3×3）。
        /// </summary>
        private static IEnumerable<Attribute[]> GetReplacementCombinations(int count)
        {
            if (count == 1)
            {
                // 1ジョーカー: Fire / Water / Light の3通りを試す
                foreach (var a in BasicAttributes)
                    yield return new[] { a };
            }
            else // count == 2
            {
                // 2ジョーカー: 3×3 = 9通りの直積を試す
                foreach (var a in BasicAttributes)
                    foreach (var b in BasicAttributes)
                        yield return new[] { a, b };
            }
        }

        // ---------------------------------------------------------
        // ③ ジョーカー自動最適化（メイン公開メソッド）
        // ---------------------------------------------------------

        /// <summary>
        /// 手札3枚の Typeless（ジョーカー）を最も高倍率になる基本属性に自動変換し、
        /// コンボ判定結果を返す。
        ///
        /// 変換優先度: Flash(2.5x) > Rainbow(1.5x) > Pair(1.2x) > None(1.0x)
        ///
        /// ・Typeless 0枚 → そのまま判定
        /// ・Typeless 1〜2枚 → 全置換パターンを試して最高役を選択
        /// ・Typeless 3枚 → リーダー属性のフラッシュとして扱う
        ///
        /// Python の resolve_jokers() に相当。
        /// </summary>
        public static ComboResult ResolveJokers(
            CardData[]  cards,
            Attribute   leaderAttribute = Attribute.Fire)
        {
            if (cards.Length != 3)
                throw new ArgumentException(
                    $"カードは3枚必要です（受け取った枚数: {cards.Length}）");

            // Typeless のインデックスを収集
            var typelessIndices = cards
                .Select((card, idx) => (card, idx))
                .Where(t => t.card.attribute == Attribute.Typeless)
                .Select(t => t.idx)
                .ToList();

            // ジョーカーなし: そのまま判定
            if (typelessIndices.Count == 0)
                return JudgeCombo(cards.Select(c => c.attribute).ToArray());

            // 全3枚ジョーカー: リーダー属性のフラッシュ
            if (typelessIndices.Count == 3)
                return new ComboResult(
                    ComboType.Flash,
                    new[] { leaderAttribute, leaderAttribute, leaderAttribute });

            // 1〜2枚ジョーカー: 全置換パターンを試して最高役を選ぶ
            Attribute[] baseAttrs = cards.Select(c => c.attribute).ToArray();
            ComboResult best      = null;

            foreach (var replacement in GetReplacementCombinations(typelessIndices.Count))
            {
                // 元の配列を壊さないようにコピーしてから置換
                Attribute[] trial = (Attribute[])baseAttrs.Clone();
                for (int i = 0; i < typelessIndices.Count; i++)
                    trial[typelessIndices[i]] = replacement[i];

                ComboResult candidate = JudgeCombo(trial);
                if (best == null || candidate.TotalMultiplier > best.TotalMultiplier)
                    best = candidate;
            }

            return best;
        }

        // ---------------------------------------------------------
        // ④ 最終ダメージ計算
        // ---------------------------------------------------------

        /// <summary>
        /// プレイされた3枚のカードとパーティメンバーから各キャラクターの最終ダメージを計算する。
        ///
        /// 計算式:
        ///   基礎攻撃力 × コンボ代表倍率 [× 所有者一致ボーナス 1.2x]
        ///
        /// ・生存キャラクター全員が攻撃する（自分のカードが場に出なかった場合もボーナスなしで攻撃）。
        /// ・所有者一致ボーナス: プレイされた3枚の中に自分の所持カードが1枚でも含まれていれば適用。
        ///   ScriptableObject の参照同一性で判定する。
        ///
        /// Python の calculate_damage() に相当。
        /// </summary>
        public static DamageResult CalculateDamage(
            CardData[]       playedCards,
            BattleCharacter[] characters,
            Attribute        leaderAttribute = Attribute.Fire)
        {
            if (playedCards.Length != 3)
                throw new ArgumentException("プレイされるカードは3枚である必要があります");
            if (characters.Length == 0)
                throw new ArgumentException("攻撃を行うキャラクターがパーティに存在しません");

            // 1. コンボ判定（ジョーカー変換含む）
            ComboResult comboResult     = ResolveJokers(playedCards, leaderAttribute);
            float       comboMultiplier = comboResult.TotalMultiplier;

            var characterDamages = new float[characters.Length];

            for (int i = 0; i < characters.Length; i++)
            {
                BattleCharacter chara = characters[i];

                // 戦闘不能キャラはダメージ 0
                if (!chara.IsAlive)
                {
                    characterDamages[i] = 0f;
                    continue;
                }

                // 2. 基礎攻撃力 × コンボ倍率
                float damage = chara.AttackPower * comboMultiplier;

                // 3. 所有者一致ボーナス判定
                //    ScriptableObject はアセットの参照同一性（== 演算子）で比較する
                bool hasOwnerBonus = playedCards.Any(played =>
                    chara.Cards.Any(owned => owned == played));

                if (hasOwnerBonus)
                    damage *= 1.2f;

                characterDamages[i] = damage;
            }

            return new DamageResult(characterDamages, comboResult);
        }
    }
}
