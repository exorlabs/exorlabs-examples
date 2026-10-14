# GitHub upload and updates

Repository: **exorlabs/exorlabs-examples**. Keep both projects in this one repository, with `README.md`, `.gitignore` and `.github/` at the root.

## Initial upload

1. Under the **exorlabs** organization, create one **Public**, empty repository called `exorlabs-examples`. Leave initial README, license and gitignore creation unchecked; these files are supplied here. Skip creation if the repository already exists.
2. Extract `exorlabs-examples.zip`. Open a terminal inside the extracted `exorlabs-examples` folder. `README.md`, `.gitignore`, `.github` and the two project folders must be at this level.
3. Set the repository links in the two blog bodies:

```bash
python3 tools/set_repository_url.py https://github.com/exorlabs/exorlabs-examples
```

4. Initialize and inspect the file list:

```bash
git init
git branch -M main
git add .
git status --short
```

The staged files should contain the code, tests, docs, workflows and `.example` templates. Real `.env` files, `firmware/config.h`, `secrets/`, generated builds and firmware binaries should be absent. If you later create real configuration, `git check-ignore` can confirm it is ignored.

5. Commit and push:

```bash
git commit -m "Add draw.io investigation and ESP32 stats dashboard"
git remote add origin https://github.com/exorlabs/exorlabs-examples.git
git push -u origin main
```

Use your normal GitHub authentication. If Git requests an author identity, configure it locally for this repository; a GitHub noreply email from your account's email settings can keep a personal email out of the public commit.

6. Open the repository's **Actions** tab. The diagram-codec, REA analysis, collector/decoder and firmware jobs should report their results. The application-codec comparisons and firmware compilation were checked locally, but no GitHub workflow execution is claimed before this push. If the vendor demo changes, the firmware preparation step stops at its recorded port hash.

## Later updates

Clone the repository once, edit the relevant project and commit the source changes:

```bash
git clone https://github.com/exorlabs/exorlabs-examples.git
cd exorlabs-examples
# Edit the files, then run the checks documented in that project's README.
git add .
git diff --cached --stat
git commit -m "Describe the change"
git push
```

For an existing checkout, use `git pull --ff-only` before starting. Keep generated firmware, vendor downloads and local configuration out of commits. Run the two projects' test commands from their respective project folders.

## Blog code links

| Article | Link for the full code |
| --- | --- |
| ESP32/LVGL dashboard | https://github.com/exorlabs/exorlabs-examples/tree/main/exor-rackstats |
| draw.io/REA investigation | https://github.com/exorlabs/exorlabs-examples/tree/main/exor-rea-drawio |

## What to put into Ghost

Use **Posts**. The short article bodies are:

| Post | Source body | Suggested slug |
| --- | --- | --- |
| Opening a draw.io file without draw.io | `exor-rea-drawio/docs/BLOG.md` | `reverse-engineering-api-rea` |
| From Proxmox and Synology stats to an ESP32 dashboard | `exor-rackstats/docs/BLOG.md` | `esp32-lvgl9-arduino-dashboard` |

Put the article's first heading into Ghost's title field. Paste the rest into a Markdown card. Use the real GitHub links after running the URL script; the full code stays in the repository.

If you already created the earlier drafts, update their title/body rather than making duplicates. Keep their slugs to preserve the URLs. Choose Public access and preview code blocks and links. The new articles describe the programs as tutorials and retain the real verification limits; they do not claim a completed REA trace or physical board deployment that has not happened.

The REA job saves its JSON in the downloadable drawio-rea-analysis artifact. After the job succeeds, you can add its actual findings as a case-study section. A failed job's error report is not a completed analysis. After uploading the board and checking both private collectors, you can add a device photograph and your observed readings to the second article.
