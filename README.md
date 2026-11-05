# PS5 Browser downloads

Native PS5 Browser packages for title **PPSA99257**.

[Download the latest package](https://github.com/Vibe-Code-Jesus/PS5Browser-Releases/releases/latest).
Extract the complete PPSA99257 folder and replace the installed app folder contents.
Keep /data/ps5browser: bookmarks, cookies, settings and downloaded files live there.

The browser checks for newer native packages at launch and every 30 minutes.
A new version appears on the main screen. Click **Update via GitHub** to download,
verify, install and restart automatically. Old package files are removed only
after the new native app and browser core confirm startup. A failed startup
restores the previous package. Browser data stays in place.

**First install:** versions .006 and earlier need one manual replacement with
this complete package to gain the installer. Subsequent releases use the button.

This is a native preview for PS5/ProsperoStore review. Local integration,
rollback and package checks passed; actual PS5 restart and storage behavior
still need console confirmation.

The existing homebrew environment must already support this app's launch service.
This repository distributes compiled packages, notices and release automation.
It does not contain PS5Browser application source, private development backups,
credentials or console data. GitHub's automatic source archives contain this
release repository's files, not the application's source tree.

## Publishing

Commit a validated versioned Preview ZIP, release.json and SHA256SUMS.txt together.
The workflow validates the package, creates a draft, verifies uploaded asset
hashes/sizes, then publishes it as the latest native release. Existing release
versions cannot be overwritten with different bytes. App source builds and
private recovery archives remain outside this repository.
