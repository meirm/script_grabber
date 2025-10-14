"""Tests for timezone handling in backend datetime operations."""

import pytest
from datetime import datetime, timezone
import json

from core.models import JobStatus, JobListItem, JobArchiveResponse, StaleJobInfo


class TestDateTimeTimezoneAwareness:
    """Test that datetime objects are timezone-aware."""

    def test_datetime_now_with_utc(self):
        """Test that datetime.now(timezone.utc) creates timezone-aware datetime."""
        dt = datetime.now(timezone.utc)
        assert dt.tzinfo is not None
        assert dt.tzinfo == timezone.utc

    def test_datetime_fromtimestamp_with_utc(self):
        """Test that datetime.fromtimestamp with tz=timezone.utc creates timezone-aware datetime."""
        timestamp = 1697280000.0  # 2023-10-14 12:00:00 UTC
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        assert dt.tzinfo is not None
        assert dt.tzinfo == timezone.utc


class TestPydanticDateTimeSerialization:
    """Test that Pydantic models serialize datetime with timezone info."""

    def test_job_status_serialization(self):
        """Test JobStatus serializes datetime fields with timezone info."""
        now_utc = datetime.now(timezone.utc)

        status = JobStatus(
            job_id="test_job",
            status="done",
            submitted_at=now_utc,
            completed_at=now_utc
        )

        # Serialize to JSON
        json_str = status.model_dump_json()
        json_data = json.loads(json_str)

        # Verify timezone info is present (Z or +00:00)
        assert 'submitted_at' in json_data
        assert 'completed_at' in json_data

        # Check for timezone indicators
        submitted_str = json_data['submitted_at']
        completed_str = json_data['completed_at']

        # ISO 8601 with timezone should contain Z or +00:00
        assert (submitted_str.endswith('Z') or '+00:00' in submitted_str or
                submitted_str.endswith('+00:00')), \
            f"submitted_at missing timezone info: {submitted_str}"
        assert (completed_str.endswith('Z') or '+00:00' in completed_str or
                completed_str.endswith('+00:00')), \
            f"completed_at missing timezone info: {completed_str}"

    def test_job_list_item_serialization(self):
        """Test JobListItem serializes datetime with timezone info."""
        now_utc = datetime.now(timezone.utc)

        item = JobListItem(
            job_id="test_job",
            status="done",
            submitted_at=now_utc
        )

        json_str = item.model_dump_json()
        json_data = json.loads(json_str)

        submitted_str = json_data['submitted_at']
        assert (submitted_str.endswith('Z') or '+00:00' in submitted_str or
                submitted_str.endswith('+00:00')), \
            f"submitted_at missing timezone info: {submitted_str}"

    def test_job_archive_response_serialization(self):
        """Test JobArchiveResponse serializes archived_at with timezone info."""
        now_utc = datetime.now(timezone.utc)

        response = JobArchiveResponse(
            job_id="test_job",
            status="success",
            message="Archived",
            archived_at=now_utc
        )

        json_str = response.model_dump_json()
        json_data = json.loads(json_str)

        archived_str = json_data['archived_at']
        assert (archived_str.endswith('Z') or '+00:00' in archived_str or
                archived_str.endswith('+00:00')), \
            f"archived_at missing timezone info: {archived_str}"

    def test_stale_job_info_serialization(self):
        """Test StaleJobInfo serializes submitted_at with timezone info."""
        now_utc = datetime.now(timezone.utc)

        info = StaleJobInfo(
            job_id="test_job",
            grabber="grabber1",
            runtime_duration=3600.0,
            submitted_at=now_utc
        )

        json_str = info.model_dump_json()
        json_data = json.loads(json_str)

        submitted_str = json_data['submitted_at']
        assert (submitted_str.endswith('Z') or '+00:00' in submitted_str or
                submitted_str.endswith('+00:00')), \
            f"submitted_at missing timezone info: {submitted_str}"

    def test_none_datetime_serialization(self):
        """Test that None datetime fields are properly serialized."""
        status = JobStatus(
            job_id="test_job",
            status="queued",
            submitted_at=None,
            completed_at=None
        )

        json_str = status.model_dump_json()
        json_data = json.loads(json_str)

        assert json_data['submitted_at'] is None
        assert json_data['completed_at'] is None


class TestTimezoneConsistency:
    """Test timezone consistency across operations."""

    def test_utc_consistency(self):
        """Test that all datetime objects use UTC timezone."""
        dt1 = datetime.now(timezone.utc)
        dt2 = datetime.fromtimestamp(1697280000.0, tz=timezone.utc)

        assert dt1.tzinfo == timezone.utc
        assert dt2.tzinfo == timezone.utc

        # Verify both are comparable (same timezone)
        assert dt1 > dt2  # dt1 is more recent

    def test_isoformat_output(self):
        """Test that isoformat() produces correct timezone representation."""
        dt = datetime(2023, 10, 14, 12, 0, 0, tzinfo=timezone.utc)
        iso_str = dt.isoformat()

        # Should end with +00:00 for UTC
        assert iso_str.endswith('+00:00'), f"ISO format incorrect: {iso_str}"
        assert '2023-10-14' in iso_str
        assert '12:00:00' in iso_str
