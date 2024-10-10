# iiPythonx / USPS

A CLI for tracking packages from USPS (with crude support for UPS packages).

### Installation

```sh
uv pip install usps-cli

# or, install from dev:
uv pip install git+https://github.com/iiPythonx/usps
```

### Usage

> [!IMPORTANT]  
> For UPS packages, USPS-cli only support the `1Z` version of UPS tracking numbers right now.

Get the tracking information for a package:
```sh
usps track 9400100000000000000000
```

Add a tracking number to your package list:
```sh
usps add 9400100000000000000000
```

Remove a tracking number from your package list:
```sh
usps remove 9400100000000000000000
```

Show all your current packages:
```sh
usps track
```

Add a name to a package:
```sh
$ usps name 9400100000000000000000 "Amazon Package"

# If you don't specify name, it will prompt for one.
$ usps name 9400100000000000000000
Choose a package name: Amazon Package
```

Remove the name from a package:
```sh
usps name --erase 9400100000000000000000
```

For more details, run `usps --help`.  

### Requirements

> [!NOTE]  
> If you **only** plan to track **UPS** packages, you can skip installing a selenium driver.

Since this package uses selenium for challenge solving, you'll need to install a [Firefox-compatible browser](https://www.mozilla.org/en-US/firefox) and [geckodriver](https://github.com/mozilla/geckodriver/releases).  
Feel free to modify the code to use Chromium instead if you prefer it.

If you're on Arch: `sudo pacman -S firefox geckodriver`,

### Inspiration

I tried to make a basic web scraper for the USPS website months ago, only to find out that its security is crazy.  
Instead of trying to reverse engineer their client, I made this instead.

How it works:
- Selenium goes to the USPS tracking website, completing the JS challenge and saving the cookies
- This client saves that request data to a JSON file for reuse (speeds up the client dramatically)
- Next, requests pulls the page from USPS using our saved cookies and parses it with BeautifulSoup
- Apply some basic scraping and there you go, a USPS tracking client
