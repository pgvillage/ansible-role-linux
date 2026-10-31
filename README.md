Linux
=========

This role manages all linux tasks for a PgVillage PostgreSQL cluster.
This role is part of PgVillage, which is an opinated PostgreSQL deployment for Virtual Machines.

Requirements
------------

This role aims at using an RPM from the MannemSolutions repo.

Role Variables
--------------

Please see the [API docs](docs/api.md) for a description of all variables,
and [defaults](defaults/main.yml) for their default values.


Dependencies
------------

No dependencies


Example Playbook
----------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

    - hosts: servers
      roles:
         - pgvillage.linux

On EL8, first install a Python that Ansible supports (see [Bootstrap](docs/api.md#bootstrap)):

    - hosts: servers
      gather_facts: false
      tasks:
        - ansible.builtin.include_role:
            name: pgvillage.linux
            tasks_from: bootstrap

License
-------

PostgreSQL

Author Information
------------------

PgVillage is an Open Community.
Main contributor is Nibble-IT.
