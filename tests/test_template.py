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
    assert (result.project_dir / ".github" / "workflows" / "release.yaml").is_file()
    assert (result.project_dir / ".github" / "workflows" / "promote.yaml").is_file()
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
    # The bootstrap pin is recorded (it seeds the source-tag pin).
    assert recorded["initial_source_tag"] == "0.1.0"


def test_snap_name_appends_suffix(copie):
    """The snap name is the plugin name plus the -obs-studio suffix."""
    result = make_project(copie, plugin_name="advanced-masks")
    assert "name: advanced-masks-obs-studio" in snapcraft_yaml(result)


def test_title_is_derived(copie):
    """The title is derived from the plugin name."""
    result = make_project(copie, plugin_name="advanced-masks")
    assert "title: Advanced Masks (OBS plugin)" in snapcraft_yaml(result)


def test_initial_source_tag_defaults_to_placeholder(copie):
    """The initial_source_tag question feeds the source-tag pin."""
    assert "source-tag: '0.1.0'" in snapcraft_yaml(make_project(copie))


def test_initial_source_tag_is_recorded_and_rendered(copie):
    """The bootstrap pin is recorded and rendered from the answer."""
    result = make_project(copie, initial_source_tag="0.4.8")
    assert "source-tag: '0.4.8'" in snapcraft_yaml(result)
    assert answers_file(result)["initial_source_tag"] == "0.4.8"


def test_adopt_info_replaces_static_version(copie):
    """The snap version is adopted from the tagged source tree, not static."""
    content = snapcraft_yaml(make_project(copie))
    assert "adopt-info: source-record" in content
    assert "version:" not in content.split("parts:")[0]
    assert 'craftctl set version="$(git describe' in content


def test_initial_source_tag_is_used_verbatim(copie):
    """An explicit bootstrap pin is rendered as-is, without any sanitization."""
    result = make_project(copie, initial_source_tag="0.4.8")
    assert "source-tag: '0.4.8'" in snapcraft_yaml(result)


def test_initial_source_tag_is_recorded_in_answers(copie):
    """The bootstrap pin is persisted for future updates."""
    result = make_project(copie, initial_source_tag="0.4.8")
    assert answers_file(result)["initial_source_tag"] == "0.4.8"


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
    """source-code points at the packaging repo; contact/issues at its issue
    tracker (the store's 'Report a bug' link is the issues URL verbatim);
    website points at the upstream plugin (without the .git suffix)."""
    data = yaml.safe_load(snapcraft_yaml(make_project(copie)))
    packaging = "https://github.com/obs-plugins-snaps/source-record-obs-studio-snap"
    assert data["website"] == "https://github.com/exeldro/obs-source-record"
    assert data["source-code"] == packaging
    assert data["contact"] == f"{packaging}/issues"
    assert data["issues"] == f"{packaging}/issues"


def test_multiline_description(copie):
    """Multi-paragraph descriptions keep their breaks, unwrapped."""
    description = (
        "First paragraph with a reasonably long line of text that would "
        "definitely have been broken by the old wordwrap filter.\n\n"
        "Second paragraph.\n\n"
        "Third paragraph with another long line that stays on one line too."
    )
    result = make_project(copie, description=description)
    rendered = yaml.safe_load(snapcraft_yaml(result))["description"]
    # Paragraphs are rendered unwrapped (the store soft-wraps for display),
    # but the paragraph breaks themselves are preserved, and the shared
    # installation fragment is appended after them.
    assert rendered.startswith(
        "First paragraph with a reasonably long line of text that would "
        "definitely have been broken by the old wordwrap filter.\n\n"
        "Second paragraph.\n\n"
        "Third paragraph with another long line that stays on one line too."
    )
    # No hard mid-sentence wrap: each source line survives intact.
    assert "definitely have been broken by the old wordwrap filter." in rendered


def test_description_includes_installation(copie):
    """The store description carries the shared installation fragment."""
    description = yaml.safe_load(snapcraft_yaml(make_project(copie)))["description"]
    assert "Installation" in description
    assert "sudo snap install source-record-obs-studio" in description
    assert (
        "sudo snap connect obs-studio:obs-plugins"
        " source-record-obs-studio:obs-plugins" in description
    )


def test_description_fits_store_limit(copie):
    """The rendered description stays within the Snap Store's 4096 chars."""
    description = yaml.safe_load(snapcraft_yaml(make_project(copie)))["description"]
    assert len(description) <= 4096


def test_grade_defaults_to_devel(copie):
    """The snap starts in devel grade until it is verified."""
    assert "grade: devel" in snapcraft_yaml(make_project(copie))


