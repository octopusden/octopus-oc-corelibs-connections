from smtplib import SMTPException
from unittest import TestCase
from psycopg2 import OperationalError
from oc_connections.CredentialManager import CredentialManager
from oc_connections.ConnectionManager import ConnectionManagerError
import oc_connections.ConnectionManager

from sys import version_info

if version_info.major == 3:
    from unittest.mock import patch;
    from smtplib import SMTPException;

    class MockSMTP( object ):
        host = None;
        port = None;
        user = None;
        password = None;

        def __init__( self, host, port, **kwargs ):
            self.host = host;
            self.port = port;

        def login( self, user, password ):
            if user != "test_smtp_user" and password != "test_smtp_password":
                raise SMTPException( "Login error. Invalid user" );

            self.user = user
            self.password = password;

    class MockSvnFs( object ):
        def __init__( self, url, client, *args, **kwargs ):
            self.url = url;

        def listdir( self, url ):
            return ['apps', 'module1', 'doc', 'module2', 'src'];

    class MockPgClient( object ):
        dict_parms = dict();

        @classmethod
        def connect( self, user, password, host, port, dbname, options, **kwargs ):
            no = self();
            no.dict_parms[ 'user' ] = user;
            no.dict_parms[ 'password' ] = password;
            no.dict_parms[ 'host' ] = host;
            no.dict_parms[ 'port' ] = port;
            no.dict_parms[ 'dbname' ] = dbname;
            no.dict_parms[ 'options' ] = options;
            return no;

    class MockFTP( object ):
        dict_parms = dict();

        def connect( self, host, port, **kwargs ):
            self.dict_parms[ 'host' ] = host;
            self.dict_parms[ 'port' ] = port;

        def login( self, user, password ):
            self.dict_parms[ 'user' ] = user;
            self.dict_parms[ 'password' ] = password

        def nlst( self, path = '/' ):
            return [ "ftp.txt" ];


    class MockNexusFS( object ):
        def __init__( self, api, work_fs, **kwargs ):
            self.api = api;
            self.work_fs = work_fs;

    class MockNexusAPI( object ):
        def __init__( self, **kwargs ):
            self.kwargs = kwargs;

    class MockFTPFS( object ):
        def __init__( self, **kwargs ):
            self.kwargs = kwargs;

