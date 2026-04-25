// Ver-C#/Scripts/Logic/HateSystem.cs
// hate_system.py の移植。
// 動的なポジション補正倍率の算出、実効ヘイトスコアの計算、
// およびタイブレークロジックを含むターゲット選定を担う。

using System.Collections.Generic;
using System.Linq;
using ProjectElements.Core;
using ProjectElements.Models;

namespace ProjectElements.Logic
{
    /// <summary>
    /// ヘイト管理とターゲット選定を担う静的ユーティリティクラス。
    /// Python の HateSystem クラスに相当。
    ///
    /// 動的ポジション補正の考え方:
    ///   「生存者の中で最後尾にいるポジション」は常に 2.0x を得る。
    ///   後衛が全員戦闘不能なら中衛が 2.0x に繰り上がり、
    ///   中衛まで全滅すれば前衛が 2.0x になる。
    /// </summary>
    public static class HateSystem
    {
        // ---------------------------------------------------------
        // ① 動的ポジション補正倍率の取得
        // ---------------------------------------------------------

        /// <summary>
        /// 生存者リストを基に、そのキャラクターの動的なポジション補正倍率を返す。
        ///
        /// ・生存者の中で最後尾ポジション（GetOrderIndex が最大）のキャラ → 2.0x
        /// ・それ以外 → Position に定義された固定倍率（Front=0.5, Mid=1.0, Back=2.0）
        ///
        /// Python の get_dynamic_multiplier() に相当。
        /// </summary>
        public static float GetDynamicMultiplier(
            BattleCharacter              character,
            IReadOnlyList<BattleCharacter> aliveChars)
        {
            // 生存者がいない場合は固定倍率をそのまま返す（安全策）
            if (aliveChars.Count == 0)
                return character.Position.GetBaseHateMultiplier();

            // 生存者の中で最も後方のポジション順序を取得
            int backmostOrder = aliveChars.Max(c => c.Position.GetOrderIndex());

            // このキャラクターが最後尾なら 2.0x に繰り上げ
            if (character.Position.GetOrderIndex() == backmostOrder)
                return 2.0f;

            // それ以外は固定倍率
            return character.Position.GetBaseHateMultiplier();
        }

        // ---------------------------------------------------------
        // ② 実効ヘイトスコアの算出
        // ---------------------------------------------------------

        /// <summary>
        /// 実効ヘイトスコア = 基礎ヘイト値 × 動的ポジション補正倍率。
        /// ターゲット選定の主比較値として使用する。
        ///
        /// Python の get_effective_hate() に相当。
        /// </summary>
        public static float GetEffectiveHate(
            BattleCharacter              character,
            IReadOnlyList<BattleCharacter> aliveChars)
        {
            return character.BaseHate * GetDynamicMultiplier(character, aliveChars);
        }

        // ---------------------------------------------------------
        // ③ ターゲット選定
        // ---------------------------------------------------------

        /// <summary>
        /// 生存キャラクターの中から敵の攻撃ターゲットを選択して返す。
        /// 生存者がいない場合は null を返す。
        ///
        /// タイブレーク優先順位:
        ///   1. 実効ヘイトスコアが最大
        ///   2. 同値ならポジションが後方（GetOrderIndex が大きい）
        ///   3. さらに同値なら残りHP割合が低い方
        ///
        /// Python の select_target() に相当。
        /// </summary>
        public static BattleCharacter SelectTarget(IReadOnlyList<BattleCharacter> characters)
        {
            var alive = characters.Where(c => c.IsAlive).ToList();
            if (alive.Count == 0) return null;

            // LINQ の OrderBy チェーンでタイブレークを再現
            // Python の sort_key: (-hate, -position_order, hp_ratio) に対応
            return alive
                .OrderByDescending(c => GetEffectiveHate(c, alive))   // 1. ヘイト降順
                .ThenByDescending(c => c.Position.GetOrderIndex())      // 2. ポジション後方優先
                .ThenBy          (c => c.HpRatio)                       // 3. HP割合昇順（低い方を優先）
                .First();
        }

        // ---------------------------------------------------------
        // ④ ヘイト蓄積
        // ---------------------------------------------------------

        /// <summary>
        /// キャラクターが行動するたびに呼び出し、基礎ヘイト値を加算する。
        /// Python の add_hate() に相当。
        /// </summary>
        public static void AddHate(BattleCharacter character, float amount)
        {
            character.BaseHate += amount;
        }
    }
}
