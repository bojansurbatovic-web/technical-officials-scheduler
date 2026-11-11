#!/bin/sh
# Creates the Apple signing certificates on Ubuntu (or any computer with openssl) – no Mac needed.
#
#   1) ./apple-certificate.sh csr distribution        → distribution.key + distribution.csr
#      Upload distribution.csr at developer.apple.com → Certificates → (+) → "Apple Distribution",
#      download the certificate (distribution.cer) into this folder.
#   2) ./apple-certificate.sh p12 distribution        → distribution.p12 and distribution.p12.base64.txt
#      Put the text of distribution.p12.base64.txt in the GitHub secret DIST_CERT_P12_BASE64
#      and the password you chose in DIST_CERT_PASSWORD.
#
#   For the Mac app also:  ./apple-certificate.sh csr installer  → upload as "Mac Installer Distribution",
#   download as installer.cer, then ./apple-certificate.sh p12 installer → secrets MAC_INSTALLER_P12_BASE64 / MAC_INSTALLER_PASSWORD.
#
# Keep the .key and .p12 files private (they are not needed in the repository). Delete them once the secrets are saved,
# or keep them in a password manager.
set -eu
cmd="${1:-}"; name="${2:-distribution}"
case "$cmd" in
  csr)
    printf "Your name (as in your Apple developer account): "; read -r cn
    printf "Your Apple ID e-mail: "; read -r mail
    umask 077
    openssl req -new -newkey rsa:2048 -nodes -keyout "$name.key" -out "$name.csr" -subj "/emailAddress=$mail/CN=$cn"
    echo "Created $name.csr – upload it to Apple, then download the certificate as $name.cer here."
    ;;
  p12)
    [ -f "$name.cer" ] || { echo "Missing $name.cer (download it from developer.apple.com)"; exit 1; }
    [ -f "$name.key" ] || { echo "Missing $name.key (made by the csr step on this computer)"; exit 1; }
    openssl x509 -inform DER -in "$name.cer" -out "$name.pem"
    echo "Choose a password for the .p12 file (you will put it in a GitHub secret):"
    umask 077
    # 3DES/SHA1 protection so that the macOS keychain on GitHub's build machines can import it
    openssl pkcs12 -export -inkey "$name.key" -in "$name.pem" -out "$name.p12" \
      -certpbe PBE-SHA1-3DES -keypbe PBE-SHA1-3DES -macalg sha1 -name "$name"
    base64 -w0 "$name.p12" > "$name.p12.base64.txt" 2>/dev/null || base64 "$name.p12" | tr -d '\n' > "$name.p12.base64.txt"
    rm -f "$name.pem"
    echo "Created $name.p12 and $name.p12.base64.txt"
    ;;
  key)
    # base64 of the App Store Connect API key (.p8) for the secret ASC_KEY_P8_BASE64
    f="${2:?usage: $0 key AuthKey_XXXXXXXXXX.p8}"
    base64 -w0 "$f" > "$f.base64.txt" 2>/dev/null || base64 "$f" | tr -d '\n' > "$f.base64.txt"
    echo "Created $f.base64.txt"
    ;;
  *)
    sed -n '2,20p' "$0"; exit 1 ;;
esac
