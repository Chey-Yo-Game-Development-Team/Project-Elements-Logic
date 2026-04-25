// Ver-C#/Scripts/Core/Enums.cs
// 属性・ポジションの列挙型定義と、ポジション補正倍率を取得する拡張メソッド

namespace ProjectElements.Core
{
    /// <summary>
    /// カードおよびキャラクターの属性。
    /// TYPELESS は無属性（ジョーカー）として機能する。
    /// </summary>
    public enum Element
    {
        Fire,
        Water,
        Light,
        Typeless
    }

    /// <summary>
    /// バトル時のキャラクター配置ポジション。
    /// 後衛(Back)ほど敵に狙われやすい（ヘイト倍率が高い）。
    /// </summary>
    public enum Position
    {
        Front,  // 前衛: ヘイト倍率 0.5x（最も狙われにくい）
        Mid,    // 中衛: ヘイト倍率 1.0x
        Back    // 後衛: ヘイト倍率 2.0x（最も狙われやすい）
    }

    /// <summary>
    /// コンボの種類。
    /// 倍率の優先度: Flash > Rainbow > Pair > None
    /// </summary>
    public enum ComboType
    {
        Flash,    // 同色3枚: 全体 2.5x
        Rainbow,  // 3色すべて: 全体 1.5x
        Pair,     // 同色2枚+異色1枚: ペア部分 1.2x、残り 1.0x
        None      // 役なし: 全体 1.0x
    }

    /// <summary>
    /// Position 列挙型の拡張メソッド群。
    /// </summary>
    public static class PositionExtensions
    {
        /// <summary>
        /// ポジションに対応する固定ヘイト倍率を返す。
        /// 後衛が全滅した場合の動的繰り上げは HateSystem 側で処理する。
        /// </summary>
        public static float GetBaseHateMultiplier(this Position position)
        {
            switch (position)
            {
                case Position.Front: return 0.5f;
                case Position.Mid:   return 1.0f;
                case Position.Back:  return 2.0f;
                default:             return 1.0f;
            }
        }

        /// <summary>
        /// ポジションの「後ろ度」を整数で返す（大きいほど後方）。
        /// ターゲット選定の同値比較に使用する。
        /// </summary>
        public static int GetOrderIndex(this Position position)
        {
            switch (position)
            {
                case Position.Front: return 0;
                case Position.Mid:   return 1;
                case Position.Back:  return 2;
                default:             return 0;
            }
        }
    }
}
