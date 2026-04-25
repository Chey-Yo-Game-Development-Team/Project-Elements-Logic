// Ver-C#/Scripts/Battle/BattleManager.cs
// Python の main.py 全体に相当するバトル進行管理クラス。
// インスペクターで CharacterData・ポジション・敵を設定し、
// Space キーを押すたびに1ターンが進む。

using System.Collections.Generic;
using System.Linq;
using System.Text;
using UnityEngine;
using ProjectElements.Core;
using ProjectElements.Data;
using ProjectElements.Models;
using ProjectElements.Logic;

namespace ProjectElements.Battle
{
    // =========================================================
    // インスペクター用のキャラクター設定構造体
    // =========================================================

    /// <summary>
    /// インスペクター上でキャラクターとポジションをセットで設定するための補助クラス。
    /// </summary>
    [System.Serializable]
    public class CharacterSetup
    {
        [Tooltip("使用するキャラクターのマスターデータ（ScriptableObject）")]
        public CharacterData data;

        [Tooltip("このキャラクターのバトル開始時のポジション")]
        public Position initialPosition = Position.Mid;
    }

    // =========================================================
    // BattleManager
    // =========================================================

    /// <summary>
    /// バトル全体の進行を管理する MonoBehaviour。
    ///
    /// 【操作方法】
    ///   Space キー : 1ターン進める
    ///   R キー     : バトルをリセットして最初から開始
    ///
    /// 【インスペクター設定】
    ///   1. characterSetups に3名のキャラクター設定を登録する
    ///   2. enemy に EnemyController を持つ GameObject を紐付ける
    ///   3. leaderAttribute でパーティリーダーの属性を選ぶ
    /// </summary>
    public class BattleManager : MonoBehaviour
    {
        // -----------------------------------------------------------------
        // インスペクター設定
        // -----------------------------------------------------------------

        [Header("パーティ設定（3名必須）")]

        [Tooltip("キャラクター3名の設定。CharacterData とポジションをセットで登録する。")]
        [SerializeField] private CharacterSetup[] characterSetups = new CharacterSetup[3];

        [Tooltip("全カードがジョーカーだった場合のリーダー属性（フォールバック）")]
        [SerializeField] private Attribute leaderAttribute = Attribute.Fire;

        [Header("敵設定")]

        [Tooltip("シーン上の EnemyController を持つ GameObject")]
        [SerializeField] private EnemyController enemy;

        [Header("デバッグ設定")]

        [Tooltip("ON にすると Start() 時に自動でバトルを開始する")]
        [SerializeField] private bool autoStartOnPlay = true;

        // -----------------------------------------------------------------
        // ランタイム状態
        // -----------------------------------------------------------------

        private Party             _party;
        private BattleCharacter[] _characters;
        private int               _turn;
        private BattleState       _state;

        private enum BattleState { Idle, InProgress, Victory, Defeat }

        // -----------------------------------------------------------------
        // 日本語表示テーブル（Python の ATTR_JP / POS_JP / COMBO_JP に相当）
        // -----------------------------------------------------------------

        private static readonly Dictionary<Attribute, string> AttrJp = new Dictionary<Attribute, string>
        {
            { Attribute.Fire,     "火" },
            { Attribute.Water,    "水" },
            { Attribute.Light,    "光" },
            { Attribute.Typeless, "無" },
        };

        private static readonly Dictionary<Position, string> PosJp = new Dictionary<Position, string>
        {
            { Position.Front, "前衛" },
            { Position.Mid,   "中衛" },
            { Position.Back,  "後衛" },
        };

        private static readonly Dictionary<ComboType, string> ComboJp = new Dictionary<ComboType, string>
        {
            { ComboType.Flash,   "フラッシュ  (全体 x2.5)" },
            { ComboType.Rainbow, "レインボー  (全体 x1.5)" },
            { ComboType.Pair,    "ペア        (同色 x1.2 / 他 x1.0)" },
            { ComboType.None,    "役なし      (全体 x1.0)" },
        };

        // -----------------------------------------------------------------
        // Unity ライフサイクル
        // -----------------------------------------------------------------

        private void Start()
        {
            if (autoStartOnPlay)
                StartBattle();
        }

        private void Update()
        {
            // Space: 1ターン進める
            if (Input.GetKeyDown(KeyCode.Space) && _state == BattleState.InProgress)
                ProcessTurn();

            // R: バトルをリセット
            if (Input.GetKeyDown(KeyCode.R))
                StartBattle();
        }

        // -----------------------------------------------------------------
        // セットアップ
        // -----------------------------------------------------------------

