"""Tests for the OBS Studio plugin snap copier template."""

import yaml

#: Answers for every question with no default.
ANSWERS = {
    "plugin_name": "source-record",
    "source_url": "https://github.com/exeldro/obs-source-record.git",
    "summary": "Record any source in OBS Studio",
}


def snapcraft_yaml(result):
    """Return the rendered snap/snapcraft.yaml as text."""
    return (result.project_dir / "snap" / "snapcraft.yaml").read_text()


def answers_file(result):
    """Return the rendered .copier-answers.yml parsed as YAML."""
    return yaml.safe_load((result.project_dir / ".copier-answers.yml").read_text())


def make_project(copie, **overrides):
    """Generate a project from the template and assert that it succeeded."""
    result = copie.copy(extra_answers={**ANSWERS, **overrides})
    assert result.exit_code == 0, result.exception
    return result


def test_copied_project_layout(copie):
    """The generated project contains exactly the expected files."""
    result = make_project(copie)
    assert (result.project_dir / "snap" / "snapcraft.yaml").is_file()
    assert (result.project_dir / "README.md").is_file()
    assert (result.project_dir / ".github" / "workflows" / "ci.yaml").is_file()
    assert (result.project_dir / ".copier-answers.yml").is_file()
    assert (result.project_dir / ".gitignore").is_file()
    # Template-own files must not be copied.
    assert not (result.project_dir / "copier.yaml").exists()


def test_answers_file_content(copie):
    """The answers file records the answers for future updates."""
    recorded = answers_file(make_project(copie))
    assert recorded["plugin_name"] == "source-record"
    assert recorded["source_url"] == "https://github.com/exeldro/obs-source-record.git"
    assert recorded["summary"] == "Record any source in OBS Studio"
    # Computed values are not recorded.
    assert "snap_name" not in recorded
    assert "title" not in recorded


def test_snap_name_appends_suffix(copie):
    """The snap name is the plugin name plus the -obs-studio suffix."""
    result = make_project(copie, plugin_name="advanced-masks")
    assert "name: advanced-masks-obs-studio" in snapcraft_yaml(result)


def test_title_is_derived(copie):
    """The title is derived from the plugin name."""
    result = make_project(copie, plugin_name="advanced-masks")
    assert "title: Advanced Masks (OBS plugin)" in snapcraft_yaml(result)


def test_version_defaults_to_placeholder(copie):
    """Without an explicit version the placeholder is used."""
    assert "version: '0.1.0'" in snapcraft_yaml(make_project(copie))


def test_version_is_used_verbatim(copie):
    """An explicit version is rendered as-is, without any sanitization."""
    assert "version: '0.4.8'" in snapcraft_yaml(make_project(copie, version="0.4.8"))


def test_license_defaults_to_omitted(copie):
    """Without an explicit license the field is omitted entirely."""
    content = snapcraft_yaml(make_project(copie))
    assert "license:" not in content


def test_license_is_used_verbatim(copie):
    """An explicit license is rendered as-is."""
    result = make_project(copie, license="GPL-3.0-or-later")
    assert "license: GPL-3.0-or-later" in snapcraft_yaml(result)


def test_description_defaults_to_summary(copie):
    """Without a description the summary is used instead."""
    result = make_project(copie)
    expected = "description: |\n  Record any source in OBS Studio\n"
    assert expected in snapcraft_yaml(result)


def test_description_override(copie):
    """A custom description is used when provided."""
    result = make_project(copie, description="Individual record button for a source.")
    assert (
        "description: |\n  Individual record button for a source.\n"
        in snapcraft_yaml(result)
    )


def test_summary_is_quoted(copie):
    """The summary is quoted, so YAML-special characters are safe."""
    result = make_project(copie, summary="Plugin: records stuff #1")
    assert 'summary: "Plugin: records stuff #1"' in snapcraft_yaml(result)


