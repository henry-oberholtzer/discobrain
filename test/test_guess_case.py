"""
Port of the MusicBrainz GuessCase test suite.

Original JavaScript test suite:
Copyright (C) 2013-2024 MetaBrainz Foundation and contributors
Source: https://github.com/metabrainz/musicbrainz-server/blob/master/root/static/scripts/tests/GuessCase.js
Licensed under GPL-2.0-or-later.
"""

from __future__ import annotations

import pytest

from discobrain.guess_case import GuessCase, guess_case, guess_sort_name


@pytest.fixture
def gc() -> GuessCase:
    return GuessCase(mode_name="English", keep_uppercased=False, roman=False)


def test_sortname(gc: GuessCase) -> None:
    artist_tests = [
        ("Members Of Mayday", False, "Members Of Mayday"),
        ("The Prodigy & Tom Morello", True, "Prodigy, The & Morello, Tom"),
        ("DJ Shadow", True, "Shadow, DJ"),
    ]
    for inp, person, expected in artist_tests:
        assert guess_sort_name(inp, entity="artist", is_person=person) == expected
        assert gc.entities["artist"].sortname(inp, is_person=person) == expected

    label_tests = [
        ("Da! Heard It Records", "Da! Heard It Records"),
        ("The Cadenza Collection", "Cadenza Collection, The"),
        ("Los Enanos Gigantes", "Enanos Gigantes, Los"),
    ]
    for inp, expected in label_tests:
        assert guess_sort_name(inp, entity="label") == expected
        assert gc.entities["label"].sortname(inp) == expected


def test_artist(gc: GuessCase) -> None:
    tests = [
        ("Members Of Mayday", "Members of Mayday"),
        ("the prodigy & tom morello", "The Prodigy & Tom Morello"),
        (" ", "[unknown]"),
        ("n/a", "[unknown]"),
        ("NONE", "[unknown]"),
        ("unknown", "[unknown]"),
        ("No Artist", "[unknown]"),
        ("Peggy Sue And The Pirates", "Peggy Sue and the Pirates"),
    ]
    for inp, expected in tests:
        assert guess_case(inp, entity="artist", keep_uppercased=False) == expected
        assert gc.entities["artist"].guess(inp) == expected


def test_instrument_and_genre(gc: GuessCase) -> None:
    assert guess_case("This Instrument", entity="instrument") == "this instrument"
    assert gc.entities["instrument"].guess("This Instrument") == "this instrument"
    assert guess_case("Electronic Rock", entity="genre") == "electronic rock"
    assert gc.entities["genre"].guess("Electronic Rock") == "electronic rock"


def test_label(gc: GuessCase) -> None:
    tests = [
        ("da! heard it records", "Da! Heard It Records"),
        (" ", "[unknown]"),
        ("n/a", "[unknown]"),
        ("NONE", "[unknown]"),
        ("unknown", "[unknown]"),
        ("No Label", "[unknown]"),
    ]
    for inp, expected in tests:
        assert guess_case(inp, entity="label", keep_uppercased=False) == expected
        assert gc.entities["label"].guess(inp) == expected


def test_recording(gc: GuessCase) -> None:
    tests = [
        ("ハイタッチ (w/o maaya)", "ハイタッチ (w/o Maaya)"),
        ("ハイタッチ (w／o maaya)", "ハイタッチ (w／o Maaya)"),
        (
            "It'S All Over Y'All, You'Re Done",
            "It's All Over Y'all, You're Done",
        ),
        (
            "Hit 'em 'til they go 'way 'n stuff!",
            "Hit 'Em 'Til They Go 'Way 'n Stuff!",
        ),
    ]
    for inp, expected in tests:
        assert guess_case(inp, entity="recording", keep_uppercased=False) == expected
        assert gc.entities["recording"].guess(inp) == expected


def test_release(gc: GuessCase) -> None:
    assert (
        guess_case(
            "All The Piano Sonatas",
            entity="release",
            mode="English",
            keep_uppercased=False,
        )
        == "All the Piano Sonatas"
    )
    assert (
        guess_case(
            "Todas Las Sonatas Para Piano",
            entity="release",
            mode="Sentence",
            keep_uppercased=False,
        )
        == "Todas las sonatas para piano"
    )


