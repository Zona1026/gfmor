from core.staff_names import canonical_staff_name, staff_name_variants


def test_canonical_staff_name_maps_legacy_name():
    assert canonical_staff_name("火腿") == "江子暢"


def test_canonical_staff_name_keeps_current_name():
    assert canonical_staff_name("江子暢") == "江子暢"


def test_canonical_staff_name_treats_blank_as_empty():
    assert canonical_staff_name("  ") is None
    assert canonical_staff_name(None) is None


def test_staff_name_variants_include_legacy_aliases():
    assert set(staff_name_variants("江子暢")) == {"火腿", "江子暢"}
