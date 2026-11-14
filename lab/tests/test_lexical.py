from neuron_lab.lexical import BM25, content_words, overlap_share, tokenize


def test_tokenize_lowercases_and_splits_on_anything_not_alphanumeric():
    assert tokenize("Set-up GitHub Actions: CI/CD v2!") == [
        "set",
        "up",
        "github",
        "actions",
        "ci",
        "cd",
        "v2",
    ]


def test_the_document_holding_the_query_term_ranks_first():
    index = BM25(["deploy a container to production", "write unit tests for a parser"])

    scores = index.scores("unit tests")

    assert scores[1] > scores[0]
    assert scores[0] == 0.0


def test_a_rare_term_outweighs_a_common_one():
    index = BM25(
        [
            "review the pull request",
            "review the database migration",
            "review the release notes",
        ]
    )

    common = index.scores("review")
    rare = index.scores("migration")

    assert rare[1] > common[1]


def test_a_shorter_document_scores_higher_for_the_same_single_hit():
    index = BM25(["cache", "cache " + "filler " * 30])

    scores = index.scores("cache")

    assert scores[0] > scores[1]


def test_a_query_with_no_known_term_scores_zero_everywhere():
    index = BM25(["alpha beta", "gamma delta"])

    assert index.scores("omega") == [0.0, 0.0]
    assert index.scores("") == [0.0, 0.0]


def test_content_words_drop_function_words_and_keep_the_rest_in_order():
    assert content_words("Set up the pipeline for a pull request") == [
        "set",
        "pipeline",
        "pull",
        "request",
    ]


def test_overlap_share_is_the_share_of_distinct_content_words_found_in_the_reference():
    reference = "Set up or improve CI/CD pipelines and quality gates"

    assert overlap_share("improve the quality of the gates", reference) == 1.0
    assert overlap_share("improve improve the checkout", reference) == 0.5
    assert overlap_share("rewrite the checkout", reference) == 0.0


def test_overlap_share_of_a_query_without_content_words_is_zero():
    assert overlap_share("the of and", "anything at all") == 0.0
