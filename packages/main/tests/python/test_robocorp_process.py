from unittest.mock import Mock, call

import pytest
from requests import HTTPError

from RPA.Robocorp.Process import Process


@pytest.fixture
def process():
    library = Process("workspace", "process", "api-key")
    library.http = Mock()
    return library


def response(data, **kwargs):
    result = Mock()
    result.json.return_value = {"data": data, **kwargs}
    return result


@pytest.mark.parametrize("pagination", [{}, {"nextCursor": None}, {"nextCursor": ""}])
@pytest.mark.parametrize("items", [[], [{"id": "1", "state": "COMPLETED"}]])
def test_list_process_work_items_single_page(process, pagination, items):
    result = response(items, **pagination)
    process.http.session_less_get.return_value = result

    assert process.list_process_work_items() == items
    process.http.session_less_get.assert_called_once_with(
        url=f"{process.process_api()}/work-items",
        headers=process.headers,
        params={"includeData": "false"},
    )
    result.raise_for_status.assert_called_once_with()


@pytest.mark.parametrize("include_data", [False, True])
@pytest.mark.parametrize("item_state", [None, "failed", "COMPLETED"])
def test_list_process_work_items_all_pages(process, include_data, item_state):
    first_items = [{"id": str(index), "state": "COMPLETED"} for index in range(100)]
    last_items = [{"id": "100", "state": "FAILED"}]
    pages = [
        response(first_items, nextCursor="page-2"),
        response([], nextCursor="page-3"),
        response(last_items, nextCursor=None),
    ]
    process.http.session_less_get.side_effect = pages

    items = process.list_process_work_items(
        process_id="other-process", include_data=include_data, item_state=item_state
    )

    expected = first_items + last_items
    if item_state:
        expected = [item for item in expected if item["state"] == item_state.upper()]
    assert items == expected
    params = {"includeData": str(include_data).lower()}
    url = f"{process.process_api('other-process')}/work-items"
    assert process.http.session_less_get.call_args_list == [
        call(url=url, headers=process.headers, params=params),
        call(url=url, headers=process.headers, params={**params, "cursor": "page-2"}),
        call(url=url, headers=process.headers, params={**params, "cursor": "page-3"}),
    ]
    for page in pages:
        page.raise_for_status.assert_called_once_with()


def test_list_process_work_items_later_page_error(process):
    first = response([{"id": "1", "state": "COMPLETED"}], nextCursor="page-2")
    second = response([])
    second.raise_for_status.side_effect = HTTPError("page request failed")
    process.http.session_less_get.side_effect = [first, second]

    with pytest.raises(HTTPError, match="page request failed"):
        process.list_process_work_items()

    assert process.http.session_less_get.call_count == 2
    second.json.assert_not_called()
