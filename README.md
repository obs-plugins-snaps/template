# OBS Studio plugin snap template

A [Copier](https://copier.readthedocs.io/) template that scaffolds a snap
package for an [OBS Studio](https://obsproject.com/) plugin.

## Usage

```shell
copier copy <path-or-URL-to-this-template> my-plugin-obs-studio
```

For example, from the parent of this directory:

```shell
copier copy ./obs-studio-plugin-snap-template my-plugin-obs-studio
```

Copier asks a series of questions and renders the project. To answer
non-interactively (e.g. in CI), pass `--defaults` plus `--data` overrides:

```shell
copier copy \
  --data plugin_name=source-record \
  --data source_url=https://github.com/exeldro/obs-source-record.git \
  --data summary="Record any source in OBS Studio" \
  ./obs-studio-plugin-snap-template source-record-obs-studio
```

## Questions

| Question      | Meaning                                                            |
| ------------- | ------------------------------------------------------------------ |
| `plugin_name` | Upstream plugin project name; lowercase letters, digits, dashes    |
| `source_url`  | Git URL of the upstream plugin repository                          |
| `summary`     | One-line summary (maximum 78 characters)                           |
| `version`     | Upstream release tag to package (must exist upstream; it pins      |
|               | the build and becomes the snap version via `adopt-info`); the      |
|               | `0.1.0` placeholder default only serves throwaway renders          |
| `description` | Longer description, optional (defaults to the summary)             |
| `license`     | SPDX license identifier, optional (omitted when empty)             |

Derived automatically (not asked): the snap name (`<plugin_name>-obs-studio`),
the title (`<Plugin Name> (OBS plugin)`), the packaging repository URL
(`https://github.com/obs-plugins-snaps/<snap_name>-snap`, used for the
`source-code`, `contact` and `issues` metadata), and the `website` metadata
(the upstream URL without a `.git` suffix).

## Development

The template itself is tested with [pytest-copie](https://pypi.org/p/pytest-copie),
which renders the template with a range of answers and asserts on the
generated files. Tests live in `tests/`.

Run the test suite and the linters with `tox` (it uses `uv` under the hood,
see `tox.toml`):

```shell
tox             # render + lint everything
tox -e 3.14     # tests only
tox -e lint     # ruff check + format check
tox -e format   # ruff format
```

Run the tests directly against a specific template directory with:

```shell
uv run pytest
```

## Updating a generated project

The template ships a `.copier-answers.yml` file, so generated projects can
be updated when the template improves:

```shell
cd my-plugin-obs-studio
copier update
```

Note that `copier update` re-renders the scaffolding; changes made by hand
to `snap/snapcraft.yaml` may produce conflicts to resolve manually.

## Testing a generated project

```shell
cd my-plugin-obs-studio
snapcraft pack
sudo snap install ./<snap-name>_<version>_amd64.snap --dangerous
sudo snap connect obs-studio:obs-plugins <snap-name>:obs-plugins
```
trivial template change
