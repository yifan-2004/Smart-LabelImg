from pathlib import Path


STATIC = Path(__file__).parents[1] / "smart_labelimg" / "web" / "static"


def test_web_static_assets_exist() -> None:
    assert (STATIC / "index.html").is_file()
    assert (STATIC / "styles.css").is_file()
    assert (STATIC / "app.js").is_file()


def test_web_ui_has_primary_annotation_controls() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    for control_id in (
        "dataset-path",
        "annotation-format",
        "annotation-canvas",
        "image-list",
        "label-list",
        "save-button",
        "previous-button",
        "next-button",
        "copy-previous-button",
        "smart-next-button",
        "manual-mode",
        "smart-mode",
        "undo-button",
        "redo-button",
    ):
        assert f'id="{control_id}"' in html


def test_web_frontend_uses_only_relative_local_api_paths() -> None:
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")
    for path in (
        '"/api/dataset/open"',
        '"/api/dataset"',
        "`/api/images/${index}`",
        "`/api/images/${index}/content`",
        "`/api/images/${index}/annotations`",
        "`/api/images/${index}/refine`",
        "`/api/images/${index}/propagate`",
        "`/api/images/${index}/previous`",
    ):
        assert path in javascript
    assert "http://" not in javascript
    assert "https://" not in javascript


def test_web_frontend_binds_speed_shortcuts_and_canvas_actions() -> None:
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")
    for marker in (
        'key === "a"',
        'key === "d"',
        'key === "w"',
        'key === "s"',
        'event.shiftKey && key === "d"',
        '["delete", "backspace"]',
        '"pointerdown"',
        '"pointermove"',
        '"pointerup"',
        "screenPoint(event)",
        "state.fitScale * state.zoom",
    ):
        assert marker in javascript


def test_smart_next_propagates_into_target_image() -> None:
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")
    next_index = javascript.index("const nextIndex = state.currentIndex + 1")
    propagate = javascript.index("API.propagate(nextIndex)", next_index)
    load_target = javascript.index("loadImageWithoutBusy(nextIndex)", propagate)
    assert next_index < propagate < load_target


def test_copy_previous_uses_the_previous_image_index_not_visit_history() -> None:
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")
    start = javascript.index("async function copyPreviousBoxes()")
    request = javascript.index("API.previous(state.currentIndex)", start)
    assert request > start


def test_low_confidence_propagation_requires_enter_to_accept() -> None:
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "state.pendingCandidates" in javascript
    assert 'event.key === "Enter"' in javascript
    assert "acceptPendingCandidates()" in javascript


def test_web_layout_is_desktop_first_and_responsive() -> None:
    css = (STATIC / "styles.css").read_text(encoding="utf-8")
    assert "grid-template-columns: var(--sidebar-width) minmax(430px, 1fr) var(--right-width)" in css
    assert "@media (max-width: 1050px)" in css
    assert "@media (max-width: 820px)" in css


def test_annotation_changes_are_debounced_and_auto_saved() -> None:
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "function scheduleAutoSave()" in javascript
    assert "setTimeout" in javascript
    assert "saveAnnotations({ silent: true" in javascript
    assert "state.editRevision === revisionAtStart" in javascript
    assert "if (state.savePromise)" in javascript


def test_opening_another_dataset_saves_the_current_dataset_first() -> None:
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")
    start = javascript.index("async function openDataset(path)")
    save = javascript.index("await saveAnnotations", start)
    open_request = javascript.index("API.openDataset", start)
    assert save < open_request
    assert "if (state.busy) return" in javascript[start:open_request]


def test_busy_state_disables_controls_that_can_mutate_the_session() -> None:
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "const busyControls" in javascript
    assert "control.disabled = value" in javascript


def test_dataset_image_names_from_backend_are_normalized_for_the_list() -> None:
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")
    assert 'typeof item === "string" ? { name: item } : item' in javascript
