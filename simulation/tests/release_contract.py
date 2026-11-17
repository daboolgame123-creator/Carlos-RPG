"""Independent current-writer oracle; frozen readers are tested separately."""
CURRENT_VERSION = (45, 71)


def assert_current_version(schema, rules):
    assert (schema, rules) == CURRENT_VERSION
