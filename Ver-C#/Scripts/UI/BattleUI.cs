using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using ProjectElements.Data;
using ProjectElements.Core;

namespace ProjectElements.UI
{
    public class BattleUI : MonoBehaviour
    {
        public event Action<CardData[]> OnSelectionComplete;

        private const int HandSize = 3;

        private GameObject _panel;
        private readonly Button[]   _buttons      = new Button[HandSize];
        private readonly Image[]    _buttonImages  = new Image[HandSize];
        private readonly Text[]     _buttonTexts   = new Text[HandSize];
        private readonly CardData[] _currentHand  = new CardData[HandSize];
        private readonly List<int>   _selectedIndices  = new List<int>();

        private static readonly Dictionary<Element, string> ElementJp =
            new Dictionary<Element, string>
            {
                { Element.Fire,     "炎" },
                { Element.Water,    "水" },
                { Element.Light,    "光" },
                { Element.Typeless, "無" },
            };

        private void Awake() => BuildUI();

        private void BuildUI()
        {
            var canvasGO = new GameObject("BattleCanvas");
            var canvas = canvasGO.AddComponent<Canvas>();
            canvas.renderMode   = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 10;
            canvasGO.AddComponent<CanvasScaler>();
            canvasGO.AddComponent<GraphicRaycaster>();

            var panelGO  = new GameObject("CardHandPanel");
            panelGO.transform.SetParent(canvasGO.transform, false);
            var panelImg = panelGO.AddComponent<Image>();
            panelImg.color = new Color(0f, 0f, 0f, 0.6f);
            var panelRect  = panelGO.GetComponent<RectTransform>();
            panelRect.anchorMin = new Vector2(0f, 0f);
            panelRect.anchorMax = new Vector2(1f, 0.25f);
            panelRect.offsetMin = Vector2.zero;
            panelRect.offsetMax = Vector2.zero;
            _panel = panelGO;

            float[] centers = { 0.2f, 0.5f, 0.8f };
            const float half = 0.13f;

            for (int i = 0; i < HandSize; i++)
            {
                var btnGO = new GameObject($"CardButton_{i}");
                btnGO.transform.SetParent(panelGO.transform, false);

                var img = btnGO.AddComponent<Image>();
                img.color        = Color.white;
                _buttonImages[i] = img;

                var btn    = btnGO.AddComponent<Button>();
                _buttons[i] = btn;

                var rect = btnGO.GetComponent<RectTransform>();
                rect.anchorMin = new Vector2(centers[i] - half, 0.05f);
                rect.anchorMax = new Vector2(centers[i] + half, 0.95f);
                rect.offsetMin = Vector2.zero;
                rect.offsetMax = Vector2.zero;

                var labelGO = new GameObject("Label");
                labelGO.transform.SetParent(btnGO.transform, false);
                var text = labelGO.AddComponent<Text>();
                var font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf")
                        ?? Resources.GetBuiltinResource<Font>("Arial.ttf");
                if (font == null)
                    Debug.LogWarning("[BattleUI] ビルトインフォントの取得に失敗しました。Unityのデフォルトフォントを使用します。");
                text.font = font;
                text.alignment            = TextAnchor.MiddleCenter;
                text.color                = Color.black;
                text.resizeTextForBestFit = true;
                text.resizeTextMinSize    = 10;
                text.resizeTextMaxSize    = 24;
                _buttonTexts[i] = text;
                var labelRect = labelGO.GetComponent<RectTransform>();
                labelRect.anchorMin = Vector2.zero;
                labelRect.anchorMax = Vector2.one;
                labelRect.offsetMin = new Vector2(4f,   4f);
                labelRect.offsetMax = new Vector2(-4f, -4f);

                int captured = i;
                btn.onClick.AddListener(() => HandleCardClick(captured));
            }

            panelGO.SetActive(false);
        }

        public void ShowHand(IReadOnlyList<CardData> hand)
        {
            if (hand == null || hand.Count < HandSize)
            {
                Debug.LogError($"[BattleUI] ShowHand requires {HandSize} cards.");
                return;
            }

            for (int i = 0; i < HandSize; i++) _currentHand[i] = hand[i];
            _selectedIndices.Clear();

            for (int i = 0; i < HandSize; i++)
            {
                var card = _currentHand[i];
                _buttonTexts[i].text     = $"{GetElementLabel(card.element)}\n{card.cardName}\n威力: {card.basePower:0}";
                _buttons[i].interactable = true;
                _buttonImages[i].color   = Color.white;
            }
            _panel.SetActive(true);
        }

        private static string GetElementLabel(Element element) =>
            ElementJp.TryGetValue(element, out var label) ? label : element.ToString();

        public void ResetSelection()
        {
            _selectedIndices.Clear();
            for (int i = 0; i < HandSize; i++)
            {
                _buttons[i].interactable = true;
                _buttonImages[i].color   = Color.white;
            }
        }

        private void HandleCardClick(int index)
        {
            if (_selectedIndices.Contains(index))
            {
                _selectedIndices.Remove(index);
                _buttonImages[index].color = Color.white;
                return;
            }

            _selectedIndices.Add(index);
            _buttonImages[index].color = Color.yellow;

            if (_selectedIndices.Count < 3) return;

            foreach (var btn in _buttons) btn.interactable = false;

            var selected = new CardData[3];
            for (int i = 0; i < 3; i++) selected[i] = _currentHand[_selectedIndices[i]];
            OnSelectionComplete?.Invoke(selected);
        }
    }
}
