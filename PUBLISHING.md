# Publishing Technical Officials Scheduler

This takes about an hour the first time. Every step is done in a web browser or in the Ubuntu terminal – **no Mac is needed**. GitHub's Mac build machines compile, sign and upload the app.

What you need:
* the GitHub account **bojansurbatovic-web**
* your **Apple Developer Program** membership (Account Holder or Admin role)
* Ubuntu with `git`, `openssl` and (optionally) the GitHub CLI `gh`

The bundle ID used everywhere below is **`com.bojansurbatovic.toscheduler`**. To use a different one, change it in `apple/Config/Base.xcconfig` and set the GitHub variable `BUNDLE_ID` (step 4).

---

## 1. Put the code on GitHub

```bash
unzip technical-officials-scheduler.zip && cd technical-officials-scheduler
gh auth login                      # sign in as bojansurbatovic-web
gh repo create bojansurbatovic-web/technical-officials-scheduler --public --source . --push
```

Without `gh`: create an empty **public** repository called `technical-officials-scheduler` on github.com, then:

```bash
git remote add origin https://github.com/bojansurbatovic-web/technical-officials-scheduler.git
git push -u origin main
```

The repository is public because the free GitHub Pages hosting (for the privacy policy, which Apple requires) needs that. It contains no secrets.

After the push, open the repository → **Actions** and check:
* **Tests and build check** – the planner tests, the screens, and an unsigned compile of the iPhone/iPad and Mac apps. If the Apple compile fails, open the run, download `xcode-build-logs`, and send me the lines with `error:`.
* **Publish web version and privacy page** – if it fails at "configure-pages", go to **Settings → Pages**, set **Source: GitHub Actions**, then re-run the workflow.

### Custom domain trisport.me

The site is served at **https://trisport.me**. At the company where trisport.me is registered (its DNS settings), add:

| Type | Name / host | Value |
|---|---|---|
| TXT | `_github-pages-challenge-bojansurbatovic-web` | the code GitHub shows on *your profile → Settings → Pages → Verified domains* |
| A | `@` (trisport.me) | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| AAAA | `@` | `2606:50c0:8000::153` |
| AAAA | `@` | `2606:50c0:8001::153` |
| AAAA | `@` | `2606:50c0:8002::153` |
| AAAA | `@` | `2606:50c0:8003::153` |
| CNAME | `www` | `bojansurbatovic-web.github.io` |

Remove any other A, AAAA or CNAME records for `@` and `www` (for example a parking page). Then:
1. Profile → **Settings → Pages → Verified domains** → **Verify** (it can take up to 24 h for DNS to update; usually minutes).
2. Repository → **Settings → Pages**: *Source* **GitHub Actions**, *Custom domain* `trisport.me` → **Save**. When the DNS check is green, tick **Enforce HTTPS**.

When it is green, these pages are live (Apple needs the privacy and support URLs):
* https://trisport.me/ – home page
* https://trisport.me/app/ – the full app in the browser. On an iPhone or iPad, *Share → Add to Home Screen* gives you the app straight away, before the App Store release.
* https://trisport.me/privacy.html
* https://trisport.me/support.html

## 2. Register the app with Apple

1. **developer.apple.com → Account → Certificates, IDs & Profiles → Identifiers → (+)** → *App IDs* → *App*.
   Description: `Technical Officials Scheduler`. Bundle ID: *Explicit*, `com.bojansurbatovic.toscheduler`. No capabilities needed. **Register.**
2. **appstoreconnect.apple.com → Apps → (+) → New App**
   * Platforms: **iOS** and **macOS**
   * Name: `Technical Officials Scheduler` (if the name is taken, add a word, e.g. "… for Triathlon")
   * Primary language: English (U.K.) or English (U.S.)
   * Bundle ID: the one from step 1
   * SKU: `toscheduler`
   * User access: Full access

## 3. Create the signing keys (on Ubuntu)

### a) App Store Connect API key – lets GitHub upload builds
**App Store Connect → Users and Access → Integrations → App Store Connect API → Team Keys → (+)**
Name `GitHub`, Access **Admin**. Download the `AuthKey_XXXXXXXXXX.p8` file (it can be downloaded only once) and note the **Key ID** and the **Issuer ID** shown above the list.

```bash
cd tools/apple-signing
./apple-certificate.sh key ~/Downloads/AuthKey_XXXXXXXXXX.p8      # → AuthKey_….p8.base64.txt
```

### b) Apple Distribution certificate – signs the app
```bash
./apple-certificate.sh csr distribution      # asks for your name and Apple ID e-mail → distribution.csr
```
**developer.apple.com → Certificates → (+) → Apple Distribution** → upload `distribution.csr` → download → save as `tools/apple-signing/distribution.cer`.
```bash
./apple-certificate.sh p12 distribution      # choose a password → distribution.p12.base64.txt
```

### c) Only for the Mac app: Mac Installer Distribution certificate
```bash
./apple-certificate.sh csr installer
# developer.apple.com → Certificates → (+) → "Mac Installer Distribution" → upload installer.csr → save as installer.cer
./apple-certificate.sh p12 installer
```

Your **Team ID** is at developer.apple.com → Account → Membership details.

## 4. Store them as GitHub secrets

