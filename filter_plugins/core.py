"""Custom Jinja2 filters for the pgvillage.linux role."""


def filter_by_group(grouped_lists, groups):
    """Flatten a hash of lists keyed by inventory group into a single list.

    Only the lists of the groups in ``groups`` (typically ``group_names``) are included.
    Hashable items (e.g. package names) are deduplicated; the order of the result is not guaranteed.
    If any item is unhashable (e.g. user or group definitions, which are dicts), all items are returned
    in order and without deduplication.

    Exposed as the ``bygroup`` filter, e.g. ``linux_packages | bygroup(group_names)``.

    :param grouped_lists: dict of inventory group name to list of items
    :param groups: list of inventory group names the host is a member of
    :return: list of items of the matching groups
    """
    # Use a set to make uniue, and then convert to list again to make it json_serializable
    try:
        return list({ value for key, values in grouped_lists.items() if key in groups for value in values })
    except TypeError:
        return [ value for key, values in grouped_lists.items() if key in groups for value in values ]


def pg_versioned(templates, versions):
    """Render every template once for every PostgreSQL version.

    In strings ``{version}`` is replaced by the version (e.g. ``17`` or ``9.6``) and ``{short}`` by the version
    without dots (e.g. ``17`` or ``96``). Dicts and lists are rendered recursively, so this works for package
    names as well as repository definitions. Other values are returned as-is.

    Exposed as the ``pg_versioned`` filter, e.g.
    ``['postgresql{short}-server'] | pg_versioned(['16', '17'])`` returns
    ``['postgresql16-server', 'postgresql17-server']``.

    :param templates: list of templates (strings, dicts or lists)
    :param versions: list of PostgreSQL versions; non-string versions are converted with ``str()``
    :return: list with all rendered templates for the first version, followed by those for the next version, etc.
    """
    def render(obj, version):
        if isinstance(obj, str):
            return obj.replace('{version}', version).replace('{short}', version.replace('.', ''))
        if isinstance(obj, dict):
            return { key: render(value, version) for key, value in obj.items() }
        if isinstance(obj, list):
            return [ render(value, version) for value in obj ]
        return obj
    return [ render(template, str(version)) for version in versions for template in templates ]


class FilterModule(object):
    """Register the custom filters of the pgvillage.linux role with Ansible."""

    def filters(self):
        """Return the mapping of filter names to filter functions."""
        return {
            'bygroup': filter_by_group,
            'pg_versioned': pg_versioned,
        }