def test_work_casing(gc: GuessCase) -> None:
    tests = [
        (
            "WE LOVE TECHPARA VI",
            "English",
            True,
            True,
            "WE LOVE TECHPARA VI",
        ),
        (
            "WE LOVE TECHPARA VI",
            "English",
            True,
            False,
            "We Love Techpara VI",
        ),
        (
            "WE LOVE TECHPARA VI",
            "English",
            False,
            False,
            "We Love Techpara Vi",
        ),
        (
            "WE LOVE TECHPARA VI",
            "Sentence",
            True,
            False,
            "We love techpara VI",
        ),
        (
            "acte 1, no. 7: chœur: «voyons brigadier»",
            "French",
            False,
            False,
            "Acte 1, no. 7 : Chœur : « Voyons brigadier »",
        ),
        ("La chenille", "French", False, False, "La Chenille"),
        ("Le téléphone", "French", False, False, "Le Téléphone"),
        ("Le tire-bouchon", "French", False, False, "Le Tire-bouchon"),
        ("Les corons", "French", False, False, "Les Corons"),
        ("L'envie", "French", False, False, "L’Envie"),
        ("L’envie", "French", False, False, "L’Envie"),
        (
            "La patience est le courage de la vertu.",
            "French",
            False,
            False,
            "La patience est le courage de la vertu.",
        ),
        (
            "American Way ft. Kelis",
            "English",
            True,
            False,
            "American Way (ft. Kelis)",
        ),
        (
            "Bring It All To Me (f. 50 Cent)",
            "English",
            True,
            False,
            "Bring It All to Me (f. 50 Cent)",
        ),
        (
            "izarın gül gül olmuş",
            "Turkish",
            False,
            False,
            "İzarın Gül Gül Olmuş",
        ),
        (
            "efendim hu nasibim Bu IECELLİ TAKSI\u0307RAT yahu",
            "Turkish",
            False,
            False,
            "Efendim Hu Nasibim Bu Iecelli Taksirat Yahu",
        ),
        (
            "ben De YAZDIM",
            "Turkish",
            False,
            True,
            "Ben de YAZDIM",
        ),
        (
            "ya devlet başa Ya Kuzgun Leşe",
            "Turkish",
            False,
            False,
            "Ya Devlet Başa ya Kuzgun Leşe",
        ),
        (
            "My Favourite Numbers ARE IV, Viii, xIx and mcmxcvi",
            "English",
            True,
            False,
            "My Favourite Numbers Are IV, VIII, XIX and MCMXCVI",
        ),
        (
            "C'est le hautbois d'amour no. cvi",
            "French",
            True,
            False,
            "C'est le hautbois d'amour no. CVI",
        ),
        (
            "My brother is a minor",
            "English",
            False,
            False,
            "My Brother Is a Minor",
        ),
        (
            "Sonata in a minor",
            "English",
            False,
            False,
            "Sonata in A minor",
        ),
        (
            "Sonata in g flat major",
            "English",
            False,
            False,
            "Sonata in G-flat major",
        ),
        (
            "hyphen-minus? hyphen‐maximus!",
            "English",
            False,
            False,
            "Hyphen-Minus? Hyphen‐Maximus!",
        ),
        (
            "Some Song (Club Mix)",
            "English",
            True,
            False,
            "Some Song (club mix)",
        ),
        (
            "mi amor",
            "Sentence",
            True,
            False,
            "Mi amor",
        ),
        (
            "cmxcix + v = miv",
            "English",
            True,
            False,
            "CMXCIX + V = MIV",
        ),
    ]

    for inp, mode, roman, keepupper, expected in tests:
        gc.mode_name = mode
        gc.roman = roman
        gc.keep_uppercased = keepupper
        result = gc.entities["work"].guess(inp)
        assert result == expected, f"Failed work guess on '{inp}' ({mode}, roman={roman}, keepupper={keepupper})"


