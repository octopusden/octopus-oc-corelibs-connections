
import os
from oc_connections.CredentialManager import CredentialManager
from unittest import TestCase
from sys import version_info


class CredentialManagerTestSuite(TestCase):

    if version_info.major == 3:
        def assertItemsEqual(self, expected_seq, actual_seq, msg=None):
            return self.assertCountEqual( actual_seq, expected_seq, msg=msg );
        
    def setUp(self):
        self.cred_mgr = CredentialManager()

    def test_get_credential(self):
        os.environ["full_name"] = "value"
        self.assertEqual("value", self.cred_mgr.get_credential("full", "name"))

    def test_get_reset_credential(self):
        os.environ["full_name"] = "value"
        self.cred_mgr.reset_credential("full", "name")
        self.assertEqual("value", self.cred_mgr.get_credential("full", "name"))

    def test_get_overridden_credential(self):
        os.environ["full_name"] = "value"
        self.cred_mgr.override_credential("full", "name", "overriding_value")
        self.assertEqual("overriding_value", self.cred_mgr.get_credential("full", "name"))

    def test_get_overridden_and_reset_credential(self):
        os.environ["full_name"] = "value"
        self.cred_mgr.override_credential("full", "name", "overriding_value")
        self.cred_mgr.reset_credential("full", "name")
        self.assertEqual("value", self.cred_mgr.get_credential("full", "name"))

    def test_get_overridden_and_overridden_credential(self):
        os.environ["full_name"] = "value"
        self.cred_mgr.override_credential("full", "name", "overriding_value")
        self.cred_mgr.override_credential("full", "name", "overriding_2_value")
        self.assertEqual("overriding_2_value", self.cred_mgr.get_credential("full", "name"))

    def test_get_credentials(self):
        os.environ["full_name"] = "value"
        os.environ["full_name_2"] = "value_2"
        self.assertItemsEqual(["value", "value_2"], self.cred_mgr.get_credentials("full", ["name", "name_2"]))

    def test_get_reset_credentials(self):
        os.environ["full_name"] = "value"
        os.environ["full_name_2"] = "value_2"
        self.cred_mgr.reset_credentials("full", ["name", "name_2"])
        self.assertItemsEqual(["value", "value_2"], self.cred_mgr.get_credentials("full", ["name", "name_2"]))

    def test_get_overridden_and_reset_credentials(self):
        os.environ["full_name"] = "value"
        os.environ["full_name_2"] = "value_2"
        self.cred_mgr.override_credential("full", "name", "overriding_value")
        self.cred_mgr.override_credential("full", "name_2", "overriding_value_2")
        self.cred_mgr.reset_credentials("full", ["name", "name_2"])
        self.assertItemsEqual(["value", "value_2"], self.cred_mgr.get_credentials("full", ["name", "name_2"]))

    def test_missing_credential(self):
        value=self.cred_mgr.get_credential("foo", "bar")
        self.assertIsNone(value)
