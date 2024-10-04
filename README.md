# iiPythonx / USPS

A CLI for tracking packages from USPS.

### Installation

```sh
uv pip install usps-cli

# or, install from dev:
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

Add a name to a package:
```sh
usps name <tracking number> [name]

# If you don't specify name, it will prompt for one.
$ usps name <tracking number>
Enter name: ...

# You can remove a name as well:
usps name --erase <tracking number>
```

### Requirements

Since this package uses selenium for challenge solving, you'll need to install a [Firefox-compatible browser](https://www.mozilla.org/en-US/firefox) and [geckodriver](https://github.com/mozilla/geckodriver/releases).  
Feel free to modify the code to use Chromium instead if you prefer it.

If you're on Arch: `sudo pacman -S firefox geckodriver`,

### Inspiration

I tried to make a basic web scraper for the USPS website months ago, only to find out that its security is crazy.  
Instead of trying to reverse engineer their client, I made this instead.

How it works:
- Selenium goes to the USPS tracking website, completing the JS challenge and logging the request data
- This client saves that request data to a JSON file for reuse (speeds up the client dramatically)
- Next, requests pulls the page from USPS using our saved cookies and parses it with BeautifulSoup
- Apply some basic scraping and there you go, a USPS tracking client
