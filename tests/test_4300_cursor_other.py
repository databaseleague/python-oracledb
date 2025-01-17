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
4300 - Module for testing other cursor methods and attributes.
"""

import decimal
import unittest

import oracledb
import test_env

class TestCase(test_env.BaseTestCase):

    def tearDown(self):
        super().tearDown()
        oracledb.__future__.old_json_col_as_obj = False

    def test_4300_prepare(self):
        "4300 - test preparing a statement and executing it multiple times"
        cursor = self.conn.cursor()
        self.assertEqual(cursor.statement, None)
        statement = "begin :value := :value + 5; end;"
        cursor.prepare(statement)
        var = cursor.var(oracledb.NUMBER)
        self.assertEqual(cursor.statement, statement)
        var.setvalue(0, 2)
        cursor.execute(None, value = var)
        self.assertEqual(var.getvalue(), 7)
        cursor.execute(None, value = var)
        self.assertEqual(var.getvalue(), 12)
        cursor.execute("begin :value2 := 3; end;", value2 = var)
        self.assertEqual(var.getvalue(), 3)

    def test_4301_exception_on_close(self):
        "4301 - confirm an exception is raised after closing a cursor"
        self.cursor.close()
        self.assertRaisesRegex(oracledb.InterfaceError, "^DPY-1006:",
                               self.cursor.execute, "select 1 from dual")

    def test_4302_iterators(self):
        "4302 - test iterators"
        self.cursor.execute("""
                select IntCol
                from TestNumbers
                where IntCol between 1 and 3
                order by IntCol""")
        rows = [v for v, in self.cursor]
        self.assertEqual(rows, [1, 2, 3])

    def test_4303_iterators_interrupted(self):
        "4303 - test iterators (with intermediate execute)"
        self.cursor.execute("truncate table TestTempTable")
        self.cursor.execute("""
                select IntCol
                from TestNumbers
                where IntCol between 1 and 3
                order by IntCol""")
        test_iter = iter(self.cursor)
        value, = next(test_iter)
        self.cursor.execute("insert into TestTempTable (IntCol) values (1)")
        self.assertRaisesRegex(oracledb.InterfaceError, "^DPY-1003:", next,
                               test_iter)

    def test_4304_bind_names(self):
        "4304 - test that bindnames() works correctly."
        cursor = self.conn.cursor()
        self.assertRaisesRegex(oracledb.ProgrammingError, "^DPY-2002:",
                               cursor.bindnames)
        cursor.prepare("begin null; end;")
        self.assertEqual(cursor.bindnames(), [])
        cursor.prepare("begin :retval := :inval + 5; end;")
        self.assertEqual(cursor.bindnames(), ["RETVAL", "INVAL"])
        cursor.prepare("begin :retval := :a * :a + :b * :b; end;")
        self.assertEqual(cursor.bindnames(), ["RETVAL", "A", "B"])
        cursor.prepare("""
                begin
                    :a := :b + :c + :d + :e + :f + :g + :h + :i + :j + :k
                        + :l;
                end;""")
        names = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
        self.assertEqual(cursor.bindnames(), names)
        cursor.prepare("select :a * :a + :b * :b from dual")
        self.assertEqual(cursor.bindnames(), ["A", "B"])
        cursor.prepare("select :value1 + :VaLue_2 from dual")
        self.assertEqual(cursor.bindnames(), ["VALUE1", "VALUE_2"])
        cursor.prepare("select :élevé, :fenêtre from dual")
        self.assertEqual(cursor.bindnames(), ["ÉLEVÉ", "FENÊTRE"])

    def test_4305_set_input_sizes_negative(self):
        "4305 - test cursor.setinputsizes() with invalid parameters"
        val = decimal.Decimal(5)
        self.assertRaisesRegex(oracledb.ProgrammingError, "^DPY-2005:",
                               self.cursor.setinputsizes, val, x=val)
        self.assertRaisesRegex(oracledb.ProgrammingError, "^DPY-2007:",
                               self.cursor.setinputsizes, val)

    def test_4306_set_input_sizes_no_parameters(self):
        "4306 - test setting input sizes without any parameters"
        self.cursor.setinputsizes()
        self.cursor.execute("select :val from dual", val="Test Value")
        self.assertEqual(self.cursor.fetchall(), [("Test Value",)])

    def test_4307_set_input_sizes_empty_dict(self):
        "4307 - test setting input sizes with an empty dictionary"
        empty_dict = {}
        self.cursor.prepare("select 236 from dual")
        self.cursor.setinputsizes(**empty_dict)
        self.cursor.execute(None, empty_dict)
        self.assertEqual(self.cursor.fetchall(), [(236,)])

    def test_4308_set_input_sizes_empty_list(self):
        "4308 - test setting input sizes with an empty list"
        empty_list = []
        self.cursor.prepare("select 239 from dual")
        self.cursor.setinputsizes(*empty_list)
        self.cursor.execute(None, empty_list)
        self.assertEqual(self.cursor.fetchall(), [(239,)])

    def test_4309_set_input_sizes_by_position(self):
        "4309 - test setting input sizes with positional args"
        var = self.cursor.var(oracledb.STRING, 100)
        self.cursor.setinputsizes(None, 5, None, 10, None, oracledb.NUMBER)
        self.cursor.execute("""
                begin
                  :1 := :2 || to_char(:3) || :4 || to_char(:5) || to_char(:6);
                end;""", [var, 'test_', 5, '_second_', 3, 7])
        self.assertEqual(var.getvalue(), "test_5_second_37")

    def test_4310_repr(self):
        "4310 - test Cursor repr()"
        expected_value = f"<oracledb.Cursor on {self.conn}>"
        self.assertEqual(str(self.cursor), expected_value)
        self.assertEqual(repr(self.cursor), expected_value)

    def test_4311_parse_query(self):
        "4311 - test parsing query statements"
        sql = "select LongIntCol from TestNumbers where IntCol = :val"
        self.cursor.parse(sql)
        self.assertEqual(self.cursor.statement, sql)
        self.assertEqual(self.cursor.description,
                         [('LONGINTCOL', oracledb.DB_TYPE_NUMBER, 17, None,
                           16, 0, 0)])

    def test_4312_set_output_size(self):
        "4312 - test cursor.setoutputsize() does not fail (but does nothing)"
        self.cursor.setoutputsize(100, 2)

    def test_4313_var_negative(self):
        "4313 - test cursor.var() with invalid parameters"
        self.assertRaisesRegex(oracledb.ProgrammingError, "^DPY-2007:",
                               self.cursor.var, 5)

    def test_4314_arrayvar_negative(self):
        "4314 - test cursor.arrayvar() with invalid parameters"
        self.assertRaisesRegex(oracledb.ProgrammingError, "^DPY-2007:",
                               self.cursor.arrayvar, 5, 1)

    def test_4315_boolean_without_plsql(self):
        "4315 - test binding boolean data without the use of PL/SQL"
        self.cursor.execute("truncate table TestTempTable")
        sql = "insert into TestTempTable (IntCol, StringCol1) values (:1, :2)"
        self.cursor.execute(sql, (False, "Value should be 0"))
        self.cursor.execute(sql, (True, "Value should be 1"))
        self.cursor.execute("""
                select IntCol, StringCol1
                from TestTempTable
                order by IntCol""")
        expected_value = [(0, "Value should be 0"), (1, "Value should be 1")]
        self.assertEqual(self.cursor.fetchall(), expected_value)

    def test_4316_as_context_manager(self):
        "4316 - test using a cursor as a context manager"
        with self.cursor as cursor:
            cursor.execute("truncate table TestTempTable")
            cursor.execute("select count(*) from TestTempTable")
            count, = cursor.fetchone()
            self.assertEqual(count, 0)
        self.assertRaisesRegex(oracledb.InterfaceError, "^DPY-1006:",
                               self.cursor.close)

    def test_4317_query_row_count(self):
        "4317 - test that rowcount attribute is reset to zero on query execute"
        for num in [0, 1, 1, 0]:
            self.cursor.execute("select * from dual where 1 = :s", [num])
            self.cursor.fetchone()
            self.assertEqual(self.cursor.rowcount, num)

    def test_4318_var_type_name_none(self):
        "4318 - test that the typename attribute can be passed a value of None"
        value_to_set = 5
        var = self.cursor.var(int, typename=None)
        var.setvalue(0, value_to_set)
        self.assertEqual(var.getvalue(), value_to_set)

    def test_4319_var_type_with_object_type(self):
        "4319 - test that an object type can be used as type in cursor.var()"
        obj_type = self.conn.gettype("UDT_OBJECT")
        var = self.cursor.var(obj_type)
        self.cursor.callproc("pkg_TestBindObject.BindObjectOut",
                             (28, "Bind obj out", var))
        obj = var.getvalue()
        result = self.cursor.callfunc("pkg_TestBindObject.GetStringRep", str,
                                      (obj,))
        exp = "udt_Object(28, 'Bind obj out', null, null, null, null, null)"
        self.assertEqual(result, exp)

    def test_4320_fetch_xmltype(self):
        "4320 - test that fetching an XMLType returns a string"
        int_val = 5
        label = "IntCol"
        expected_result = f"<{label}>{int_val}</{label}>"
        self.cursor.execute(f"""
                select XMLElement("{label}", IntCol)
                from TestStrings
                where IntCol = :int_val""",
                int_val=int_val)
        result, = self.cursor.fetchone()
        self.assertEqual(result, expected_result)

    def test_4321_lastrowid(self):
        "4321 - test last rowid"

        # no statement executed: no rowid
        self.assertIsNone(self.cursor.lastrowid)

        # DDL statement executed: no rowid
        self.cursor.execute("truncate table TestTempTable")
        self.assertIsNone(self.cursor.lastrowid)

        # statement prepared: no rowid
        self.cursor.prepare("insert into TestTempTable (IntCol) values (:1)")
        self.assertIsNone(self.cursor.lastrowid)

        # multiple rows inserted: rowid of last row inserted
        rows = [(n,) for n in range(225)]
        self.cursor.executemany(None, rows)
        rowid = self.cursor.lastrowid
        self.cursor.execute("""
                select rowid
                from TestTempTable
                where IntCol = :1""", rows[-1])
        self.assertEqual(self.cursor.fetchone()[0], rowid)

        # statement executed but no rows updated: no rowid
        self.cursor.execute("delete from TestTempTable where 1 = 0")
        self.assertIsNone(self.cursor.lastrowid)

        # stetement executed with one row updated: rowid of updated row
        self.cursor.execute("""
                update TestTempTable set StringCol1 = 'Modified'
                where IntCol = :1""", rows[-2])
        rowid = self.cursor.lastrowid
        self.cursor.execute("""
                select rowid
                from TestTempTable
                where IntCol = :1""", rows[-2])
        self.assertEqual(self.cursor.fetchone()[0], rowid)

        # statement executed with many rows updated: rowid of last updated row
        self.cursor.execute("""
                update TestTempTable set
                    StringCol1 = 'Row ' || to_char(IntCol)
                where IntCol = :1""", rows[-3])
        rowid = self.cursor.lastrowid
        self.cursor.execute("""
                select StringCol1
                from TestTempTable
                where rowid = :1""", [rowid])
        self.assertEqual(self.cursor.fetchone()[0], "Row %s" % rows[-3])

    def test_4322_prefetchrows(self):
        "4322 - test prefetch rows"
        self.setup_round_trip_checker()

        # perform simple query and verify only one round trip is needed
        with self.conn.cursor() as cursor:
            cursor.execute("select sysdate from dual").fetchall()
            self.assertRoundTrips(1)

        # set prefetchrows to 1 and verify that two round trips are now needed
        with self.conn.cursor() as cursor:
            cursor.prefetchrows = 1
            cursor.execute("select sysdate from dual").fetchall()
            self.assertRoundTrips(2)

        # simple DDL only requires a single round trip
        with self.conn.cursor() as cursor:
            cursor.execute("truncate table TestTempTable")
            self.assertRoundTrips(1)

        # array execution only requires a single round trip
        num_rows = 590
        with self.conn.cursor() as cursor:
            data = [(n + 1,) for n in range(num_rows)]
            cursor.executemany("""
                    insert into TestTempTable (IntCol)
                    values (:1)""",
                    data)
            self.assertRoundTrips(1)

        # setting prefetch and array size to 1 requires a round-trip for each
        # row
        with self.conn.cursor() as cursor:
            cursor.prefetchrows = 1
            cursor.arraysize = 1
            cursor.execute("select IntCol from TestTempTable").fetchall()
            self.assertRoundTrips(num_rows + 1)

        # setting prefetch and array size to 300 requires 2 round-trips
        with self.conn.cursor() as cursor:
            cursor.prefetchrows = 300
            cursor.arraysize = 300
            cursor.execute("select IntCol from TestTempTable").fetchall()
            self.assertRoundTrips(2)

    def test_4323_existing_cursor_prefetchrows(self):
        "4323 - test prefetch rows using existing cursor"
        self.setup_round_trip_checker()

        # Set prefetch rows on an existing cursor
        num_rows = 590
        with self.conn.cursor() as cursor:
            cursor.execute("truncate table TestTempTable")
            self.assertRoundTrips(1)
            data = [(n + 1,) for n in range(num_rows)]
            cursor.executemany("""
                    insert into TestTempTable (IntCol)
                    values (:1)""",
                    data)
            self.assertRoundTrips(1)
            cursor.prefetchrows = 30
            cursor.arraysize = 100
            cursor.execute("select IntCol from TestTempTable").fetchall()
            self.assertRoundTrips(7)

    def test_4327_parse_plsql(self):
        "4327 - test parsing plsql statements"
        sql = "begin :value := 5; end;"
        self.cursor.parse(sql)
        self.assertEqual(self.cursor.statement, sql)
        self.assertIsNone(self.cursor.description)

    def test_4328_parse_ddl(self):
        "4328 - test parsing ddl statements"
        sql = "truncate table TestTempTable"
        self.cursor.parse(sql)
        self.assertEqual(self.cursor.statement, sql)
        self.assertIsNone(self.cursor.description)

    def test_4329_parse_dml(self):
        "4329 - test parsing dml statements"
        sql = "insert into TestTempTable (IntCol) values (1)"
        self.cursor.parse(sql)
        self.assertEqual(self.cursor.statement, sql)
        self.assertIsNone(self.cursor.description)

    def test_4330_encodingErrors_deprecation(self):
        "4330 - test to verify encodingErrors is deprecated"
        errors = 'strict'
        self.assertRaisesRegex(oracledb.ProgrammingError, "^DPY-2014:",
                               self.cursor.var, oracledb.NUMBER,
                               encoding_errors=errors, encodingErrors=errors)

    def test_4331_unsupported_arrays_of_arrays(self):
        "4331 - test arrays of arrays not supported"
        simple_var = self.cursor.arrayvar(oracledb.NUMBER, 3)
        self.assertRaisesRegex(oracledb.NotSupportedError, "^DPY-3005:",
                               simple_var.setvalue, 1, [1, 2, 3])

    def test_4332_set_input_sizes_with_invalid_list_parameters(self):
        "4332 - test cursor.setinputsizes() with invalid list parameters"
        self.assertRaisesRegex(oracledb.ProgrammingError, "^DPY-2011:",
                               self.cursor.setinputsizes, [int, 2, 10])

    def test_4333_unsupported_python_type(self):
        "4333 - test unsupported python type on cursor"
        self.assertRaisesRegex(oracledb.NotSupportedError, "^DPY-3003:",
                               self.cursor.var, list)

    def test_4334_bind_by_name_with_leading_colon(self):
        "4334 - test binding by name with leading colon"
        params = {":arg1" : 5}
        self.cursor.execute("select :arg1 from dual", params)
        result, = self.cursor.fetchone()
        self.assertEqual(result, params[":arg1"])

    def test_4335_bind_out_mixed_null_not_null(self):
        "4335 - test binding mixed null and not null values in a PL/SQL block"
        out_vars = [self.cursor.var(str) for i in range(4)]
        self.cursor.execute("""
                begin
                    :1 := null;
                    :2 := 'Value 1';
                    :3 := null;
                    :4 := 'Value 2';
                end;""",
                out_vars)
        values = [var.getvalue() for var in out_vars]
        self.assertEqual(values, [None, 'Value 1', None, 'Value 2'])

    def test_4337_exclude_from_stmt_cache(self):
        "4337 - test excluding statement from statement cache"
        num_iters = 10
        sql = "select user from dual"
        self.setup_parse_count_checker()

        # with statement cache enabled, only one parse should take place
        for i in range(num_iters):
            with self.conn.cursor() as cursor:
                cursor.execute(sql)
        self.assertParseCount(1)

        # with statement cache disabled for the statement, parse count should
        # be the same as the number of iterations
        for i in range(num_iters):
            with self.conn.cursor() as cursor:
                cursor.prepare(sql, cache_statement=False)
                cursor.execute(None)
        self.assertParseCount(num_iters - 1)

    def test_4339_repeated_ddl(self):
        "4339 - test repeated DDL"
        self.cursor.execute("truncate table TestTempTable")
        self.cursor.execute("insert into TestTempTable (IntCol) values (1)")
        self.cursor.execute("truncate table TestTempTable")
        self.cursor.execute("insert into TestTempTable (IntCol) values (1)")

    def test_4340_sql_with_non_ascii_chars(self):
        "4340 - test executing SQL with non-ASCII characters"
        self.cursor.execute("select 'FÖÖ' from dual")
        result, = self.cursor.fetchone()
        self.assertIn(result, ('FÖÖ', 'F¿¿'))

    def test_4341_unquoted_binds_case_sensitivity(self):
        "4341 - test case sensitivity of unquoted bind names"
        self.cursor.execute("select :test from dual", {"TEST": "a"})
        result, = self.cursor.fetchone()
        self.assertEqual(result, "a")

    def test_4342_quoted_binds_case_sensitivity(self):
        "4342 - test case sensitivity of quoted bind names"
        self.assertRaisesRegex(oracledb.DatabaseError,
                               "^ORA-01036:|^DPY-4008:", self.cursor.execute,
                               'select :"test" from dual', {'"TEST"': "a"})

    def test_4343_reserved_keyword_as_bind_name(self):
        "4343 - test using a reserved keywords as a bind name"
        sql = 'select :ROWID from dual'
        self.assertRaisesRegex(oracledb.DatabaseError,
                               "^ORA-01745:", self.cursor.parse, sql)

    def test_4347_arraysize_lt_prefetchrows(self):
        "4347 - test array size less than prefetch rows"
        for i in range(2):
            with self.conn.cursor() as cursor:
                cursor.arraysize = 1
                cursor.execute("select 1 from dual union select 2 from dual")
                self.assertEqual(cursor.fetchall(), [(1,), (2,)])

    def test_4348_reexecute_query_with_blob_as_bytes(self):
        "4348 - test re-executing a query with blob as bytes"
        def type_handler(cursor, metadata):
            if metadata.type_code is oracledb.DB_TYPE_BLOB:
                return cursor.var(bytes, arraysize=cursor.arraysize)

        self.conn.outputtypehandler = type_handler
        blob_data = b"An arbitrary set of blob data for test case 4348"
        self.cursor.execute("truncate table TestBLOBs")
        self.cursor.execute("""
                insert into TestBLOBs
                (IntCol, BlobCol)
                values (1, :data)""",
                [blob_data])
        self.cursor.execute("select IntCol, BlobCol from TestBLOBs")
        self.assertEqual(self.cursor.fetchall(), [(1, blob_data)])

        self.cursor.execute("truncate table TestBLOBs")
        self.cursor.execute("""
                insert into TestBLOBs
                (IntCol, BlobCol)
                values (1, :data)""",
                [blob_data])
        self.cursor.execute("select IntCol, BlobCol from TestBLOBs")
        self.assertEqual(self.cursor.fetchall(), [(1, blob_data)])

    def test_4350_reexecute_after_error(self):
        "4350 - test re-executing a statement after raising an error"
        sql = "select * from TestFakeTable"
        self.assertRaisesRegex(oracledb.DatabaseError, "^ORA-00942:",
                               self.cursor.execute, sql)
        self.assertRaisesRegex(oracledb.DatabaseError, "^ORA-00942:",
                               self.cursor.execute, sql)

        sql = "insert into TestStrings (StringCol) values (NULL)"
        self.assertRaisesRegex(oracledb.DatabaseError, "^ORA-01400:",
                               self.cursor.execute, sql)
        self.assertRaisesRegex(oracledb.DatabaseError, "^ORA-01400:",
                               self.cursor.execute, sql)

    def test_4351_variable_not_in_select_list(self):
        "4351 - test executing a statement that raises ORA-01007"
        with self.conn.cursor() as cursor:
            cursor.execute("""
                    create or replace view ora_1007 as
                        select 1 as SampleNumber, 'String' as SampleString,
                            'Another String' as AnotherString
                        from dual""")
        with self.conn.cursor() as cursor:
            cursor.execute("select * from ora_1007")
            self.assertEqual(cursor.fetchone(),
                             (1, 'String', 'Another String'))
        with self.conn.cursor() as cursor:
            cursor.execute("""
                    create or replace view ora_1007 as
                        select 1 as SampleNumber,
                            'Another String' as AnotherString
                        from dual""")
        with self.conn.cursor() as cursor:
            cursor.execute("select * from ora_1007")
            self.assertEqual(cursor.fetchone(), (1, 'Another String'))

    def test_4352_update_empty_row(self):
        "4352 - test updating an empty row"
        int_var = self.cursor.var(int)
        self.cursor.execute("truncate table TestTempTable")
        self.cursor.execute("""
                begin
                    update TestTempTable set IntCol = :1
                    where StringCol1 = :2
                    returning IntCol into :3;
                end;""",
                [1, "test string 4352", int_var])
        self.assertEqual(int_var.values, [None])

    def test_4354_fetch_duplicate_data_twice(self):
        "4354 - fetch duplicate data from query in statement cache"
        sql = """
                select 'A', 'B', 'C' from dual
                union all
                select 'A', 'B', 'C' from dual
                union all
                select 'A', 'B', 'C' from dual"""
        expected_data = [('A', 'B', 'C')] * 3
        with self.conn.cursor() as cursor:
            cursor.prefetchrows = 0
            cursor.execute(sql)
            self.assertEqual(cursor.fetchall(), expected_data)
        with self.conn.cursor() as cursor:
            cursor.prefetchrows = 0
            cursor.execute(sql)
            self.assertEqual(cursor.fetchall(), expected_data)

    def test_4355_fetch_duplicate_data_with_out_converter(self):
        "4355 - fetch duplicate data with outconverter"
        def out_converter(value):
            self.assertIs(type(value), str)
            return int(value)

        def type_handler(cursor, metadata):
            if metadata.name == "COL_3":
                return cursor.var(str, arraysize=cursor.arraysize,
                                  outconverter=out_converter)

        self.cursor.outputtypehandler = type_handler
        self.cursor.execute("""
                select 'A' as col_1, 2 as col_2, 3 as col_3 from dual
                    union all
                select 'A' as col_1, 2 as col_2, 3 as col_3 from dual
                    union all
                select 'A' as col_1, 2 as col_2, 3 as col_3 from dual""")
        expected_data = [('A', 2, 3)] * 3
        self.assertEqual(self.cursor.fetchall(), expected_data)

    def test_4357_setinputsizes_with_defaults(self):
        "4357 - test setinputsizes() with defaults specified"
        self.cursor.setinputsizes(None, str)
        self.assertIsNone(self.cursor.bindvars[0])
        self.assertIsInstance(self.cursor.bindvars[1], oracledb.Var)
        self.cursor.setinputsizes(a=None, b=str)
        self.assertIsNone(self.cursor.bindvars.get("a"))
        self.assertIsInstance(self.cursor.bindvars["b"], oracledb.Var)

    def test_4358_kill_conn_with_open_cursor(self):
        "4538 - kill connection with open cursor"
        admin_conn = test_env.get_admin_connection()
        conn = test_env.get_connection()
        self.assertEqual(conn.is_healthy(), True)
        cursor = conn.cursor()
        cursor.execute("""
                select
                    dbms_debug_jdwp.current_session_id,
                    dbms_debug_jdwp.current_session_serial
                from dual""")
        sid, serial = cursor.fetchone()
        with admin_conn.cursor() as admin_cursor:
            sql = f"alter system kill session '{sid},{serial}'"
            admin_cursor.execute(sql)
        self.assertRaisesRegex(oracledb.DatabaseError, "^DPY-4011:",
                               cursor.execute, "select user from dual")
        self.assertFalse(conn.is_healthy())

    def test_4359_kill_conn_in_context_manager(self):
        "4359 - kill connection in cursor context manager"
        admin_conn = test_env.get_admin_connection()
        conn = test_env.get_connection()
        self.assertEqual(conn.is_healthy(), True)
        with conn.cursor() as cursor:
            cursor.execute("""
                    select
                        dbms_debug_jdwp.current_session_id,
                        dbms_debug_jdwp.current_session_serial
                    from dual""")
            sid, serial = cursor.fetchone()
            with admin_conn.cursor() as admin_cursor:
                admin_cursor.execute(f"""
                        alter system kill session '{sid},{serial}'""")
            self.assertRaisesRegex(oracledb.DatabaseError, "^DPY-4011:",
                                   cursor.execute, "select user from dual")
            self.assertEqual(conn.is_healthy(), False)

    def test_4360_fetchmany(self):
        "4360 - fetchmany() with and without parameters"
        sql_part = "select user from dual"
        sql = " union all ".join([sql_part] * 10)
        with self.conn.cursor() as cursor:
            cursor.arraysize = 6
            cursor.execute(sql)
            rows = cursor.fetchmany()
            self.assertEqual(len(rows), cursor.arraysize)
            cursor.execute(sql)
            rows = cursor.fetchmany(size=2)
            self.assertEqual(len(rows), 2)
            cursor.execute(sql)
            rows = cursor.fetchmany(numRows=4)
            self.assertEqual(len(rows), 4)
            cursor.execute(sql)
            self.assertRaisesRegex(oracledb.DatabaseError, "^DPY-2014:",
                                   cursor.fetchmany, size=2, numRows=4)

    def test_4361_rowcount_after_close(self):
        "4361 - access cursor.rowcount after closing cursor"
        with self.conn.cursor() as cursor:
            cursor.execute("select user from dual")
            cursor.fetchall()
            self.assertEqual(cursor.rowcount, 1)
        self.assertEqual(cursor.rowcount, -1)

    def test_4362_change_of_bind_type_with_define(self):
        "4362 - changing bind type with define needed"
        self.cursor.execute("truncate table TestClobs")
        row_for_1 = (1, "Short value 1")
        row_for_56 = (56, "Short value 56")
        for data in (row_for_1, row_for_56):
            self.cursor.execute("""
                    insert into TestClobs (IntCol, ClobCol)
                    values (:1, :2)""", data)
        sql = "select IntCol, ClobCol from TestClobs where IntCol = :int_col"
        with test_env.FetchLobsContextManager(False):
            self.cursor.execute(sql, int_col="1")
            self.assertEqual(self.cursor.fetchone(), row_for_1)
            self.cursor.execute(sql, int_col="56")
            self.assertEqual(self.cursor.fetchone(), row_for_56)
            self.cursor.execute(sql, int_col=1)
            self.assertEqual(self.cursor.fetchone(), row_for_1)

    def test_4363_multiple_parse(self):
        "4363 - test calling cursor.parse() twice with the same statement"
        self.cursor.execute("truncate table TestTempTable")
        data = (4363, "Value for test 4363")
        self.cursor.execute("""
                insert into TestTempTable (IntCol, StringCol1)
                values (:1, :2)""", data)
        sql = "update TestTempTable set StringCol1 = :v where IntCol = :i"
        for i in range(2):
            self.cursor.parse(sql)
            self.cursor.execute(sql, ("Updated value", data[0]))

    def test_4365_add_column_to_cached_query(self):
        "4365 - test addition of column to cached query"
        table_name = "test_4365"
        try:
            self.cursor.execute(f"drop table {table_name}")
        except:
            pass
        data = ('val 1', 'val 2')
        self.cursor.execute(f"create table {table_name} (col1 varchar2(10))")
        self.cursor.execute(f"insert into {table_name} values (:1)", [data[0]])
        self.conn.commit()
        self.cursor.execute(f"select * from {table_name}")
        self.assertEqual(self.cursor.fetchall(), [(data[0],)])
        self.cursor.execute(f"alter table {table_name} add col2 varchar2(10)")
        self.cursor.execute(f"update {table_name} set col2 = :1", [data[1]])
        self.conn.commit()
        self.cursor.execute(f"select * from {table_name}")
        self.assertEqual(self.cursor.fetchall(), [data])

    def test_4366_populate_array_var_with_too_many_elements(self):
        "4366 - test population of array var with too many elements"
        var = self.cursor.arrayvar(int, 3)
        self.assertRaisesRegex(oracledb.ProgrammingError, "^DPY-2016:",
                               var.setvalue, 0, [1, 2, 3, 4])

    def test_4367_plsql_with_executemany_and_increasing_sizes(self):
        "4367 - test executemany() with PL/SQL and increasing data lengths"
        sql = "begin :1 := length(:2); end;"
        var = self.cursor.var(int, arraysize=3)
        self.cursor.executemany(sql,
                                [(var, "one"), (var, "two"), (var, "end")])
        self.assertEqual(var.values, [3, 3, 3])
        self.cursor.executemany(sql,
                                [(var, "three"), (var, "four"), (var, "end")])
        self.assertEqual(var.values, [5, 4, 3])
        self.cursor.executemany(sql,
                                [(var, "five"), (var, "six"), (var, "end")])
        self.assertEqual(var.values, [4, 3, 3])

    def test_4368_cursor_rowcount_for_queries(self):
        "4368 - test cursor.rowcount values for queries"
        max_rows = 93
        self.cursor.arraysize = 10
        self.cursor.execute("""
                select rownum as id
                from dual connect by rownum <= :1""",
                [max_rows])
        self.assertEqual(self.cursor.rowcount, 0)
        batch_num = 1
        while True:
            rows = self.cursor.fetchmany()
            if not rows:
                break
            expected_value = min(max_rows, batch_num * self.cursor.arraysize)
            self.assertEqual(self.cursor.rowcount, expected_value)
            batch_num += 1
        self.cursor.fetchall()
        self.assertEqual(self.cursor.rowcount, max_rows)

    def test_4369_bind_order_for_plsql(self):
        "4369 - test bind order for PL/SQL"
        self.cursor.execute("truncate table TestClobs")
        sql = """
            insert into TestClobs (IntCol, CLOBCol, ExtraNumCol1)
            values (:1, :2, :3)"""
        data = "x" * 9000
        rows = [(1, data, 5), (2, data, 6)]
        self.cursor.execute(sql, rows[0])
        plsql = f"begin {sql}; end;"
        self.cursor.execute(plsql, rows[1])
        self.conn.commit()
        with test_env.FetchLobsContextManager(False):
            self.cursor.execute("""
                select IntCol, CLOBCol, ExtraNumCol1
                from TestCLOBs
                order by IntCol""")
            self.assertEqual(self.cursor.fetchall(), rows)

    def test_4370_rebuild_table_with_lob_in_cached_query(self):
        "4370 - test rebuild of table with LOB in cached query (as string)"
        table_name = "test_4370"
        drop_sql = f"drop table {table_name} purge"
        create_sql = f"""
            create table {table_name} (
                Col1 number(9) not null,
                Col2 clob not null
            )"""
        insert_sql = f"insert into {table_name} values (:1, :2)"
        query_sql = f"select * from {table_name} order by Col1"
        data = [(1, "CLOB value 1"), (2, "CLOB value 2")]
        try:
            self.cursor.execute(drop_sql)
        except:
            pass
        with test_env.FetchLobsContextManager(False):
            self.cursor.execute(create_sql)
            self.cursor.executemany(insert_sql, data)
            self.cursor.execute(query_sql)
            self.assertEqual(self.cursor.fetchall(), data)
            self.cursor.execute(query_sql)
            self.assertEqual(self.cursor.fetchall(), data)
            self.cursor.execute(drop_sql)
            self.cursor.execute(create_sql)
            self.cursor.executemany(insert_sql, data)
            self.cursor.execute(query_sql)
            self.assertEqual(self.cursor.fetchall(), data)

    def test_4371_rebuild_table_with_lob_in_cached_query(self):
        "4371 - test rebuild of table with LOB in cached query (as LOB)"
        table_name = "test_4371"
        drop_sql = f"drop table {table_name} purge"
        create_sql = f"""
            create table {table_name} (
                Col1 number(9) not null,
                Col2 clob not null)"""
        insert_sql = f"insert into {table_name} values (:1, :2)"
        query_sql = f"select * from {table_name} order by Col1"
        data = [(1, "CLOB value 1"), (2, "CLOB value 2")]
        try:
            self.cursor.execute(drop_sql)
        except:
            pass
        self.cursor.execute(create_sql)
        self.cursor.executemany(insert_sql, data)
        self.cursor.execute(query_sql)
        fetched_data = [(n, c.read()) for n, c in self.cursor]
        self.assertEqual(fetched_data, data)
        self.cursor.execute(query_sql)
        fetched_data = [(n, c.read()) for n, c in self.cursor]
        self.assertEqual(fetched_data, data)
        self.cursor.execute(drop_sql)
        self.cursor.execute(create_sql)
        self.cursor.executemany(insert_sql, data)
        self.cursor.execute(query_sql)
        fetched_data = [(n, c.read()) for n, c in self.cursor]
        self.assertEqual(fetched_data, data)

    def test_4372_fetch_json_columns(self):
        "4372 - fetch JSON columns as Python objects"
        oracledb.__future__.old_json_col_as_obj = True
        expected_data = (1, [1, 2, 3], [4, 5, 6], [7, 8, 9])
        self.cursor.execute("select * from TestJsonCols")
        self.assertEqual(self.cursor.fetchone(), expected_data)

    @unittest.skipIf(test_env.get_server_version() < (23, 1),
                     "unsupported database")
    @unittest.skipIf(test_env.get_client_version() < (23, 1),
                     "unsupported client")
    def test_4373_fetch_domain_and_annotations(self):
        "4373 - fetch table with domain and annotations"
        self.cursor.execute("select * from TableWithDomainAndAnnotations")
        self.assertEqual(self.cursor.fetchall(), [(1, 25)])
        column_1 = self.cursor.description[0]
        self.assertIsNone(column_1.domain_schema)
        self.assertIsNone(column_1.domain_name)
        self.assertIsNone(column_1.annotations)
        column_2 = self.cursor.description[1]
        self.assertEqual(column_2.domain_schema,
                         test_env.get_main_user().upper())
        self.assertEqual(column_2.domain_name, "SIMPLEDOMAIN")
        expected_annotations = {
            "ANNO_1": "first annotation",
            "ANNO_2": "second annotation",
            "ANNO_3": ""
        }
        self.assertEqual(column_2.annotations, expected_annotations)

if __name__ == "__main__":
    test_env.run_test_cases()
