# iiPythonx / USPS

A CLI for tracking packages from USPS.

### Installation

```sh
uv pip install git+https://github.com/iiPythonx/usps
```

### Usage

Get the tracking information for a package:
```sh
usps track <tracking number>
```

Add a tracking number to your package list:
```sh
usps add <tracking number>
```

Remove a tracking number from your package list:
```sh
usps remove <tracking number>
```

Show all your current packages:
```sh
usps track
```

### Inspiration

I tried to make a basic web scraper for the USPS website months ago, only to find out that its security is crazy.  
Instead of trying to reverse engineer their client, this script generates cookies using Selenium and then uses requests
and BeautifulSoup to make the request and parse the result.
