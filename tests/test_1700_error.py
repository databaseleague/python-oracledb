#------------------------------------------------------------------------------
# Copyright (c) 2020, 2023, Oracle and/or its affiliates.
#
# This software is dual-licensed to you under the Universal Permissive License
# (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl and Apache License
# 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose
# either license.
#
# If you elect to accept the software under the Apache License, Version 2.0,
# the following applies:
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#------------------------------------------------------------------------------

"""
1700 - Module for testing error objects
"""

import pickle
import unittest

import oracledb
import test_env

class TestCase(test_env.BaseTestCase):

    def test_1700_parse_error(self):
        "1700 - test parse error returns offset correctly"
        with self.assertRaises(oracledb.Error) as cm:
            self.cursor.execute("begin t_Missing := 5; end;")
        error_obj, = cm.exception.args
        self.assertEqual(error_obj.full_code, "ORA-06550")
        self.assertEqual(error_obj.offset, 6)

    def test_1701_pickle_error(self):
        "1701 - test picking/unpickling an error object"
        with self.assertRaises(oracledb.Error) as cm:
            self.cursor.execute("""
                    begin
                        raise_application_error(-20101, 'Test!');
                    end;""")
        error_obj, = cm.exception.args
        self.assertIsInstance(error_obj, oracledb._Error)
        self.assertIn("Test!", error_obj.message)
        self.assertEqual(error_obj.code, 20101)
        self.assertEqual(error_obj.offset, 0)
        self.assertIsInstance(error_obj.isrecoverable, bool)
        new_error_obj = pickle.loads(pickle.dumps(error_obj))
        self.assertIsInstance(new_error_obj, oracledb._Error)
        self.assertEqual(new_error_obj.message, error_obj.message)
        self.assertEqual(new_error_obj.code, error_obj.code)
        self.assertEqual(new_error_obj.offset, error_obj.offset)
        self.assertEqual(new_error_obj.context, error_obj.context)
        self.assertEqual(new_error_obj.isrecoverable, error_obj.isrecoverable)

    def test_1702_error_full_code(self):
        "1702 - test generation of full_code for ORA, DPI and DPY errors"
        cursor = self.conn.cursor()
        with self.assertRaises(oracledb.Error) as cm:
            cursor.execute(None)
        error_obj, = cm.exception.args
        self.assertEqual(error_obj.full_code, "DPY-2001")
        if not self.conn.thin:
            with self.assertRaises(oracledb.Error) as cm:
                cursor.execute("truncate table TestTempTable")
                int_var = cursor.var(int)
                str_var = cursor.var(str, 2)
                cursor.execute("""
                        insert into TestTempTable (IntCol, StringCol1)
                        values (1, 'Longer than two chars')
                        returning IntCol, StringCol1
                        into :int_var, :str_var""",
                        int_var=int_var, str_var=str_var)
            error_obj, = cm.exception.args
            self.assertEqual(error_obj.full_code, "DPI-1037")

    @unittest.skipIf(test_env.get_client_version() < (23, 1),
                     "unsupported client")
    def test_1703_error_help_url(self):
        "1703 - test generation of error help portal URL"
        cursor = self.conn.cursor()
        with self.assertRaises(oracledb.Error) as cm:
            cursor.execute("select 1 / 0 from dual")
        error_obj, = cm.exception.args
        to_check = "Help: https://docs.oracle.com/error-help/db/ora-01476/"
        self.assertIn(to_check, error_obj.message)

if __name__ == "__main__":
    test_env.run_test_cases()