def test_qt_packages_always_included(copie):
    """Qt6 build packages are included for every plugin."""
    content = snapcraft_yaml(make_project(copie))
    assert "- qt6-base-dev" in content
    assert "- qt6-svg-dev" in content


def test_packaging_metadata_points_at_packaging_repo(copie):
    """source-code, contact and issues point at the packaging repo; website
    points at the upstream plugin (without the .git suffix)."""
    data = yaml.safe_load(snapcraft_yaml(make_project(copie)))
    packaging = "https://github.com/obs-plugins-snaps/source-record-obs-studio-snap"
    assert data["website"] == "https://github.com/exeldro/obs-source-record"
    assert data["source-code"] == packaging
    assert data["contact"] == packaging
    assert data["issues"] == packaging


def test_multiline_description(copie):
    """Multi-paragraph descriptions survive wrapping and indentation."""
    description = (
        "First paragraph with a reasonably long line of text to force the "
        "wordwrap filter to break it at some point.\n\n"
        "Second paragraph.\n\n"
        "Third paragraph with another reasonably long line of text that the "
        "wordwrap filter will also break somewhere."
    )
    result = make_project(copie, description=description)
    rendered = yaml.safe_load(snapcraft_yaml(result))["description"]
    # Paragraphs are wrapped independently (76 columns + 2 of indent), but
    # the paragraph breaks themselves are preserved.
    expected = (
        "First paragraph with a reasonably long line of text to force the "
        "wordwrap\nfilter to break it at some point.\n\n"
        "Second paragraph.\n\n"
        "Third paragraph with another reasonably long line of text that the "
        "wordwrap\nfilter will also break somewhere."
    )
    assert rendered.rstrip("\n") == expected


def test_grade_defaults_to_devel(copie):
    """The snap starts in devel grade until it is verified."""
    assert "grade: devel" in snapcraft_yaml(make_project(copie))


def test_snapcraft_yaml_is_valid_yaml(copie):
    """The rendered snapcraft.yaml parses and has the expected structure."""
    data = yaml.safe_load(snapcraft_yaml(make_project(copie)))
    assert data["name"] == "source-record-obs-studio"
    assert data["base"] == "core24"
    assert data["version"] == "0.1.0"
    assert data["confinement"] == "strict"
    assert data["slots"]["obs-plugins"]["interface"] == "content"
    assert data["parts"]["prepare-hook"]["plugin"] == "nil"
    part = data["parts"]["source-record"]
    assert part["plugin"] == "cmake"
    assert part["source"] == "https://github.com/exeldro/obs-source-record.git"
    assert part["build-snaps"] == ["obs-studio/latest/stable"]


def test_prepare_hook_writes_snapctl(copie):
    """The prepare hook tells the obs-studio snap which snap provides plugins."""
    assert "snapctl set :obs-plugins snapname=" in snapcraft_yaml(make_project(copie))


def test_readme_mentions_snap_name(copie):
    """The generated README references the snap name."""
    readme = (make_project(copie).project_dir / "README.md").read_text()
    assert "sudo snap install source-record-obs-studio" in readme
    assert (
        "sudo snap connect obs-studio:obs-plugins source-record-obs-studio:obs-plugins"
        in readme
    )


def test_ci_workflow_calls_central_workflow(copie):
    """The CI workflow delegates to the shared build-snap reusable workflow."""
    ci_yaml = make_project(copie).project_dir / ".github" / "workflows" / "ci.yaml"
    workflow = yaml.safe_load(ci_yaml.read_text())
    job = workflow["jobs"]["call-central-workflow"]
    central = "obs-plugins-snaps/workflows/.github/workflows/build-snap.yml@main"
    assert job["uses"] == central
    assert job["with"]["plugin_name"] == "source-record"


def test_j2_suffix_not_leaking(copie):
    """No .j2 or .jinja suffixes remain in the generated project."""
    assert not list(make_project(copie).project_dir.rglob("*.j2"))
    assert not list(make_project(copie).project_dir.rglob("*.jinja"))