def test_snapcraft_yaml_is_valid_yaml(copie):
    """The rendered snapcraft.yaml parses and has the expected structure."""
    data = yaml.safe_load(snapcraft_yaml(make_project(copie)))
    assert data["name"] == "source-record-obs-studio"
    assert data["base"] == "core24"
    assert data["adopt-info"] == "source-record"
    assert "version" not in data
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
    # The intro links to the upstream repository without the .git suffix.
    assert "https://github.com/exeldro/obs-source-record.git" not in readme
    assert "[source-record](https://github.com/exeldro/obs-source-record)" in readme
    assert "## Development" in readme


def test_ci_workflow_calls_central_workflows(copie):
    """ci.yaml builds on pull requests via the shared reusable workflow."""
    ci_yaml = make_project(copie).project_dir / ".github" / "workflows" / "ci.yaml"
    workflow = yaml.safe_load(ci_yaml.read_text())
    # YAML 1.1 parses the `on` key as the boolean True.
    triggers = workflow[True]
    assert triggers["pull_request"] is None
    assert "push" not in triggers and "workflow_dispatch" not in triggers

    build = workflow["jobs"]["build"]
    assert build["uses"] == (
        "obs-plugins-snaps/workflows/.github/workflows/build-snap.yml@main"
    )
    assert build["with"]["plugin_name"] == "source-record"


def test_release_workflow_releases_to_edge(copie):
    """release.yaml packs and releases to latest/edge on pushes to main."""
    release_yaml = (
        make_project(copie).project_dir / ".github" / "workflows" / "release.yaml"
    )
    workflow = yaml.safe_load(release_yaml.read_text())
    triggers = workflow[True]
    assert triggers["push"] == {"branches": ["main"]}
    assert "pull_request" not in triggers

    release = workflow["jobs"]["release"]
    assert release["uses"] == (
        "obs-plugins-snaps/workflows/.github/workflows/release-to-edge.yml@main"
    )
    assert release["with"]["plugin_name"] == "source-record"
    assert release["secrets"] == "inherit"


def test_promote_workflow_is_dispatchable(copie):
    """promote.yaml promotes a revision from the Actions tab."""
    promote_yaml = (
        make_project(copie).project_dir / ".github" / "workflows" / "promote.yaml"
    )
    workflow = yaml.safe_load(promote_yaml.read_text())
    triggers = workflow[True]
    assert "push" not in triggers and "pull_request" not in triggers
    dispatch = triggers["workflow_dispatch"]
    assert dispatch["inputs"]["revision"]["default"] == "latest"
    assert dispatch["inputs"]["channel"]["required"] is True
    assert dispatch["inputs"]["channel"]["type"] == "choice"
    assert dispatch["inputs"]["channel"]["options"] == [
        "beta",
        "candidate",
        "stable",
    ]

    promote = workflow["jobs"]["promote"]
    assert promote["uses"] == (
        "obs-plugins-snaps/workflows/.github/workflows/promote.yml@main"
    )
    assert promote["with"]["plugin_name"] == "source-record"
    assert promote["with"]["revision"] == "${{ github.event.inputs.revision }}"
    assert promote["with"]["channel"] == "${{ github.event.inputs.channel }}"
    assert promote["secrets"] == "inherit"


def test_j2_suffix_not_leaking(copie):
    """No .j2 or .jinja suffixes remain in the generated project."""
    assert not list(make_project(copie).project_dir.rglob("*.j2"))
    assert not list(make_project(copie).project_dir.rglob("*.jinja"))


def test_icon_key_and_asset_shipped(copie):
    """The rendered yaml declares the icon and the template ships the PNG."""
    result = make_project(copie)
    data = yaml.safe_load(snapcraft_yaml(result))
    assert data["icon"] == "snap/gui/icon.png"
    icon = result.project_dir / "snap" / "gui" / "icon.png"
    assert icon.is_file()
    assert icon.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic


def test_readme_carries_store_badge(copie):
    """The README links the store badge for the snap."""
    readme = (make_project(copie).project_dir / "README.md").read_text()
    assert (
        "[![source-record-obs-studio]"
        "(https://snapcraft.io/source-record-obs-studio/badge.svg)]"
        "(https://snapcraft.io/source-record-obs-studio)" in readme
    )


def test_bug_issue_template_rendered(copie):
    """The bug report issue template is rendered without jinja artifacts."""
    path = make_project(copie).project_dir / ".github" / "ISSUE_TEMPLATE" / "bug.yml"
    content = path.read_text()
    assert "Affected snap" in content
    native = (
        "I have checked that this error does not happen "
        "by installing the plugin natively"
    )
    assert native in content
    assert "{{" not in content and "{%" not in content
