Changes that exist only on the /preview2/ test copy, as `git diff` patches against main.
`tools/build_preview2.sh` applies every `*.patch` here in name order (01-..., 02-...). When a feature
is approved for the live site, apply its patch to main and delete it from here.
