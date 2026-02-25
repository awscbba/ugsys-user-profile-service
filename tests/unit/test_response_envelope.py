"""Unit tests for response envelope utilities."""

from src.presentation.response_envelope import list_response, success_response


def test_success_response_wraps_data():
    result = success_response(data={"id": "123"}, request_id="req-abc")
    assert result["data"] == {"id": "123"}
    assert result["meta"]["request_id"] == "req-abc"


def test_success_response_default_request_id():
    result = success_response(data="hello")
    assert result["meta"]["request_id"] == ""


def test_list_response_pagination_metadata():
    result = list_response(data=[1, 2, 3], total=50, page=2, page_size=10, request_id="r1")
    assert result["data"] == [1, 2, 3]
    assert result["meta"]["total"] == 50
    assert result["meta"]["page"] == 2
    assert result["meta"]["page_size"] == 10
    assert result["meta"]["total_pages"] == 5
    assert result["meta"]["request_id"] == "r1"


def test_list_response_total_pages_ceiling():
    result = list_response(data=[], total=21, page=1, page_size=10)
    assert result["meta"]["total_pages"] == 3


def test_list_response_zero_page_size():
    result = list_response(data=[], total=10, page=1, page_size=0)
    assert result["meta"]["total_pages"] == 0
