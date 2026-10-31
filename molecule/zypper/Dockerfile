# openSUSE Leap 16.0 with systemd and python, so it can run as a systemd container managed by Ansible.
# The PgVillage and PGDG zypper repositories only publish x86_64 packages for Leap 16.0, hence the platform.
FROM --platform=linux/amd64 docker.io/opensuse/leap:16.0
RUN zypper --non-interactive install --no-recommends systemd python3 shadow sudo \
    && zypper clean --all
CMD ["/usr/lib/systemd/systemd"]
