# Development

## Setup

### Prerequisites

Install system dependencies:
```bash
sudo apt-get install libsystemd-dev libsqlite3-dev  # Debian/Ubuntu
sudo dnf install systemd-devel sqlite-devel         # Fedora/RHEL
```

### Install Python and dependencies

```bash
./scripts/install.sh
```

Or manually:
```bash
pyenv install
pyenv local
pip install -e .
pip install -r requirements.txt
```

## Linting

```bash
./scripts/lint.sh
```

## Testing

```bash
./scripts/test.sh
```

View HTML coverage report: `htmlcov/index.html`

## Building Debian Package

```bash
./scripts/debian.sh
```
