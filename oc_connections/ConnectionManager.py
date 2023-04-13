import os
import re
from sys import version_info

if version_info.major == 2:
    import urlparse

if version_info.major == 3:
    import urllib.parse as urlparse

import warnings
from ftplib import FTP
from smtplib import SMTP
import psycopg2
import pysvn
from functools import wraps

if version_info.major == 2:
    from .ExtendedSMBClient import ExtendedSMBClient

from oc_cdtapi.NexusAPI import NexusAPI
from oc_cdtapi.JenkinsAPI import Jenkins
from oc_pyfs.NexusFS import NexusFS
from oc_pyfs.SvnFS import SvnFS
from fs.ftpfs import FTPFS
from smb.SMBConnection import SMBConnection

from .CredentialManager import CredentialManager


def _deprecated(replacement):
    def decorator(func):
        message="Deprecated method '%s' is used. Use '%s' instead" % (func.__name__, replacement)
        @wraps(func)
        def wrapped(*args, **kwargs):
            warnings.warn(message, DeprecationWarning, 2)
            if os.getenv("CONNECTION_MANAGER_DISABLE_DEPRECATED") == "TRUE":
                raise ConnectionManagerError(message)
            else:
                return func(*args, **kwargs)
        wrapped.__doc__="DEPRECATED: use '%s' instead" % replacement
        return wrapped
    return decorator


