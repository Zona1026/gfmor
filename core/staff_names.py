STAFF_NAME_ALIASES = {
    "火腿": "江子暢",
}


def canonical_staff_name(name):
    if name is None:
        return None
    stripped = str(name).strip()
    if not stripped:
        return None
    return STAFF_NAME_ALIASES.get(stripped, stripped)


def staff_name_variants(name):
    canonical = canonical_staff_name(name)
    if not canonical:
        return []
    variants = {canonical}
    variants.update(alias for alias, target in STAFF_NAME_ALIASES.items() if target == canonical)
    return list(variants)
