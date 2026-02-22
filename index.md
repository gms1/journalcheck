# journalcheck

Welcome to **journalcheck**

[Project Homepage](https://github.com/gms1/journalcheck)

## Offical APT reopository for **journalcheck**

To add this repsitory and install **journalcheck** please follow these steps:

```bash
# add gpg key
curl -sS https://gms1.github.io/journalcheck/apt/public.gpg | sudo gpg --dearmor -o /usr/share/keyrings/journalcheck.gpg

# add APT repository
echo "deb [signed-by=/usr/share/keyrings/journalcheck.gpg] https://gms1.github.io/journalcheck/apt ./" | sudo tee /etc/apt/sources.list.d/journalcheck.list

# install journalcheck
sudo apt update
sudo apt install journalcheck
```