def test_mbs_bugfixes(gc: GuessCase) -> None:
    gc.keep_uppercased = False
    tests = [
        (
            "Je T’Aime Moi… Non Plus (feat. Miss Kittin)",
            "English",
            "Je T’Aime Moi… Non Plus (feat. Miss Kittin)",
        ),
        (
            "E Pra Sempre Te Amar: Ao Vivo",
            "Sentence",
            "E pra sempre te amar: Ao vivo",
        ),
        (
            "Me Esqueça / No Limite / Desesperadamente Apaixonado",
            "Sentence",
            "Me esqueça / No limite / Desesperadamente apaixonado",
        ),
        (
            "Megablast (Rap Version) (ft. Merlin)",
            "English",
            "Megablast (rap version) (ft. Merlin)",
        ),
        (
            "너 (Techno Version)",
            "English",
            "너 (techno version)",
        ),
        (
            "aka AKA a.k.a. A.K.A. a/k/a A/K/A",
            "English",
            "aka aka a.k.a. a.k.a. a.k.a. a.k.a.",
        ),
        (
            "Stuff aka Stuffy AKA Stuffy Stuff",
            "English",
            "Stuff aka Stuffy aka Stuffy Stuff",
        ),
        (
            "Boy In Da Corner / Fire Ina Hole / Bird Inna De Nest / Rock Di Mexicano",
            "English",
            "Boy in da Corner / Fire ina Hole / Bird inna de Nest / Rock di Mexicano",
        ),
        (
            "We Ready Fe Dem / Santa Fe Express / We Come Fi Rock",
            "English",
            "We Ready fe Dem / Santa Fe Express / We Come fi Rock",
        ),
        (
            "Contagious (The Isley Brothers f/ R. Kelly)",
            "English",
            "Contagious (The Isley Brothers f/ R. Kelly)",
        ),
        (
            "X (extended version, Part 1) (feat. Peter Tosh & Bunny Wailer)",
            "English",
            "X (extended version, Part 1) (feat. Peter Tosh & Bunny Wailer)",
        ),
        (
            "Hold on, I'm Coming",
            "English",
            "Hold On, I'm Coming",
        ),
        (
            "I’ll do something - Johnny’s great band",
            "English",
            "I’ll Do Something - Johnny’s Great Band",
        ),
        (
            "10000 dB Goa Trance",
            "English",
            "10000 dB Goa Trance",
        ),
        (
            "Hey c'Mon Everybody",
            "English",
            "Hey C'mon Everybody",
        ),
        (
            "Hey c'Mon Everybody",
            "French",
            "Hey c'mon everybody",
        ),
        (
            "We Love Techno (Remode)",
            "English",
            "We Love Techno (remode)",
        ),
        (
            "We Love Techno (Stereo)",
            "English",
            "We Love Techno (stereo)",
        ),
        (
            "¿qué No? ¡anda Que No!",
            "Sentence",
            "¿Qué no? ¡Anda que no!",
        ),
        (
            "¿QUÉ NO? ¡ANDA QUE NO!",
            "Sentence",
            "¿Qué no? ¡Anda que no!",
        ),
        (
            "Protect Ya Neck",
            "English",
            "Protect Ya Neck",
        ),
        (
            "Protect Ya Neck",
            "Turkish",
            "Protect ya Neck",
        ),
        (
            "I Love My iPad, My IPod and My Iphone, my iphone!",
            "English",
            "I Love My iPad, My iPod and My iPhone, My iPhone!",
        ),
        (
            "A story of YouTube (youtube edit)",
            "English",
            "A Story of YouTube (YouTube edit)",
        ),
        (
            "Chronic Attention Seeking Inspires the Golden Calf of Self-Centeredness, Just Open Tiktok to Witness Irredeemable Narcissism on Every Profile",
            "English",
            "Chronic Attention Seeking Inspires the Golden Calf of Self-Centeredness, Just Open TikTok to Witness Irredeemable Narcissism on Every Profile",
        ),
        (
            "Stuff with f",
            "English",
            "Stuff With F",
        ),
        (
            "«quoted stuff»",
            "French",
            "« Quoted stuff »",
        ),
        (
            "“quoted stuff”",
            "English",
            "“Quoted Stuff”",
        ),
        (
            "[Unknown] / This track is / [Untitled]",
            "English",
            "[unknown] / This Track Is / [untitled]",
        ),
        (
            "The Best Song (Official Video Mix)",
            "English",
            "The Best Song (official video mix)",
        ),
        (
            "The Best Song (Uncensored Explicit Video)",
            "English",
            "The Best Song (uncensored explicit video)",
        ),
        (
            "Nights in the Studio",
            "English",
            "Nights in the Studio",
        ),
        (
            "Nights (Studio Version)",
            "English",
            "Nights (studio version)",
        ),
        (
            "Still Single",
            "English",
            "Still Single",
        ),
        (
            "Still (Single)",
            "English",
            "Still (single)",
        ),
        (
            "The Best Song (8-Bit Loop Version)",
            "English",
            "The Best Song (8-bit loop version)",
        ),
        (
            "The Best Re-Edit (Someone Famous Re-Edit)",
            "English",
            "The Best Re-Edit (Someone Famous re-edit)",
        ),
        (
            "The Best Re-Edit",
            "English",
            "The Best (re-edit)",
        ),
        (
            "The Best Remaster",
            "English",
            "The Best (remaster)",
        ),
        (
            "The Best Refix",
            "English",
            "The Best (refix)",
        ),
        (
            "The Best OC Remix Song (OC Remix By Stan)",
            "English",
            "The Best OC ReMix Song (OC ReMix by Stan)",
        ),
        (
            "An A Cappella Festival (A Cappella Version)",
            "English",
            "An A Cappella Festival (a cappella version)",
        ),
    ]

    for inp, mode, expected in tests:
        gc.mode_name = mode
        result = gc.entities["work"].guess(inp)
        assert result == expected, f"Failed on '{inp}' with mode {mode}"


