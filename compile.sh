#!/bin/bash
# shellcheck disable=SC2068
# compile.sh - quickly compile a struct for all targets

KSC="$(which kaitai-struct-compiler 2>/dev/null)"
OUTPUT="${OUTPUT:-build}"
STRUCTS="$(find . -type f -name "*.ksy")"

if [[ -z "$KSC" ]]; then
    echo "ERROR: Unable to find 'ksc' (https://kaitai.io/) in PATH"
    exit 1
fi

rm -rf "$OUTPUT"
for struct in ${STRUCTS[@]}; do
    name="$(basename "$struct" ".ksy")"
    mkdir -p "${OUTPUT}/${name}"

    echo "Compiling ${name}..."
    "$KSC" --outdir "${OUTPUT}/${name}" --target all "$struct"

    (cd "$OUTPUT" && zip -r "${name}.zip" "${name}")
done
