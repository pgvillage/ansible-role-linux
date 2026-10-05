def filter_by_group(grouped_lists, groups):
    # Use a set to make uniue, and then convert to list again to make it json_serializable
    try:
        return list({ value for key, values in grouped_lists.items() if key in groups for value in values })
    except TypeError:
        return [ value for key, values in grouped_lists.items() if key in groups for value in values ]

def pg_versioned(templates, versions):
    # Render every template once for every PostgreSQL version.
    # In strings '{version}' is replaced by the version (e.g. 17 or 9.6) and '{short}' by the version without dots (e.g. 17 or 96).
    # Dicts and lists are rendered recursively, so this works for package names as well as repository definitions.
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
    def filters(self):
        return {
            'bygroup': filter_by_group,
            'pg_versioned': pg_versioned,
        }
