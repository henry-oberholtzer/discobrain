import pytest

from discobrain.utils import most_common_script

@pytest.mark.parametrize("text,script", [(
    "This is a sentence in a latin script",
    "Latn"
),
(
    "Это предложение, написанное кириллицей.",
    "Cyrl"
),
(
    "\u067E",
    "Arab"
),
(
    "\u067E\u067EЭ",
    "Arab"
)
])
def test_most_common_script(text: str, script: str):
    assert most_common_script(text) == script