        /// <summary>
        /// バトルを初期化して開始する。
        /// インスペクターの設定から BattleCharacter と Party を生成する。
        /// Python の setup() + ゲームループ開始に相当。
        /// </summary>
        public void StartBattle()
        {
            // バリデーション
            if (characterSetups == null || characterSetups.Length != 3)
            {
                Debug.LogError("[BattleManager] characterSetups に3名分の設定が必要です。");
                return;
            }
            if (enemy == null)
            {
                Debug.LogError("[BattleManager] enemy が未設定です。");
                return;
            }

            // BattleCharacter の生成
            _characters = new BattleCharacter[3];
            for (int i = 0; i < 3; i++)
            {
                var setup = characterSetups[i];
                if (setup.data == null)
                {
                    Debug.LogError($"[BattleManager] characterSetups[{i}].data が null です。");
                    return;
                }
                _characters[i] = new BattleCharacter(setup.data, setup.initialPosition);
            }

            // Party の生成（デッキ構築＆シャッフルもここで行われる）
            _party = new Party(_characters, leaderAttribute);

            // 敵のリセット
            enemy.Initialize();

            _turn  = 0;
            _state = BattleState.InProgress;

            // 初期状態のログ出力
            var sb = new StringBuilder();
            sb.AppendLine("======================================================");
            sb.AppendLine("          プロジェクト・エレメンツ");
            sb.AppendLine("              バトル開始！");
            sb.AppendLine("======================================================");
            sb.AppendLine("[初期編成]");
            foreach (var chara in _characters)
            {
                string attrs = string.Join(" / ", chara.Cards.Select(c => AttrJp[c.attribute]));
                sb.AppendLine($"  {chara.Name} ({PosJp[chara.Position]}): {attrs}");
            }
            sb.AppendLine("[ヒント] Space キーでターンを進める  /  R キーでリセット");
            Debug.Log(sb.ToString());

            LogStatus();
        }

        // -----------------------------------------------------------------
        // ターン処理
        // -----------------------------------------------------------------

        /// <summary>
        /// 1ターン分の全処理を実行する。
        /// Python の process_turn() に相当。
        /// </summary>
        public void ProcessTurn()
        {
            _turn++;
            var sb = new StringBuilder();
            sb.AppendLine("======================================================");
            sb.AppendLine($"  ■ ターン {_turn}");
            sb.AppendLine("======================================================");

            // ── 0. 手札を引く（デッキ切れならリシャッフル）──────────────
            bool reshuffled = _party.DrawHand();
            if (reshuffled)
                sb.AppendLine("  ★ デッキが0枚！ カードをリシャッフルしました。(9枚に戻す)");

            // ── 1. 手札ログ ────────────────────────────────────────────
            sb.AppendLine("\n[手札]");
            var hand = _party.Hand;
            for (int i = 0; i < hand.Count; i++)
            {
                var card  = hand[i];
                string ownerName = GetOwnerName(card);
                sb.AppendLine($"  カード{i + 1}: [{AttrJp[card.attribute]}]  " +
                              $"威力 {card.basePower,4:0}  [所有者: {ownerName}]");
            }

            // ── 2. コンボ判定・ダメージ計算 ─────────────────────────────
            CardData[] playedCards = _party.Hand.ToArray();
            DamageResult result    = ComboEngine.CalculateDamage(
                playedCards, _characters, leaderAttribute);
            ComboResult combo = result.ComboResult;

            sb.AppendLine("\n[コンボ判定]");
            sb.AppendLine($"  変換後属性: {string.Join(" / ", combo.ResolvedAttributes.Select(a => AttrJp[a]))}");
            sb.AppendLine($"  成立役    : {ComboJp[combo.ComboType]}");

            // ── 3. ダメージ内訳ログ ────────────────────────────────────
            sb.AppendLine("\n[ダメージ内訳]");
            float totalDamage = 0f;
            for (int i = 0; i < _characters.Length; i++)
            {
                var   chara = _characters[i];
                float dmg   = result.CharacterDamages[i];
                bool  hasBonus = playedCards.Any(p => chara.Cards.Any(o => o == p));
                string bonusTag = hasBonus ? " ★所有者一致 (+20%)" : "";
                string posLabel = chara.IsAlive ? PosJp[chara.Position] : "戦闘不能";
                sb.AppendLine($"  {chara.Name} ({posLabel}): {dmg,7:F1} ダメージ{bonusTag}");
                totalDamage += dmg;
            }
            sb.AppendLine($"\n  合計ダメージ: {totalDamage:F1}");

            // ── 4. 敵にダメージを適用 ────────────────────────────────────
            enemy.TakeDamage(totalDamage);

            // ── 5. ヘイト蓄積（行動したキャラに +5）─────────────────────
            foreach (var chara in _characters)
                if (chara.IsAlive)
                    HateSystem.AddHate(chara, 5.0f);

            // ── 6. 手札を消費（補充は次ターン開始時）────────────────────
            _party.PlayHand();

            // ── 7. 勝利判定 ──────────────────────────────────────────────
            if (!enemy.IsAlive)
            {
                sb.AppendLine($"\n  [{enemy.EnemyName} の残りHP: {enemy.CurrentHp}/{enemy.MaxHp}]");
                Debug.Log(sb.ToString());
                EndBattle(victory: true);
                return;
            }

            // ── 8. 敵の反撃 ──────────────────────────────────────────────
            sb.AppendLine($"\n[{enemy.EnemyName} の反撃]");
            var aliveChars = _party.AliveCharacters;
            BattleCharacter target = HateSystem.SelectTarget(_characters);

            if (target == null)
            {
                sb.AppendLine("  ターゲットなし（全員戦闘不能）");
            }
            else
            {
                float effHate = HateSystem.GetEffectiveHate(target, aliveChars);
                sb.AppendLine($"  ターゲット: {target.Name}（{PosJp[target.Position]}）" +
                              $"  実効ヘイト={effHate:F1}");
                target.TakeDamage(enemy.AttackPower);
                sb.AppendLine($"  {target.Name} が {enemy.AttackPower} ダメージ！  " +
                              $"HP: {target.CurrentHp}/{target.MaxHp}");
            }

            // ── 9. 敗北判定 ──────────────────────────────────────────────
            if (_party.AliveCharacters.Count == 0)
            {
                Debug.Log(sb.ToString());
                EndBattle(victory: false);
                return;
            }

            // ── 10. 山札残り内訳ログ ──────────────────────────────────────
            sb.AppendLine("\n[山札残り]");
            var deckSummary = _party.GetDeckSummary();
            int deckTotal   = deckSummary.Values.Sum();
            string deckLine = string.Join(" / ",
                _characters.Select(c => $"{c.Name}: {deckSummary.GetValueOrDefault(c.Name, 0)}枚"));
            sb.AppendLine($"  {deckLine}  (合計: {deckTotal}枚)");
            if (_party.DeckCount == 0)
                sb.AppendLine("  ★ 山札が0枚になりました。次ターン開始時にリシャッフルします。");

            Debug.Log(sb.ToString());
            LogStatus();
        }

