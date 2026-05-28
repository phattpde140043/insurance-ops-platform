from app.core.permissions import Permission, has_permission


def test_admin_wildcard_grants_all_permissions() -> None:
    assert has_permission(
        (Permission.ADMIN_ALL.value,),
        (Permission.INSURANCE_WRITE.value, Permission.AUDIT_READ.value),
    )


def test_missing_permission_is_denied() -> None:
    assert not has_permission(
        (Permission.INSURANCE_READ.value,),
        (Permission.INSURANCE_WRITE.value,),
    )
