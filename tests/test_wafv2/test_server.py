import unittest

import pytest

import moto.server as server
from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from .test_helper_functions import CREATE_WEB_ACL_BODY

CREATE_WEB_ACL_HEADERS = {
    "X-Amz-Target": "AWSWAF_20190729.CreateWebACL",
    "Content-Type": "application/json",
}


LIST_WEB_ACL_HEADERS = {
    "X-Amz-Target": "AWSWAF_20190729.ListWebACLs",
    "Content-Type": "application/json",
}


@pytest.fixture(scope="function", autouse=True)
def skip_in_server_mode():
    if settings.TEST_SERVER_MODE:
        raise unittest.SkipTest("No point testing this in ServerMode")


@mock_aws
def test_create_web_acl():
    backend = server.create_backend_app("wafv2")
    test_client = backend.test_client()

    res = test_client.post(
        "/",
        headers=CREATE_WEB_ACL_HEADERS,
        json=CREATE_WEB_ACL_BODY("John", "REGIONAL"),
    )
    assert res.status_code == 200

    web_acl = res.json["Summary"]
    assert web_acl.get("Name") == "John"
    assert web_acl.get("ARN").startswith(
        f"arn:aws:wafv2:us-east-1:{ACCOUNT_ID}:regional/webacl/John/"
    )

    # Duplicate name - should raise error
    res = test_client.post(
        "/",
        headers=CREATE_WEB_ACL_HEADERS,
        json=CREATE_WEB_ACL_BODY("John", "REGIONAL"),
    )
    assert res.status_code == 400
    assert (
        b"AWS WAF could not perform the operation because some resource "
        b"in your request is a duplicate of an existing one."
    ) in res.data
    assert b"WafV2DuplicateItem" in res.data

    res = test_client.post(
        "/",
        headers=CREATE_WEB_ACL_HEADERS,
        json=CREATE_WEB_ACL_BODY("Carl", "CLOUDFRONT"),
    )
    web_acl = res.json["Summary"]
    assert web_acl.get("ARN").startswith(
        f"arn:aws:wafv2:us-east-1:{ACCOUNT_ID}:global/webacl/Carl/"
    )


@mock_aws
def test_list_web_ac_ls():
    backend = server.create_backend_app("wafv2")
    test_client = backend.test_client()

    test_client.post(
        "/",
        headers=CREATE_WEB_ACL_HEADERS,
        json=CREATE_WEB_ACL_BODY("John", "REGIONAL"),
    )
    test_client.post(
        "/",
        headers=CREATE_WEB_ACL_HEADERS,
        json=CREATE_WEB_ACL_BODY("JohnSon", "REGIONAL"),
    )
    test_client.post(
        "/",
        headers=CREATE_WEB_ACL_HEADERS,
        json=CREATE_WEB_ACL_BODY("Sarah", "CLOUDFRONT"),
    )
    res = test_client.post(
        "/", headers=LIST_WEB_ACL_HEADERS, json={"Scope": "REGIONAL"}
    )
    assert res.status_code == 200

    web_acls = res.json["WebACLs"]
    assert len(web_acls) == 2
    assert web_acls[0]["Name"] == "John"
    assert web_acls[1]["Name"] == "JohnSon"

    res = test_client.post(
        "/", headers=LIST_WEB_ACL_HEADERS, json={"Scope": "CLOUDFRONT"}
    )
    assert res.status_code == 200
    web_acls = res.json["WebACLs"]
    assert len(web_acls) == 1
    assert web_acls[0]["Name"] == "Sarah"
