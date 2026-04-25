// Ver-C#/Scripts/Models/Party.cs
// 3名の BattleCharacter を保持し、共有デッキ（9枚）と手札（3枚）を管理するクラス。
// Python の Party dataclass（models.py）に相当。

using System;
using System.Collections.Generic;
using System.Linq;
using ProjectElements.Core;
using ProjectElements.Data;

namespace ProjectElements.Models
{
    /// <summary>
    /// バトル中のパーティ全体を管理する純粋 C# クラス。
    /// デッキは全メンバーのカード9枚を1つにまとめた「共有デッキ方式」。
    /// </summary>
    public class Party
    {
        // -----------------------------------------------------------------
        // 公開プロパティ
        // -----------------------------------------------------------------

        /// <summary>パーティメンバー3名（配列の並び順がそのまま表示順になる）。</summary>
        public BattleCharacter[] Characters { get; }

        /// <summary>全カードがジョーカーだった場合のフォールバック属性（パーティリーダー属性）。</summary>
        public Attribute LeaderAttribute { get; }

        /// <summary>山札の残り枚数。</summary>
        public int DeckCount => _deck.Count;

        /// <summary>現在の手札（読み取り専用ビュー）。</summary>
        public IReadOnlyList<CardData> Hand => _hand;

        /// <summary>生存しているキャラクターのリスト。</summary>
        public IReadOnlyList<BattleCharacter> AliveCharacters =>
            Characters.Where(c => c.IsAlive).ToList();

        // -----------------------------------------------------------------
        // 内部状態
        // -----------------------------------------------------------------

        // 山札。末尾から取り出す（スタック操作）ことで O(1) のドローを実現する
        private readonly List<CardData> _deck;
        private readonly List<CardData> _hand;

        // Fisher-Yates シャッフル用の乱数生成器
        private readonly System.Random _rng;

        // -----------------------------------------------------------------
        // コンストラクタ
        // -----------------------------------------------------------------

        /// <param name="characters">パーティメンバー3名</param>
        /// <param name="leaderAttribute">全ジョーカー時のフォールバック属性（デフォルト: Fire）</param>
        /// <param name="seed">シャッフルのシード値（0 以下で時刻ベースのランダム）</param>
        public Party(
            BattleCharacter[] characters,
            Attribute leaderAttribute = Attribute.Fire,
            int seed = 0)
        {
            if (characters == null || characters.Length != 3)
                throw new ArgumentException("パーティは3名必要です");

            Characters      = characters;
            LeaderAttribute = leaderAttribute;
            _rng            = seed > 0 ? new System.Random(seed) : new System.Random();
            _deck           = new List<CardData>(9);
            _hand           = new List<CardData>(3);

            BuildAndShuffleDeck();
            // Python 版と同様、コンストラクタではドローしない（ターン開始時に DrawHand() を呼ぶ）
        }

        // -----------------------------------------------------------------
        // デッキ操作
        // -----------------------------------------------------------------

        /// <summary>
        /// 全メンバーのカードを集めてデッキを9枚に再構築し、シャッフルする。
        /// Python の reshuffle() に相当。
        /// </summary>
        public void Reshuffle()
        {
            BuildAndShuffleDeck();
        }

        /// <summary>
        /// デッキから3枚引いて手札に加える。デッキ切れの場合は自動リシャッフルする。
        /// Python の draw_hand() に相当。
        /// </summary>
        /// <returns>リシャッフルが発生した場合 true</returns>
        public bool DrawHand()
        {
            bool reshuffled = false;

            while (_hand.Count < 3)
            {
                if (_deck.Count == 0)
                {
                    Reshuffle();
                    reshuffled = true;
                }

                // 末尾からドロー（O(1)）
                int lastIndex = _deck.Count - 1;
                _hand.Add(_deck[lastIndex]);
                _deck.RemoveAt(lastIndex);
            }

            return reshuffled;
        }

        /// <summary>
        /// 手札3枚を全てプレイして返す。手札はクリアされる。
        /// 次ターン開始時に DrawHand() を呼ぶまで手札は補充されない。
        /// Python の play_hand() に相当。
        /// </summary>
        public CardData[] PlayHand()
        {
            var played = _hand.ToArray();
            _hand.Clear();
            return played;
        }

        /// <summary>
        /// 山札の残りカードをオーナー別にカウントした辞書を返す。
        /// デバッグログ用途。
        /// </summary>
        public Dictionary<string, int> GetDeckSummary()
        {
            var summary = new Dictionary<string, int>();

            foreach (var chara in Characters)
            {
                int count = _deck.Count(card => chara.Cards.Any(owned => owned == card));
                summary[chara.Name] = count;
            }

            return summary;
        }

        // -----------------------------------------------------------------
        // 内部ヘルパー
        // -----------------------------------------------------------------

        private void BuildAndShuffleDeck()
        {
            _deck.Clear();

            // 全メンバーのカード3枚ずつを1つのデッキにフラット展開
            foreach (var chara in Characters)
                foreach (var card in chara.Cards)
                    _deck.Add(card);

            Shuffle(_deck);
        }

        /// <summary>Fisher-Yates アルゴリズムによるインプレースシャッフル。</summary>
        private void Shuffle(List<CardData> list)
        {
            for (int i = list.Count - 1; i > 0; i--)
            {
                int j = _rng.Next(i + 1);
                (list[i], list[j]) = (list[j], list[i]);
            }
        }
    }
}