        // -----------------------------------------------------------------
        // バトル終了
        // -----------------------------------------------------------------

        private void EndBattle(bool victory)
        {
            _state = victory ? BattleState.Victory : BattleState.Defeat;

            LogStatus();

            var sb = new StringBuilder();
            sb.AppendLine("======================================================");
            if (victory)
                sb.AppendLine($"  勝利！ {enemy.EnemyName} を {_turn} ターンで撃破！");
            else
                sb.AppendLine($"  敗北... パーティが全滅しました。({_turn} ターン経過)");
            sb.AppendLine("======================================================");
            sb.AppendLine("[ヒント] R キーでリセット");
            Debug.Log(sb.ToString());
        }

        // -----------------------------------------------------------------
        // ステータスログ（Python の print_status() に相当）
        // -----------------------------------------------------------------

        private void LogStatus()
        {
            var sb = new StringBuilder();
            sb.AppendLine("------------------------------------------------------");
            sb.AppendLine("[パーティ]");
            foreach (var chara in _characters)
            {
                string posLabel = chara.IsAlive ? PosJp[chara.Position] : "戦闘不能";
                string bar      = HpBar(chara.CurrentHp, chara.MaxHp);
                sb.AppendLine($"  {chara.Name,-6} ({posLabel,4}) {bar}");
            }
            sb.AppendLine($"[敵] {enemy.EnemyName}");
            sb.AppendLine($"       {HpBar(enemy.CurrentHp, enemy.MaxHp)}");
            sb.AppendLine("------------------------------------------------------");
            Debug.Log(sb.ToString());
        }

        // -----------------------------------------------------------------
        // 内部ヘルパー
        // -----------------------------------------------------------------

        /// <summary>
        /// 指定した CardData を所持しているキャラクターの名前を返す。
        /// 見つからない場合は "不明" を返す。
        /// </summary>
        private string GetOwnerName(CardData card)
        {
            foreach (var chara in _characters)
                if (chara.Cards.Any(owned => owned == card))
                    return chara.Name;
            return "不明";
        }

        /// <summary>HP バーを文字列で生成する。Python の hp_bar() に相当。</summary>
        private static string HpBar(int current, int maxHp, int width = 20)
        {
            float ratio  = Mathf.Max(0f, (float)current / maxHp);
            int   filled = Mathf.RoundToInt(ratio * width);
            string bar   = new string('#', filled) + new string('.', width - filled);
            return $"[{bar}] {current,4}/{maxHp}";
        }
    }
}
