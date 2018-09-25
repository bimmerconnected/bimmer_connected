#/bin/bash
set -eux
if [-d "dist"]; then
    rm -r dist
fi
python3 setup.py sdist bdist_wheel
twine upload dist/* -u m1n3rva -p "sndoA1v6ao87jKTAU45i"
