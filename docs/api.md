# pgvillage.linux role API

This document describes all variables that can be used to configure the `pgvillage.linux` role.
All defaults are defined in [defaults/main.yml](../defaults/main.yml).

The role:

- creates OS groups and users ([tasks/users.yml](../tasks/users.yml))
- configures package repositories and installs packages for the package manager of the host
  (`apt`, `dnf` or `zypper`), including one or more PostgreSQL versions side by side (`linux_pg_versions`)
- applies OS family specific tasks (if available)
- installs sysstat
- optionally adds all inventory hosts to `/etc/hosts` (poor man's DNS)

## Group based variables

Several variables (`linux_users`, `linux_groups` and `linux_packages`) are hashes keyed by inventory group name.
The custom `bygroup` filter ([filter_plugins/core.py](../filter_plugins/core.py)) flattens such a hash into a
single list, containing only the items of the groups that the current host is a member of (`group_names`).
Package names in `linux_packages` are deduplicated. User and group definitions in `linux_users` and
`linux_groups` are dictionaries, so they are returned without deduplication; definitions repeated across
matching inventory groups remain in the list.

The default PgVillage groups are:

| Group        | Purpose                                                        |
|--------------|----------------------------------------------------------------|
| `hacluster`  | PostgreSQL database servers (Stolon, etcd, WAL-G, pgbouncer, ...) |
| `backup`     | Backup servers (MinIO)                                         |
| `router`     | Routers (HAProxy, keepalived, pgroute66)                       |
| `localhosts` | The Ansible controller (chainsmith)                            |

Example:

```yaml
linux_users:
  hacluster:
    - name: postgres
      system: true
  backup:
    - name: minio
      system: true
```

A host in the `hacluster` group gets the `postgres` user, a host in the `backup` group gets the `minio` user,
and a host in both groups gets both.

## Version specific variables

The custom `pg_versioned` filter ([filter_plugins/core.py](../filter_plugins/core.py)) renders a list of templates
once for every PostgreSQL version in a list of versions, and returns all results as a single list.
In strings `{version}` is replaced by the version (e.g. `17` or `9.6`) and `{short}` by the version without dots
(e.g. `17` or `96`). Dicts and lists are rendered recursively, so it works for package names as well as repository
definitions. The role uses it to derive `linux_packages` from `_linux_pg_packages` and `linux_public_repos` from
`_linux_pg_repos`.

When overriding `linux_packages` or `linux_public_repos`, the filter can be used to keep installing all versions in
`linux_pg_versions`. Example:

```yaml
linux_pg_versions: ["16", "17"]
linux_packages:
  hacluster: "{{ ['postgresql{short}-server', 'postgresql{short}-contrib'] | pg_versioned(linux_pg_versions) }}"
```

Results in `postgresql16-server`, `postgresql16-contrib`, `postgresql17-server` and `postgresql17-contrib`
for hosts in the `hacluster` group.

## Variables

### General

#### `linux_pg_version`

- **Type:** string
- **Default:** `"17"`

The primary PostgreSQL major version (e.g. `"16"`, `"17"`), kept for backwards compatibility and for roles that
need a single version. Within this role it is only used as the default for `linux_pg_versions`.

#### `linux_pg_versions`

- **Type:** list of strings
- **Default:** `["{{ linux_pg_version }}"]`

All PostgreSQL major versions to install side by side (e.g. `["16", "17"]` during a major upgrade).
Used to derive the PostgreSQL package names (see `_linux_pg_packages`) and the version specific PGDG repositories
(see `_linux_pg_repos`) to configure. Must be a non-empty list; the role fails otherwise.

### Users and groups

#### `linux_users`

- **Type:** dict of lists (keyed by inventory group)
- **Default:**

| Group       | Users                                                                       |
|-------------|-----------------------------------------------------------------------------|
| `hacluster` | `postgres` (bash), `pgbouncer` (bash), `avchecker`, `pgquartz`, `pgfga`, `pgroute66` |
| `backup`    | `minio`                                                                     |
| `router`    | `haproxy`, `keepalived`, `pgroute66`                                        |

All default users are system users.

OS users to create, per inventory group.
Every item is passed as-is to
[`ansible.builtin.user`](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/user_module.html),
so any option of that module (`uid`, `shell`, `home`, ...) can be set.

#### `linux_groups`

- **Type:** dict of lists (keyed by inventory group)
- **Default:**

| Group       | Groups      |
|-------------|-------------|
| `hacluster` | `postgres`  |
| `backup`    | `minio`     |
| `router`    | `pgroute66` |

All default groups are system groups.

OS groups to create, per inventory group. Groups are created before users.
Every item is passed as-is to
[`ansible.builtin.group`](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/group_module.html),
so any option of that module (`gid`, `system`, ...) can be set.

### Packages

#### `linux_package_state`

- **Type:** string (`present` or `latest`)
- **Default:** `present`

State of the packages to install. When set to `latest`, all packages on the system are upgraded as well.

#### `linux_packages`

- **Type:** dict of lists (keyed by inventory group)
- **Default:** `_linux_packages.default` with `_linux_packages[ansible_facts.pkg_mgr]` and the PostgreSQL packages
  from `_linux_pg_packages` appended

Packages to install, per inventory group.
By default this is the `default` set of `_linux_packages`, with the set for the package manager of the host
(`apt`, `dnf` or `zypper`) appended per group, plus the PostgreSQL packages (`_linux_pg_packages`) for every version
in `linux_pg_versions` appended to the `hacluster` group.

#### `_linux_packages` (internal)

- **Type:** dict (package manager → inventory group → list of packages)

Package lists per package manager and per inventory group, used to derive `linux_packages`.
Override `linux_packages` rather than this variable.

| Package manager | Group        | Packages |
|-----------------|--------------|----------|
| `default`       | `hacluster`  | `stolon`, `wal-g-pg`, `etcd` |
| `default`       | `backup`     | `minio` |
| `default`       | `router`     | `keepalived`, `haproxy`, `pgroute66` |
| `default`       | `localhosts` | `chainsmith` |
| `apt`           | `hacluster`  | `acl` |
| `apt`           | `backup`     | `acl` |
| `dnf`           | `hacluster`  | `glibc-all-langpacks`, `langpacks-en` |
| `zypper`        | `hacluster`  | `glibc-locale`, `glibc-locale-base`, `openssl` |

On Debian based systems, the role prevents the packaging system from automatically starting services and creating
a default PostgreSQL cluster, and stops / disables `postgresql.service` when PostgreSQL packages are installed.

#### `_linux_pg_packages` (internal)

- **Type:** dict (package manager → list of package name templates)

PostgreSQL packages per package manager, added to the `hacluster` group of `linux_packages` once for every version
in `linux_pg_versions`. Package managers without an entry use the `default` list.
`{version}` is replaced by the version (e.g. `9.6`) and `{short}` by the version without dots (e.g. `96`).
Override `linux_packages` rather than this variable.

| Package manager | Packages |
|-----------------|----------|
| `default`       | `postgresql{short}`, `postgresql{short}-server`, `-contrib`, `-devel`, `-plpython3` |
| `apt`           | `postgresql-{version}` |

### Repositories

#### `linux_public_repos`

- **Type:** list of dicts
- **Default:** `_linux_public_repos[ansible_facts.pkg_mgr]` plus `_linux_pg_repos[ansible_facts.pkg_mgr]` for every
  version in `linux_pg_versions`

Package repositories to configure, selected from `_linux_public_repos` by the package manager of the host.
Items are passed as-is to
[`ansible.builtin.yum_repository`](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/yum_repository_module.html) (dnf) or
[`community.general.zypper_repository`](https://docs.ansible.com/ansible/latest/collections/community/general/zypper_repository_module.html) (zypper).
For apt only the `repo` field is used (prefixed with `deb `) by
[`ansible.builtin.apt_repository`](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/apt_repository_module.html).
The version specific PGDG repositories from `_linux_pg_repos` are appended for every version in `linux_pg_versions`.

#### `_linux_public_repos` (internal)

- **Type:** dict (package manager → list of repository definitions)

Repository definitions per package manager. Override `linux_public_repos` rather than this variable.

| Package manager | Repositories |
|-----------------|--------------|
| `dnf`           | PgVillage, `pgdg-common`, `pgdg-rhel-extras`, `epel` |
| `zypper`        | PgVillage, `pgdg-common`, `pgdg-rhel-extras` |
| `apt`           | PgVillage, `pgdg` (serves all PostgreSQL versions) |

#### `_linux_pg_repos` (internal)

- **Type:** dict (package manager → list of repository definition templates)

Version specific PGDG repositories per package manager, added to `linux_public_repos` once for every version in
`linux_pg_versions`. `{version}` is replaced by the version (e.g. `17`).
Override `linux_public_repos` rather than this variable.

| Package manager | Repositories |
|-----------------|--------------|
| `dnf`           | `pgdg{version}` |
| `zypper`        | `pgdg{version}` |

apt has no entry, because apt.postgresql.org serves all versions from one repository.

#### `linux_architecture`

- **Type:** string
- **Default:** `"{{ linux_architectures[ansible_facts.architecture] }}"`

Debian style architecture name (`amd64` / `arm64`) of the host, derived from `ansible_facts.architecture`
using the `linux_architectures` mapping in [vars/main.yml](../vars/main.yml). Used in the apt repository definitions.

#### `linux_disable_gpg_check`

- **Type:** boolean (as string)
- **Default:** `"false"`

Disable GPG signature checking when installing packages (dnf and zypper only).

#### `linux_gpg_keys`

- **Type:** dict (package manager → key name → url)

GPG keys per package manager:

- `dnf`: PGDG keys per architecture (`x86_64`, `aarch64`, as reported by `ansible_facts.architecture`) and the
  `epel` key, referenced by the dnf repositories in `_linux_public_repos`
- `zypper`: PGDG keys per SLES version (`sles15`, `sles16`), referenced by `linux_zypper_gpg_keys`
- `apt`: all keys (`postgresql`, `pgvillage`) are downloaded to `/etc/apt/keyrings/<key>.asc` and referenced with
  `signed-by` in the apt repositories

#### `linux_zypper_gpg_keys`

- **Type:** list of strings
- **Default:** `["{{ linux_gpg_keys.zypper.sles16 }}"]`

List of GPG keys (urls or paths) to import into the rpm keyring on zypper based systems.

### Red Hat subscription management

#### `linux_rh_subscription`

- **Type:** dict
- **Default:** `{}`

Red Hat subscription (Satellite) configuration for dnf based systems.
When set, the system is registered with
[`community.general.redhat_subscription`](https://docs.ansible.com/ansible/latest/collections/community/general/redhat_subscription_module.html)
using `activationkey`, `org_id` and `pool_ids`, `linux_rh_misc_repo` is configured (if set) and subscriptions are
(auto-)attached. Leave empty (`{}`) to skip Red Hat subscription management.

Example:

```yaml
linux_rh_subscription:
  activationkey: "ORG1"
  org_id: "ORG1"
  pool_ids: []
```

#### `linux_rh_misc_repo`

- **Type:** dict
- **Default:** `{}`

Additional (Satellite hosted) yum repository to configure when `linux_rh_subscription` is set.
All keys in the example below are required. Leave empty (`{}`) to skip.

Example:

```yaml
linux_rh_misc_repo:
  name: "Rhel_Misc"
  description: "Rhel Misc repository"
  baseurl: "http://satellite.example.org/pulp/content/ORG1/Library/custom/rhel_misc/rhel_misc/"
  enabled: "true"
  gpgcheck: "true"
  gpgkey: file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release
  sslverify: "true"
  sslcacert: /etc/rhsm/ca/katello-server-ca.pem
  sslclientkey: /etc/pki/entitlement/8675925567367701300-key.pem
  sslclientcert: /etc/pki/entitlement/8675925567367701300.pem
  priority: "20"
```

### Name resolution

#### `linux_poor_mans_dns`

- **Type:** boolean
- **Default:** `false`

When enabled, an entry (ip, fqdn and hostname) is added to `/etc/hosts` for all hosts in the inventory, except the
hosts in the `localhosts` group.
Note that the task is delegated to localhost, so the entries are added to `/etc/hosts` on the Ansible controller.