Repository → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `APPLE_TEAM_ID` | your Team ID (10 characters) |
| `ASC_KEY_ID` | the API key's Key ID |
| `ASC_ISSUER_ID` | the Issuer ID |
| `ASC_KEY_P8_BASE64` | contents of `AuthKey_….p8.base64.txt` |
| `DIST_CERT_P12_BASE64` | contents of `distribution.p12.base64.txt` |
| `DIST_CERT_PASSWORD` | the password you chose in 3b |
| `MAC_INSTALLER_P12_BASE64` | *(Mac only)* contents of `installer.p12.base64.txt` |
| `MAC_INSTALLER_PASSWORD` | *(Mac only)* the password from 3c |

Optional variable (*Variables* tab): `BUNDLE_ID`, only if you changed it.

With the GitHub CLI instead: `gh secret set DIST_CERT_P12_BASE64 < distribution.p12.base64.txt` (and the same for the others).

Then delete the `.p8`, `.key`, `.p12` and `.base64.txt` files, or keep them in a password manager. `.gitignore` already keeps them out of git.

## 5. Build and upload

Repository → **Actions → Upload to TestFlight → Run workflow**. Choose `iphone-ipad`, `mac` or `both`, and the version (`1.0.0`). It takes about 15–25 minutes. Later you can also release by pushing a tag: `git tag v1.0.1 && git push --tags` (this uploads the iPhone/iPad app).

When it is done, the build appears in **App Store Connect → TestFlight** after Apple's processing, which usually takes 5–30 minutes. Install the **TestFlight** app on your iPhone or iPad and test. On a Mac, TestFlight is in the Mac App Store.

## 6. Submit to the App Store

In App Store Connect → your app:
1. **App Information**: category Sports (secondary Productivity), and the privacy policy URL from step 1.
2. **App Privacy** → Get Started → *No, we do not collect data from this app* → Publish.
3. **Pricing and Availability**: Free, all countries or the ones you choose.
4. **iOS App → 1.0 Prepare for Submission**:
   * Screenshots: drag in `app-store/screenshots/iphone-6.9-*.png` (6.9" display) and `ipad-13-*.png` (13" display)
   * Promotional text, description, keywords, support and marketing URL: copy from `app-store/metadata.md`
   * **Build**: choose the build uploaded in step 5
   * Age rating: answer *None* everywhere (4+)
   * App Review Information: no sign-in required; paste the review notes from `metadata.md`
   * **Add for Review → Submit**
5. **macOS App** (if you uploaded it): the same, with `mac-*.png`.

Apple's review usually takes 1–3 days. You will get an e-mail; after approval the app goes live (or on the date you set).

**Without the Mac build:** iPad apps are also offered to Macs with Apple silicon (every Mac since late 2020). Leave *Make this app available on Mac* ticked under Pricing and Availability.

## Updating the app

1. Change the code and push it. The checks run automatically.
2. Run **Upload to TestFlight** with a higher version, e.g. `1.0.1`. The build number counts up by itself.
3. In App Store Connect, create the new version, choose the build, and submit.

## If something goes wrong

| Message | Fix |
|---|---|
| `Secret … is missing` | Add the secret named in the message (step 4). |
| `No profile for team … matching` / `Could not find a matching code signing identity` | Check that `DIST_CERT_P12_BASE64` is the **Apple Distribution** certificate made from *your* `distribution.key`, and that the bundle ID is registered (step 2.1). |
| `No suitable application records were found` | Create the app record in App Store Connect (step 2.2) with the same bundle ID. |
| `The bundle version must be higher` | Run the workflow again (the build number is the run number), or use a new version. |
| `Authentication credentials are missing or invalid` | The API key needs the **Admin** role, and `ASC_KEY_P8_BASE64` must be the base64 of the whole `.p8` file. |
| Build errors in Swift | Download the build logs artifact and send me the `error:` lines. |

### Building on a Mac instead (optional)
```bash
brew install xcodegen && cd apple && xcodegen generate && open TOScheduler.xcodeproj
```
Choose your team under *Signing & Capabilities* for both targets, then *Product → Archive → Distribute App → App Store Connect*.

---

## Snap Store (Ubuntu)

The Ubuntu desktop app (`linux/`) is packaged as a snap (`snap/snapcraft.yaml`). The workflow **Snap (Ubuntu)** builds it on every change to `linux/` or `snap/`, and you can also start it from the Actions tab and choose a channel. Every run leaves the built `.snap` as a download (artifact `snap`). It is uploaded to the Snap Store only once the secret below exists.

One-time setup on your Ubuntu computer, signed in with the same Ubuntu One account as TriCarbon:

```bash
sudo snap install snapcraft --classic
snapcraft login
snapcraft register technical-officials-scheduler
snapcraft export-login --snaps=technical-officials-scheduler \
  --acls package_access,package_push,package_update,package_release snap-credentials.txt
gh secret set SNAPCRAFT_STORE_CREDENTIALS -R bojansurbatovic-web/technical-officials-scheduler < snap-credentials.txt
rm snap-credentials.txt
```

You can also register the name at https://snapcraft.io/register-snap, and paste the file's contents as the secret under *Settings → Secrets and variables → Actions*.

Then run **Actions → Snap (Ubuntu) → Run workflow** with the channel `stable`. On snapcraft.io → *My snaps → technical-officials-scheduler → Listing*, add screenshots (`app-store/screenshots/mac-*.png` work well), the category *Productivity* and the website https://www.trisport.me. After that, anyone can install it:

```bash
sudo snap install technical-officials-scheduler
```

Pushes to `main` that change `linux/` or `snap/` go to the `edge` channel. Use *Run workflow* with `stable` to release.
