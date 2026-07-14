import os
import re

from odoo.tests import TransactionCase, tagged

# Statutory-looking numbers that must NEVER appear as literals in executable Python — they belong in
# the rate engine so a Finance Act is a data edit, not a deployment (RATE_ENGINE.md §6).
STATUTORY = [r"\b37000\b", r"\b32000\b", r"0\.0833", r"0\.0975", r"\b600000\b",
             r"\b1200000\b", r"\b2200000\b", r"\b4100000\b", r"\b10000000\b"]
MODULES = ["c2p_payroll_rates", "c2p_l10n_pk_hr_payroll", "c2p_payroll_bpo", "c2p_payroll_import"]


@tagged("post_install", "-at_install")
class TestNoStatutoryLiterals(TransactionCase):
    def test_no_statutory_literals(self):
        here = os.path.dirname(__file__)
        root = os.path.abspath(os.path.join(here, "..", ".."))
        hits = []
        for module in MODULES:
            for folder in ("models", "wizard"):
                d = os.path.join(root, module, folder)
                if not os.path.isdir(d):
                    continue
                for fn in os.listdir(d):
                    if not fn.endswith(".py"):
                        continue
                    for i, line in enumerate(open(os.path.join(d, fn), encoding="utf-8"), 1):
                        code = line.split("#", 1)[0]
                        if code.strip().startswith(('"', "'")):  # skip docstring lines
                            continue
                        for pat in STATUTORY:
                            if re.search(pat, code):
                                hits.append("%s/%s/%s:%d %s" % (module, folder, fn, i, line.strip()))
        self.assertFalse(hits, "Statutory literals found in Python:\n" + "\n".join(hits))
