# Common Ansible Collection

Essential Linux system administration roles.

Only tested on Debian-based systems. Might work on others.

## Roles

- `bashrc` - Configure bashrc.d directory and enable drop-in shell scripts
- `bashrc_aliases` - Install colored prompt and common shell aliases
- `buildtools` - Install common build tools and compilers
- `cron` - Install and manage cron jobs
- `docker` - Install and configure Docker Engine
- `hostname` - Configure system hostname
- `mariadb` - Install and configure MariaDB server
- `nodejs` - Install Node.js and enable package managers via Corepack
- `packages` - Install a list of system packages
- `redis` - Install and configure Redis server
- `restic` - Install restic and autorestic for backups
- `sshd` - Configure SSH daemon with security best practices
- `systemd_timer` - Create systemd service/timer units for scheduled tasks
- `timezone` - Configure system timezone
- `users` - Manage system users and groups

## Modules

- `install_github_release` - Download and install assets from a GitHub repository's releases page

## Installation

```bash
ansible-galaxy collection install git+https://github.com/astappiev/ansible-collection-common.git
```

## License

MIT