class ConnectionManager(object):
    """
    Factory which generates clients to external systems (Nexus, SVN and e.c.)
    """

    if version_info.major == 2:
        @staticmethod
        def parse_smb_user(user):
            """
            Parses Samba user string.

            :param user: user string, which must determine domain and user name
            :returns: domain, user name
            """
            parts = user.split( '/', 1)
            if len(parts) < 2:
                raise ConnectionManagerError("Invalid smb user given: domain and user name are required")
            return parts[0], parts[1]

        @staticmethod
        def parse_smb_url(url):
            """
            Parses Samba connection string.
            
            :param url: connection string, which must determine host, share and may determine path
            :returns: host, share, path
            """
            parts = url.split("//", 1)[1].split('/', 2)
            parts_number = len(parts)
            if parts_number < 2:
                raise ConnectionManagerError("Invalid smb url given: host and share are required")
            elif parts_number == 2:
                parts.append('')
            return parts[0], parts[1], parts[2]

    @staticmethod
    def parse_psql_url(url):
        """
        Parses PostgreSQL connection string.
        
        :param url: connection string, which must determine host, port, database name and may determine options
        :returns: hosts, port, database name, options
        """
        if not re.match("(.*?:)?//", url):
            url = "//" + url
        parse_result = urlparse.urlparse(url)
        host = parse_result.hostname
        port = parse_result.port
        dbname = parse_result.path.strip('/')
        options = parse_result.query
        if not all([host, port, dbname]):
            raise ConnectionManagerError("Invalid psql url given: host, port and dbname are required")
        return host, port, dbname, options

    def __init__(self, credential_manager=None):
        """
        Initialize.
        
        :param credential_manager: credential manager
        """
        if credential_manager:
            self.__credential_manager = credential_manager
        else:
            self.__credential_manager = CredentialManager()

    def __get_connection_credentials(self, resource, required=True):
        """
        Get resource connection credentials.
        
        :param resource: resource name
        :param required: defines credentials necessity
        :returns: values of URL, USER, PASSWORD credentials for resource
        """
        url, user, password = self.__credential_manager.get_credentials(resource, ["URL", "USER", "PASSWORD"])
        def assert_credential_given(name, value):
            if not value:
                raise ConnectionManagerError("%s credential is not set for '%s' resource" %
                                             (name, resource))
        if required:
            assert_credential_given("URL", url)
            assert_credential_given("USER", user)
            assert_credential_given("PASSWORD", password)
        return url, user, password

    def get_url(self, resource, required=True):
        """
        Get URL of resource.

        :param resource: resource name
        :param required: defines URL credential necessity
        :returns: URL credential value
        """
        url = self.__credential_manager.get_credential(resource, "URL")
        if not url and required:
            raise ConnectionManagerError("URL credential is not set for '%s' resource" % resource)
        return url

    def get_psql_django_configuration(self, resource):
        """
        Returns PostgreSQL-specific django database connection parameters.

        :param resource: resource name
        :returns: DATABASES config dictionary for Django settings.
        """
        url, user, password = self.__get_connection_credentials(resource)
        host, port, dbname, options = ConnectionManager.parse_psql_url(url)
        if not options:
            raise ConnectionManagerError("Options are required for django configuration")
        return {
            "default": {
                "ENGINE": "django.db.backends.postgresql_psycopg2",
                "NAME": dbname,
                "USER": user,
                "PASSWORD": password,
                "HOST": host,
                "PORT": port,
                "OPTIONS": {"options": "-c " + options},
            }}

    def get_psql_client(self, resource, **kwargs):
        """
        Get PostgreSQL connection.

        :param resource: resource name
        :param kwargs: additional parameters
        :returns: psycopg2 connection
        """
        url, user, password = self.__get_connection_credentials(resource)
        host, port, dbname, options = ConnectionManager.parse_psql_url(url)
        return psycopg2.connect(user=user, password=password, host=host, port=port, dbname=dbname,
                                options="-c " + options if options else "", **kwargs)

    def get_mvn_client(self, resource, **kwargs):
        """
        Get Nexus client.

        :param resource: resource name
        :param kwargs: additional parameters
        :returns: cdt.NexusAPI.NexusAPI
        """
        url, user, password = self.__get_connection_credentials(resource, False)
        if not url:
            raise ConnectionManagerError("URL credential is not set for '%s' resource" % resource)
        if user:
            if not password:
                raise ConnectionManagerError("PASSWORD credential is not set for '%s' resource" % resource)
            client = NexusAPI(root=url, user=user, auth=password, **kwargs)
        else:
            client = NexusAPI(root=url, anonymous=True, **kwargs)
        return client

    def get_mvn_fs_client(self, resource, **kwargs):
        """
        Get Nexus FS client.

        :param resource: resource name
        :param kwargs: additional parameters
        :returns: cdt.pyfs.NexusFS.NexusFS
        """
        work_fs=kwargs.pop("work_fs", None) # this is a parameter to NexusFS, not NexusAPI
        return NexusFS(self.get_mvn_client(resource, **kwargs), work_fs=work_fs)

    def get_svn_client(self, resource):
        """
        Get SVN client.
        
        :param resource: resource name
        :returns: pysvn client 
        """
        user, password = self.__credential_manager.get_credentials(resource, ["USER", "PASSWORD"])
        if not user:
            raise ConnectionManagerError("USER credential is not set for '%s' resource" % resource)
        if not password:
            raise ConnectionManagerError("PASSWORD credential is not set for '%s' resource" % resource)

        class OneAttemptLogin:
            """
            pysvn goes into infinite loop on login failure. This class allows only one login attempt.
            """

            def __init__(self):
                self.__attempt_tried = False

            def __call__(self, x, y, z):
                # return value: retcode, username, password, credentials caching
                if not self.__attempt_tried:
                    self.__attempt_tried = True
                    return True, user, password, False
                else:
                    return False, "xx", "xx", False

        client = pysvn.Client()
        client.callback_get_login = OneAttemptLogin()
        # return values: trust, accept occured failures, save certificate
        # based on example by pysvn author: https://stackoverflow.com/questions/4893218/pysvn-client-callback-ssl-server-trust-prompt-error
        client.callback_ssl_server_trust_prompt=lambda trust_dict: (True, trust_dict["failures"], True)
        client.set_auth_cache(False)
        client.set_store_passwords(False)
        client.set_default_username("")
        client.set_default_password("")
        client.set_interactive(False)
        return client

    def get_svn_fs_client(self, resource, *args, **kwargs):
        """
        Get SVN FS client.

        :param resource: resource name
        :param args: additional parameters
        :param kwargs: additional parameters
        :returns: cdt.pyfs.SvnFS.SvnFS
        """
        return SvnFS(self.get_url(resource), self.get_svn_client(resource), *args, **kwargs)

    if version_info.major == 2:
        def get_smb_client(self, resource):
            """
            Get Samba client.
    
            :param resource: resource name
            :returns: SMBConnection
            """
            url, user, password = self.__get_connection_credentials(resource)
            host, share, path = ConnectionManager.parse_smb_url(url)
            domain, user = ConnectionManager.parse_smb_user(user)
            client = SMBConnection(user, password, 'cln', host, domain, use_ntlm_v2=True, is_direct_tcp=True)
            if not client.connect(host, port=445):
                raise ConnectionManagerError('Connection to Samba server failed')
            return client
    
        # TODO: create get_smb_fs_client when oc_pyfs.SmbFS will be ready to use

    def get_ftp_client(self, resource, **kwargs):
        """
        Get FTP client.

        :param resource: resource name
        :param kwargs: additional parameters
        :returns: FTP client
        """
        url, user, password = self.__get_connection_credentials(resource)
        host, port = _extract_host_port(url)
        client = FTP()
        client.connect(host, port, **kwargs)
        client.login(user, password)
        return client

    def get_ftp_fs_client(self, resource, **kwargs):
        """
        Get FTP FS client.

        :param resource: resource name
        :param kwargs: additional parameters
        :returns: FTPFS client
        """
        url, user, password = self.__get_connection_credentials(resource)
        host, port = _extract_host_port(url)
        return FTPFS(user=user, passwd=password, host=host, port=port, **kwargs)

    def get_smtp_client(self, resource, **kwargs):
        """
        Get SMTP client. Note: Authorization is performed only if USER credential is set.

        :param resource: resource name
        :param kwargs: additional parameters
        :returns: SMTP client
        """
        url, user, password = self.__get_connection_credentials(resource, False)
        if not url:
            raise ConnectionManagerError("URL credential is not set for '%s' resource" % resource)
        host, port = _extract_host_port(url)
        client = SMTP(host=host, port=port, **kwargs)
        if user:
            if not password:
                raise ConnectionManagerError("PASSWORD credential is not set for '%s' resource" % resource)
            client.login(user, password)
        return client

    def get_jenkins_client(self, resource, **kwargs):
        """
        Get Jenkins client. Note: PASSWORD credential is used as auth token.

        :param resource: resource name
        :param kwargs: additional parameters
        :returns: cdt.jenkins.Jenkins
        """
        url, user, password = self.__get_connection_credentials(resource)
        return Jenkins(url, user, password, **kwargs)

    ########################
    # DEPRECATED FUNCTIONS #
    ########################
    # TODO: REMOVE

    @staticmethod
    def parse_conn_url(url):
        return ConnectionManager.parse_psql_url(url)

    @_deprecated(replacement="get_psql_client")
    def get_psql_connection(self, **kwargs):
        return self.get_psql_client("PSQL", **kwargs)
        
    @_deprecated(replacement="get_mvn_client")
    def get_mvn_connection(self, anonymous=False, **kwargs):
        if anonymous:
            url = self.get_url("MVN")
            client = NexusAPI(root=url, anonymous=True, **kwargs)
        else:
            url, username, password = self.__get_connection_credentials("MVN")
            client = NexusAPI(root=url, user=username, auth=password, **kwargs)
        return client

    @_deprecated(replacement="get_svn_client")
    def get_svn_connection(self):
        return self.get_svn_client("SVN")

    if version_info.major == 2:
        @_deprecated(replacement="get_smb_client")
        def get_smb_connection(self, path=""):
            url, user, password = self.__get_connection_credentials("SMB")
            domain = "spb"
            if re.search(r"/", user):
                domain, user = user.split('/')
            # path: O, P, etc. - suffix from "source = %SMB_URL%/..." in mirror.ini
            if path:
                url = urlparse.urljoin(url, path)
            return ExtendedSMBClient(url, user, password, domain)

    @_deprecated(replacement="get_ftp_client")
    def get_ftp_connection(self, **kwargs):
        return self.get_ftp_client("FTP", **kwargs)

    @_deprecated(replacement="get_smtp_client")
    def get_smtp_connection(self, **kwargs):
        return self.get_smtp_client("SMTP", **kwargs)

    @_deprecated(replacement="get_jenkins_client")
    def get_jenkins_connection(self, **kwargs):
        return self.get_jenkins_client("JENKINS", **kwargs)

    @_deprecated(replacement="get_url")
    def get_credential(self, full_name, required=True):
        # noinspection PyProtectedMember
        value = self.__credential_manager._get_credential_value(full_name)
        if not value and required:
            raise CredentialsError("'%s' was not set" % full_name)
        return value

    @_deprecated(replacement="get_url")
    def get_credentials_group(self, prefix, names, required=True):
        if not isinstance(names, list):
            raise CredentialsError("names must be instance of list")
        return [self.get_credential(prefix + '_' + name, required) for name in names]


def _extract_host_port(url):
    """
    Extracts host and port from (maybe) incomplete URL

    :param url: URL string
    :returns: host, port
    """
    if not re.match("(.*?:)?//", url):
        url = "//" + url
    parse_result = urlparse.urlparse(url)
    host = parse_result.hostname
    port = parse_result.port
    if not all([host, port]):
        raise ConnectionManagerError("Invalid url given: host and port are required")
    return host, port


class ConnectionManagerError(Exception):
    """
    ConnectionManager exception
    """
    pass


class CredentialsError(Exception):
    """
    DEPRECATED: Do not use it. Only 'CredentialManager.CredentialManagerError' may be used
    """    
    pass


