"""Pure, dependency-free cell transforms for the import engine.

The whole point of G1 (docs/GAP_REGISTER.md) is that the ugly client files import through mapping
PROFILES alone, with zero per-file Python. These transforms are the vocabulary a profile composes;
if a new file needs a new transform it is added here once, generically — never special-cased per file.
Kept pure so they are unit-testable without Odoo (see the module tests / scripts).
"""
import re


def t_strip(value, arg=None):
    return value.strip() if isinstance(value, str) else value


def t_number_from_text(value, arg=None):
    """'1,500' -> 1500.0 ; '-' / '' / None -> 0.0 ; 24 -> 24.0. Dashes and blanks are zeros."""
    if value in (None, "", "-", "—"):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[,\s]", "", str(value))
    if cleaned in ("", "-", "—"):
        return 0.0
    return float(cleaned)


def t_strip_currency_prefix(value, arg=None):
    """'Rs. 200,000' -> 200000.0 ; 'PKR 37,000' -> 37000.0 ; handles bare numbers too."""
    if value in (None, "", "-", "—"):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    # Drop thousands separators, then take the first numeric token — so the '.' in 'Rs.' is ignored.
    s = str(value).replace(",", "")
    m = re.search(r"\d+(?:\.\d+)?", s)
    return float(m.group()) if m else 0.0


def t_yn_to_bool(value, arg=None):
    return str(value).strip().lower() in ("y", "yes", "true", "1", "member")


def t_clean_iban(value, arg=None):
    """'PK90 HABB 3758 1325 5509 8059' -> 'PK90HABB3758132555098059'."""
    return re.sub(r"\s+", "", str(value)).upper() if value else value


def t_date_dmy(value, arg=None):
    """'15/06/2026' or '15-06-2026' -> '2026-06-15'. Passes through date objects."""
    if not value:
        return None
    if not isinstance(value, str):
        return value
    m = re.match(r"\s*(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\s*$", value)
    if not m:
        return value
    d, mo, y = m.groups()
    y = ("20" + y) if len(y) == 2 else y
    return "%s-%s-%s" % (y, mo.zfill(2), d.zfill(2))


def t_constant(value, arg=None):
    """Ignore the cell; return the profile-supplied constant (e.g. a period '2026-06')."""
    return arg


def t_prefix(value, arg=None):
    """Employee-code normaliser: '007' + prefix 'ITM-' -> 'ITM-007'. Skips if already prefixed."""
    s = str(value).strip()
    if not arg or s.startswith(arg):
        return s
    return "%s%s" % (arg, s)


TRANSFORMS = {
    "strip": t_strip,
    "number_from_text": t_number_from_text,
    "strip_currency_prefix": t_strip_currency_prefix,
    "yn_to_bool": t_yn_to_bool,
    "clean_iban": t_clean_iban,
    "date_dmy": t_date_dmy,
    "constant": t_constant,
    "prefix": t_prefix,
}


def apply_transform(name, value, arg=None):
    fn = TRANSFORMS.get(name or "strip")
    if fn is None:
        raise ValueError("Unknown transform: %s" % name)
    return fn(value, arg)