def test_vinyl_sizes(gc: GuessCase) -> None:
    gc.mode_name = "English"
    gc.roman = False

    tests = [
        (
            'Testing 7 in, 10in, 12" vinyl sizes in mix titles',
            'Testing 7 In, 10", 12" Vinyl Sizes in Mix Titles',
        ),
        (
            "Fine Day (Mike Koglin 12' mix)",
            'Fine Day (Mike Koglin 12" mix)',
        ),
        (
            'Where Love Lives (12"Classic mix)',
            'Where Love Lives (12" Classic mix)',
        ),
        (
            "7's 10's 12's",
            "7's 10's 12's",
        ),
        (
            "greatest 80's hits",
            "Greatest 80's Hits",
        ),
    ]

    for inp, expected in tests:
        result = gc.entities["track"].guess(inp)
        assert result == expected


def test_no_quote_blocks(gc: GuessCase) -> None:
    gc.mode_name = "English"
    gc.roman = False

    tests = [
        ("Boot ’em Up", "Boot ’Em Up"),
        ("Look, no apostrophes!", "Look, No Apostrophes!"),
        ("Tryin’ To Get To You", "Tryin’ to Get to You"),
    ]

    for inp, expected in tests:
        result = gc.entities["track"].guess(inp)
        assert result == expected


def test_acronym_casing(gc: GuessCase) -> None:
    acronym_tests = [
        ("D.A.V.E.", "D.A.V.E."),
        ("d.a.v.e.", "D.A.V.E."),
        ("D.O.P.", "D.O.P."),
        ("U.S.A.", "U.S.A."),
        ("R.E.M.", "R.E.M."),
        ("D.A.V.E. The Drummer", "D.A.V.E. the Drummer"),
        ("Made in the U.S.A.", "Made in the U.S.A."),
    ]

    for inp, expected in acronym_tests:
        assert guess_case(inp, entity="artist") == expected
        assert guess_case(inp, entity="release") == expected
        assert guess_case(inp, entity="track") == expected
        assert gc.entities["artist"].guess(inp) == expected
        assert gc.entities["release"].guess(inp) == expected