class ConnectionManagerTestSuite(TestCase):
    if version_info.major == 3:
        def assertItemsEqual(self, expected_seq, actual_seq, msg=None):
            return self.assertCountEqual( actual_seq, expected_seq, msg=msg );

    def setUp(self):
        self.cred_mgr = CredentialManager()
        self.conn_mgr = oc_connections.ConnectionManager.ConnectionManager(self.cred_mgr)

    # PSQL group
    if version_info.major == 3:
        @patch( 'oc_connections.ConnectionManager.psycopg2', new = MockPgClient )
        def test_psql_connection(self):
            self.cred_mgr.override_credential("TEST_PSQL", "URL", "127.0.0.1:5432/postgres" )
            self.cred_mgr.override_credential("TEST_PSQL", "USER", "test_user")
            self.cred_mgr.override_credential("TEST_PSQL", "PASSWORD", "test_user")
            expected_params = {
                'dbname': 'postgres',
                'user': 'test_user',
                'port': 5432,
                'host': '127.0.0.1',
                'options' : '',
                'password' : "test_user"
            }
            client = self.conn_mgr.get_psql_client("TEST_PSQL");
            self.assertIsInstance( client, MockPgClient );
            self.assertEqual(expected_params, client.dict_parms)

        @patch( 'oc_connections.ConnectionManager.psycopg2', new = MockPgClient )
        def test_psql_connection_url_with_protocol(self):
            self.cred_mgr.override_credential("TEST_PSQL", "URL", "postgresql://127.0.0.1:5432/postgres" )
            self.cred_mgr.override_credential("TEST_PSQL", "USER", "test_user")
            self.cred_mgr.override_credential("TEST_PSQL", "PASSWORD", "test_user")
            expected_params = {
                'dbname': 'postgres',
                'user': 'test_user',
                'port': 5432,
                'host': '127.0.0.1',
                'options' : '',
                'password' : 'test_user'
            }
            client = self.conn_mgr.get_psql_client("TEST_PSQL");
            self.assertIsInstance( client, MockPgClient );
            self.assertEqual(expected_params, client.dict_parms)

        @patch( 'oc_connections.ConnectionManager.psycopg2', new = MockPgClient )
        def test_psql_connection_url_with_options(self):
            self.cred_mgr.override_credential("TEST_PSQL", "URL", "127.0.0.1:5432/postgres?search_path=dl_schema")
            self.cred_mgr.override_credential("TEST_PSQL", "USER", "test_user")
            self.cred_mgr.override_credential("TEST_PSQL", "PASSWORD", "test_user")
            expected_params = {
                'dbname': 'postgres',
                'user': 'test_user',
                'port': 5432,
                'host': '127.0.0.1',
                'options' : '-c search_path=dl_schema',
                'password' : 'test_user'
            }
            client = self.conn_mgr.get_psql_client("TEST_PSQL");
            self.assertIsInstance( client, MockPgClient );
            self.assertEqual(expected_params, client.dict_parms)

    def test_postgres_fail_no_username(self):
        self.cred_mgr.override_credential("TEST_PSQL", "URL", "127.0.0.1:5432/postgres")
        self.cred_mgr.reset_credential("TEST_PSQL", "USER")
        self.cred_mgr.override_credential("TEST_PSQL", "PASSWORD", "test_user")
        with self.assertRaises(ConnectionManagerError):
            self.conn_mgr.get_psql_client("TEST_PSQL")

    def test_postgres_fail_wrong_password(self):
        self.cred_mgr.override_credential("TEST_PSQL", "URL", "127.0.0.1:5432/postgres")
        self.cred_mgr.override_credential("TEST_PSQL", "USER", "test_user")
        self.cred_mgr.override_credential("TEST_PSQL", "PASSWORD", "XXX")
        with self.assertRaises(OperationalError):
            self.conn_mgr.get_psql_client("TEST_PSQL")

    def test_incomplete_conn_url(self):
        self.cred_mgr.override_credential("TEST_PSQL", "URL", "127.0.0.1/postgres")
        self.cred_mgr.override_credential("TEST_PSQL", "USER", "test_user")
        self.cred_mgr.override_credential("TEST_PSQL", "PASSWORD", "test_user")
        with self.assertRaises(ConnectionManagerError):
            self.conn_mgr.get_psql_client("TEST_PSQL")

    # SVN group
    def test_svn_connection(self):
        self.cred_mgr.override_credential("TEST_SVN", "USER", "user")
        self.cred_mgr.override_credential("TEST_SVN", "PASSWORD", "password")
        client = self.conn_mgr.get_svn_client("TEST_SVN")
        actual_login_data = client.callback_get_login(None, None, None)
        expected_login_data = (True, "user", "password", False)
        self.assertEqual(expected_login_data, actual_login_data)
        # check that infinite loop prevented
        relogin_data = client.callback_get_login(None, None, None)
        self.assertFalse(relogin_data[0])

    if version_info.major == 3:
        @patch( 'oc_connections.ConnectionManager.SvnFS', new = MockSvnFs )
        def test_svn_fs_connection(self):
            self.cred_mgr.override_credential(
                "TEST_SVN", "URL", "127.0.0.1")
            self.cred_mgr.override_credential("TEST_SVN", "USER", "guest")
            self.cred_mgr.override_credential("TEST_SVN", "PASSWORD", "guest")
            client = self.conn_mgr.get_svn_fs_client("TEST_SVN");
            self.assertIsInstance( client, MockSvnFs );
            self.assertItemsEqual(["apps", "module1", "doc", "module2", "src"], client.listdir('/'))

    def test_svn_no_user(self):
        self.cred_mgr.reset_credential("TEST_SVN", "USER")
        self.cred_mgr.override_credential("TEST_SVN", "PASSWORD", "guest")
        with self.assertRaises(ConnectionManagerError):
            self.conn_mgr.get_svn_client("TEST_SVN")

    def test_svn_fs_no_url(self):
        self.cred_mgr.reset_credential("TEST_SVN", "URL")
        self.cred_mgr.override_credential("TEST_SVN", "USER", "guest")
        self.cred_mgr.override_credential("TEST_SVN", "PASSWORD", "guest")
        with self.assertRaises(ConnectionManagerError):
            self.conn_mgr.get_svn_fs_client("TEST_SVN")

    # MVN group
    def test_mvn_connection(self):
        self.cred_mgr.override_credential("TEST_MVN", "URL", "http://127.0.0.1:8081/nexus/" )
        self.cred_mgr.override_credential("TEST_MVN", "USER", "test-user")
        self.cred_mgr.override_credential("TEST_MVN", "PASSWORD", "test-user")
        client = self.conn_mgr.get_mvn_client("TEST_MVN")
        self.assertEqual(("test-user", "test-user"), client.web.auth)

    def test_mvn_no_url(self):
        self.cred_mgr.reset_credential("TEST_MVN", "URL")
        self.cred_mgr.override_credential("TEST_MVN", "USER", "test-user")
        self.cred_mgr.override_credential("TEST_MVN", "PASSWORD", "test-user")
        with self.assertRaises(ConnectionManagerError):
            self.conn_mgr.get_mvn_client("TEST_MVN")

    def test_mvn_no_password(self):
        self.cred_mgr.override_credential("TEST_MVN", "URL", "http://127.0.0.1:8081/nexus/" )
        self.cred_mgr.override_credential("TEST_MVN", "USER", "test-user")
        self.cred_mgr.reset_credential("TEST_MVN", "PASSWORD")
        with self.assertRaises(ConnectionManagerError):
            self.conn_mgr.get_mvn_client("TEST_MVN")

    def test_mvn_anonymous(self):
        self.cred_mgr.override_credential("TEST_MVN", "URL", "http://127.0.0.1:8081/nexus/" )
        self.cred_mgr.reset_credential("TEST_MVN", "USER")
        self.cred_mgr.reset_credential("TEST_MVN", "PASSWORD")
        client = self.conn_mgr.get_mvn_client("TEST_MVN")
        self.assertIsNone(client.web.auth);


    #FTP group
    if version_info.major == 3:
        @patch( 'oc_connections.ConnectionManager.FTP', new = MockFTP )
        def test_ftp_connection(self):
            self.cred_mgr.override_credential("TEST_FTP", "URL", "127.0.0.1:21")
            self.cred_mgr.override_credential("TEST_FTP", "USER", "test_ftp")
            self.cred_mgr.override_credential("TEST_FTP", "PASSWORD", "test_ftp")
            expected_parms = { 
                    'host' : '127.0.0.1',
                    'port' : 21,
                    'user' : 'test_ftp',
                    'password' : 'test_ftp'
                }
            client = self.conn_mgr.get_ftp_client("TEST_FTP")
            self.assertIsInstance( client, MockFTP );
            self.assertEqual( client.dict_parms, expected_parms );
            self.assertIn( "ftp.txt", client.nlst() )

    def test_ftp_no_url(self):
        self.cred_mgr.reset_credential("TEST_FTP", "URL")
        self.cred_mgr.override_credential("TEST_FTP", "USER", "test_ftp")
        self.cred_mgr.override_credential("TEST_FTP", "PASSWORD", "test_ftp")
        with self.assertRaises(ConnectionManagerError):
            self.conn_mgr.get_ftp_client("TEST_FTP")

    def test_ftp_no_user(self):
        self.cred_mgr.override_credential("TEST_FTP", "URL", "127.0.0.1:21")
        self.cred_mgr.reset_credential("TEST_FTP", "USER")
        self.cred_mgr.override_credential("TEST_FTP", "PASSWORD", "test_ftp")
        with self.assertRaises(ConnectionManagerError):
            self.conn_mgr.get_ftp_client("TEST_FTP")

    if version_info.major == 3:
        @patch( 'oc_connections.ConnectionManager.FTP', new = MockFTP )
        def test_ftp_url_with_protocol(self):
            self.cred_mgr.override_credential("TEST_FTP", "URL", "ftp://127.0.0.1:21")
            self.cred_mgr.override_credential("TEST_FTP", "USER", "test_ftp")
            self.cred_mgr.override_credential("TEST_FTP", "PASSWORD", "test_ftp")
            client = self.conn_mgr.get_ftp_client("TEST_FTP")
            expected_parms = { 
                    'host' : '127.0.0.1',
                    'port' : 21,
                    'user' : 'test_ftp',
                    'password' : 'test_ftp'
                }
            client = self.conn_mgr.get_ftp_client("TEST_FTP")
            self.assertIsInstance( client, MockFTP );
            self.assertEqual( client.dict_parms, expected_parms );
            self.assertIn( "ftp.txt", client.nlst() )

    #SMTP group
    if version_info.major == 3:
        @patch( 'oc_connections.ConnectionManager.SMTP', new = MockSMTP )
        def test_smtp_correct_user(self):
            self.cred_mgr.override_credential("TEST_SMTP", "URL", "127.0.0.1:25")
            self.cred_mgr.override_credential("TEST_SMTP", "USER", "test_smtp_user")
            self.cred_mgr.override_credential("TEST_SMTP", "PASSWORD", "test_smtp_password")
            client = self.conn_mgr.get_smtp_client("TEST_SMTP")

            self.assertIsInstance( client, MockSMTP );
            self.assertEqual( client.user, "test_smtp_user" );
            self.assertEqual( client.password, "test_smtp_password" );
            self.assertEqual( client.host, "127.0.0.1" );
            self.assertEqual( client.port, 25 );

        @patch( 'oc_connections.ConnectionManager.SMTP', new = MockSMTP )
        def test_smtp_fail_user(self):
            self.cred_mgr.override_credential("TEST_SMTP", "URL", "127.0.0.1:25")
            self.cred_mgr.override_credential("TEST_SMTP", "USER", "XXX")
            self.cred_mgr.override_credential("TEST_SMTP", "PASSWORD", "XXX")
            with self.assertRaises(SMTPException):
                self.conn_mgr.get_smtp_client("TEST_SMTP")

        @patch( 'oc_connections.ConnectionManager.SMTP', new = MockSMTP )
        def test_smtp_no_user(self):
            self.cred_mgr.override_credential("TEST_SMTP", "URL", "127.0.0.1:25")
            self.cred_mgr.reset_credential("TEST_SMTP", "USER")
            self.cred_mgr.override_credential("TEST_SMTP", "PASSWORD", "XXX")
            client = self.conn_mgr.get_smtp_client("TEST_SMTP")

            self.assertIsInstance( client, MockSMTP );
            self.assertIsNone( client.user );
            self.assertIsNone( client.password );
            self.assertEqual( client.host, "127.0.0.1" );
            self.assertEqual( client.port, 25 );

    #JENKINS group
    def test_jenkins_connection(self):
        self.cred_mgr.override_credential("TEST_JENKINS", "URL", "http://127.0.0.1:8080/" )
        self.cred_mgr.override_credential("TEST_JENKINS", "USER", "user")
        self.cred_mgr.override_credential("TEST_JENKINS", "PASSWORD", "password")
        client = self.conn_mgr.get_jenkins_client("TEST_JENKINS")
        self.assertEqual("http://127.0.0.1:8080/", client.root)
        self.assertEqual(("user", "password"), client.web.auth)

    def test_jenkins_no_url(self):
        self.cred_mgr.reset_credential("TEST_JENKINS", "URL")
        self.cred_mgr.override_credential("TEST_JENKINS", "USER", "user")
        self.cred_mgr.override_credential("TEST_JENKINS", "PASSWORD", "password")
        with self.assertRaises(ConnectionManagerError):
            self.conn_mgr.get_jenkins_client("TEST_JENKINS")

    if version_info.major == 2:
        def test_parse_smb_url( self ):
            self.assertEqual( self.conn_mgr.parse_smb_url( "smb://localhost/labuda/K/Ret/In"), ( "localhost", "labuda", "K/Ret/In" ) );

            #invalid URL
            with self.assertRaises( IndexError ):
                self.conn_mgr.parse_smb_url( "localhost/labuda/bab" );

            with self.assertRaises( ConnectionManagerError ):
                self.conn_mgr.parse_smb_url( "smb://localhost" );


        def test_parse_smb_user( self ):
            self.assertEqual( self.conn_mgr.parse_smb_user( "T/K" ), ( "T", "K" ) );

            # no domain given
            with self.assertRaises( ConnectionManagerError ):
                self.conn_mgr.parse_smb_user( "thebug" );

            # explicit domain
            self.assertEqual( self.conn_mgr.parse_smb_user( "T/K/P" ), ( "T", "K/P" ) );

    def test_parse_psql_url( self ):
        self.assertEqual( self.conn_mgr.parse_psql_url( "localhost:5432/postgres?search_path=dl_schema" ), ('localhost', 5432, 'postgres', 'search_path=dl_schema') );
        self.assertEqual( self.conn_mgr.parse_psql_url( "localhost:5432/postgres" ), ('localhost', 5432, 'postgres', '') );
        with self.assertRaises( ConnectionManagerError ):
            self.conn_mgr.parse_psql_url( "localhost/postgres" );


    def test_get_url( self ):
        new_url = "fff://Create/In";
        self.cred_mgr.override_credential( "TEST","URL", new_url );
        self.assertEqual( self.conn_mgr.get_url( "TEST", required = True ), new_url );
        #non-existant url
        self.cred_mgr.reset_credential( "TEST","URL" );
        with self.assertRaises( ConnectionManagerError ):
            self.conn_mgr.get_url( "TEST" );


    def test_get_psql_django_config( self ):
        # no URL
        self.cred_mgr.reset_credential( "TEST", "URL" );
        self.cred_mgr.reset_credential( "TEST", "USER" );
        self.cred_mgr.reset_credential( "TEST", "PASSWORD" );

        with self.assertRaises( ConnectionManagerError ):
            self.conn_mgr.get_psql_django_configuration( "TEST" );

        # no user
        test_url = "localhost:777/postgears?search_path=fake_off_schema"
        self.cred_mgr.override_credential( "TEST", "URL", test_url );
        with self.assertRaises( ConnectionManagerError ):
            self.conn_mgr.get_psql_django_configuration( "TEST" );

        test_user = "bugs_off";
        self.cred_mgr.override_credential( "TEST", "USER", test_user );
        with self.assertRaises( ConnectionManagerError ):
            self.conn_mgr.get_psql_django_configuration( "TEST" );

        test_password = "bugs_on";
        self.cred_mgr.reset_credential( "TEST", "USER" );
        self.cred_mgr.override_credential( "TEST", "PASSWORD", test_password );
        with self.assertRaises( ConnectionManagerError ):
            self.conn_mgr.get_psql_django_configuration( "TEST" );

        # all OK
        self.cred_mgr.override_credential( "TEST", "USER", test_user );
        self.assertEqual( self.conn_mgr.get_psql_django_configuration( "TEST" ), {
            "default": {
                "ENGINE": "django.db.backends.postgresql_psycopg2",
                "NAME": "postgears",
                "USER": test_user,
                "PASSWORD": test_password,
                "HOST": "localhost",
                "PORT": 777,
                "OPTIONS": {"options": "-c " + "search_path=fake_off_schema"},
            }} );


        # no options
        test_url = "localhost:777/postgears"
        self.cred_mgr.override_credential( "TEST", "URL", test_url );
        with self.assertRaises( ConnectionManagerError ):
            self.conn_mgr.get_psql_django_configuration( "TEST" );


    if version_info.major == 3:
        @patch( 'oc_connections.ConnectionManager.NexusFS', new = MockNexusFS )
        @patch( 'oc_connections.ConnectionManager.NexusAPI', new = MockNexusAPI )
        def test_get_mvn_fs_client( self ):
            url = "http://localhost:777/nexus";
            user = "buggy_boy";
            password = "buggy_girl";
            self.cred_mgr.override_credential( "TEST", "URL", url );
            self.cred_mgr.override_credential( "TEST", "USER", user );
            self.cred_mgr.override_credential( "TEST", "PASSWORD", password );
            client = self.conn_mgr.get_mvn_fs_client( "TEST" );
            self.assertIsInstance( client, MockNexusFS );
            self.assertIsInstance( client.api, MockNexusAPI );
            self.assertEqual( client.api.kwargs[ 'root' ], url );
            self.assertEqual( client.api.kwargs[ 'user' ], user );
            self.assertEqual( client.api.kwargs[ 'auth' ], password );

            # anonymous
            self.cred_mgr.reset_credential( "TEST", "USER" );
            self.cred_mgr.reset_credential( "TEST", "PASSWORD" );
            client = self.conn_mgr.get_mvn_fs_client( "TEST" );
            self.assertIsInstance( client, MockNexusFS );
            self.assertIsInstance( client.api, MockNexusAPI );
            self.assertEqual( client.api.kwargs[ 'root' ], url );
            self.assertTrue( client.api.kwargs[ 'anonymous' ] );

        @patch( 'oc_connections.ConnectionManager.FTP', new = MockFTP )
        @patch( 'oc_connections.ConnectionManager.FTPFS', new = MockFTPFS )
        def test_get_ftp_fs_client( self ):
            
            url = "ftp://localhost:777";
            user = "fuggy_boy";
            password = "fuggy_girl";
            self.cred_mgr.override_credential( "TEST", "URL", url );
            self.cred_mgr.override_credential( "TEST", "USER", user );
            self.cred_mgr.override_credential( "TEST", "PASSWORD", password );
            client = self.conn_mgr.get_ftp_fs_client( "TEST" );
            self.assertIsInstance( client, MockFTPFS );
            self.assertEqual( 'ftp://%s:%d' % (client.kwargs[ 'host' ], client.kwargs[ 'port' ]), url );
            self.assertEqual( client.kwargs[ 'user' ], user );
            self.assertEqual( client.kwargs[ 'passwd' ], password );

            # anonymous
            self.cred_mgr.reset_credential( "TEST", "USER" );
            self.cred_mgr.reset_credential( "TEST", "PASSWORD" );
            with self.assertRaises( ConnectionManagerError ):
                client = self.conn_mgr.get_ftp_fs_client( "TEST" );
