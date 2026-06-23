from scripts.check_milvus_fields import audit_rows


def issue_codes(report):
    return {issue["code"] for issue in report["issues"]}


def issue_codes_for_chunk(report, chunk_id):
    return {
        issue["code"]
        for issue in report["issues"]
        if issue["row"].get("chunk_id") == chunk_id
    }


def test_audit_rows_flags_field_quality_regressions_from_memory_rows():
    rows = [
        {
            "chunk_id": "raw_1",
            "content_type": "raw_child",
            "retrieval_text": "same evidence text",
            "parent_chunk_id": "",
            "chunk_text": "<table><tr><td>alarm</td></tr></table>",
            "source_page_start": 0,
            "source_page_end": 2,
        },
        {
            "chunk_id": "fault_1",
            "content_type": "fault_code",
            "retrieval_text": "fault code evidence",
            "chunk_text": r"see output\images\fault.png",
            "parent_chunk_id": "parent_1",
            "fault_code": "",
            "source_page_start": 3,
            "source_page_end": 3,
        },
        {
            "chunk_id": "image_1",
            "content_type": "image_ref",
            "chunk_text": "diagram evidence",
            "retrieval_text": "output/images/camera.png",
            "parent_chunk_id": "parent_2",
            "image_title": "assets/figures/camera.png",
            "source_page_start": 4,
            "source_page_end": 4,
        },
        {
            "chunk_id": "spec_1",
            "content_type": "spec_item",
            "chunk_text": "parameter evidence",
            "retrieval_text": "parameter recall terms",
            "parent_chunk_id": "parent_3",
            "parameter_name": "",
            "parameter_value": None,
            "source_page_start": 5,
            "source_page_end": 0,
        },
    ]

    report = audit_rows(rows)

    assert report["summary"] == {
        "row_count": 4,
            "issue_count": 11,
        "affected_row_count": 4,
    }
    assert report["counters"] == {
            "missing_parent_chunk_id": 1,
        "html_pollution": 1,
        "image_path_pollution": 2,
        "fault_code_missing_code": 1,
        "image_ref_missing_asset_id": 1,
        "image_title_looks_like_path": 1,
        "invalid_source_page": 2,
        "spec_item_missing_parameter_name": 1,
        "spec_item_missing_parameter_value": 1,
    }
    assert issue_codes(report) == set(report["counters"])
    assert issue_codes_for_chunk(report, "raw_1") == {
        "missing_parent_chunk_id",
        "html_pollution",
        "invalid_source_page",
    }
    assert issue_codes_for_chunk(report, "fault_1") == {
        "image_path_pollution",
        "fault_code_missing_code",
    }
    assert issue_codes_for_chunk(report, "image_1") == {
        "image_path_pollution",
        "image_ref_missing_asset_id",
        "image_title_looks_like_path",
    }
    assert issue_codes_for_chunk(report, "spec_1") == {
        "invalid_source_page",
        "spec_item_missing_parameter_name",
        "spec_item_missing_parameter_value",
    }


def test_audit_rows_accepts_clean_typed_evidence_rows():
    rows = [
        {
            "chunk_id": "raw_1",
            "content_type": "raw_child",
            "chunk_text": "The camera focal length is 4 mm on page 2.",
            "retrieval_text": "camera focal length 4 mm page 2",
            "parent_chunk_id": "section_1",
            "source_page_start": 2,
            "source_page_end": 2,
        },
        {
            "chunk_id": "fault_1",
            "content_type": "fault_code",
            "chunk_text": "Fault 03 means no signal input.",
            "retrieval_text": "fault 03 no signal input",
            "parent_chunk_id": "section_2",
            "fault_code": "03",
            "source_page_start": 8,
            "source_page_end": 8,
        },
        {
            "chunk_id": "image_1",
            "content_type": "image_ref",
            "chunk_text": "Figure 2 shows the camera wiring diagram.",
            "retrieval_text": "camera wiring diagram figure 2",
            "parent_chunk_id": "section_3",
            "image_asset_id": "img_camera_wiring",
            "image_title": "Camera wiring diagram",
            "source_page_start": 9,
            "source_page_end": 9,
        },
        {
            "chunk_id": "spec_1",
            "content_type": "spec_item",
            "chunk_text": "Operating voltage: 24 V DC.",
            "retrieval_text": "operating voltage 24 V DC",
            "parent_chunk_id": "section_4",
            "parameter_name": "Operating voltage",
            "parameter_value": "24 V DC",
            "source_page_start": 10,
            "source_page_end": 10,
        },
    ]

    report = audit_rows(rows)

    assert report["summary"] == {
        "row_count": 4,
        "issue_count": 0,
        "affected_row_count": 0,
    }
    assert report["counters"] == {}
    assert report["issues"] == []


def test_audit_rows_allows_doc_summary_without_parent_chunk_id():
    report = audit_rows(
        [
            {
                "chunk_id": "doc_summary_1",
                "content_type": "doc_summary",
                "chunk_text": "Document summary.",
                "retrieval_text": "document summary recall text",
                "parent_chunk_id": "",
                "source_page_start": 1,
                "source_page_end": 1,
            }
        ]
    )

    assert report["summary"]["issue_count"] == 0


def test_audit_rows_flags_image_path_pollution_in_chunk_text():
    report = audit_rows(
        [
            {
                "chunk_id": "raw_with_image_path",
                "content_type": "raw_child",
                "retrieval_text": "clean recall text",
                "chunk_text": "Clean sentence plus images/page_001.png",
                "parent_chunk_id": "section_1",
                "source_page_start": 1,
                "source_page_end": 1,
            }
        ]
    )

    assert issue_codes_for_chunk(report, "raw_with_image_path") == {"image_path_pollution"}
