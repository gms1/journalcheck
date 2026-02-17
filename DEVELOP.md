# Development

## Setup

### Prerequisites

pyenv is not absolutely necessary, but it is recommended
### Install System and Python and dependencies

```bash
./scripts/install.sh
```

Or manually:
```bash
sudo apt-get install libsystemd-dev libsqlite3-dev  # Debian/Ubuntu
sudo dnf install systemd-devel sqlite-devel         # Fedora/RHEL
pyenv install -s # when using pyenv
pyenv local # when using pyenv
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

## Building Python Package

```bash
./scripts/build.sh
```

## Building Debian Package

```bash
./scripts/debian.sh
```
