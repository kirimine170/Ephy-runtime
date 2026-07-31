from packages.eval_core.style import assess_response_style


def test_response_style_accepts_short_natural_japanese() -> None:
    assessment = assess_response_style("主な原因はpromptの応答契約です．まず既定の長さと構造を調整します．")

    assert assessment.passed is True
    assert assessment.violations == ()


def test_response_style_detects_ai_slop_patterns() -> None:
    answer = """# 概要
## 詳細
### まとめ
#### 結論
- 一つ目。
- 二つ目。
- 三つ目。
- 四つ目。
- 五つ目。
- 六つ目。
- 七つ目。
"""

    assessment = assess_response_style(answer, max_characters=70)

    assert assessment.passed is False
    assert "answer_too_long" in assessment.violations
    assert "too_many_bullets" in assessment.violations
    assert "too_many_headings" in assessment.violations


def test_response_style_ignores_code_block_length_and_structure() -> None:
    answer = "説明は短く記述します．\n\n```text\n# 見出し\n- 項目\n" + ("x" * 2000) + "\n```"

    assessment = assess_response_style(answer)

    assert assessment.passed is True
