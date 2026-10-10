"""The per-participant quality screen (memo 0003) gives a reason for every exclusion."""

from __future__ import annotations

import pandas as pd

from neurographx.m1_ingestion import metadata as md
from neurographx.m1_ingestion import screening

RULES = {"qc_rater_1": ["OK"], "qc_func_rater_2": ["OK", "maybe"]}


def reasons(**cells):
    return screening.exclusion_reasons(pd.Series(cells), RULES)


def test_passing_participant_has_no_reasons():
    assert reasons(FILE_ID="NYU_0050001", qc_rater_1="OK", qc_func_rater_2="maybe") == []


def test_values_are_compared_without_surrounding_spaces():
    assert reasons(qc_rater_1=" OK ", qc_func_rater_2="OK") == []


def test_each_failed_rule_is_named():
    out = reasons(FILE_ID="no_filename", qc_rater_1="fail", qc_func_rater_2=None)
    assert out == [
        "no preprocessed data in ABIDE (FILE_ID is no_filename)",
        "qc_rater_1 is fail (accepted: OK)",
        "qc_func_rater_2 is missing (accepted: OK, maybe)",
    ]


def test_a_rule_whose_column_is_absent_is_skipped():
    assert reasons(qc_rater_1="OK") == []


def test_rules_are_read_from_the_config():
    rules = screening.rater_criteria()
    assert set(rules) == set(md.QC_ACCEPTED)
    assert all(isinstance(v, list) and v for v in rules.values())
