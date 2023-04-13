import os


class CredentialManager(object):
    """
    Class for managing credentials.
    
    All credentials are stored as environment variables and may be overridden at instance level.
    Full credential name consists of resource name and credential name separated by underscore. For example: SVN_CLIENTS_URL - where SVN_CLIENTS is a resource name and URL is a credential name
    """

    @staticmethod
    def __get_full_name(resource, name):
        """
        Private method for full credential name assembling.
        
        :param resource: resource name
        :param name: credential name
        :returns: full credential name
        """
        return resource + "_" + name

    def __init__(self):
        self.__forced_credentials = {}

    def _get_credential_value(self, full_name):
        """
        Protected method for credential value retrieval. Note: Subclasses may override it for reading from other sources (for example, config file).

        :param full_name: credential full name
        :returns: credential value
        """
        return self.__forced_credentials.get(full_name, os.getenv(full_name))

    def get_credential(self, resource, name):
        """
        Get value of a credential.

        :param resource: resource name
        :param name: credential name
        :returns: credential value
        """
        full_name = CredentialManager.__get_full_name(resource, name)
        return self._get_credential_value(full_name)

    def get_credentials(self, resource, names):
        """
        Get values of credentials.

        :param resource: resource name
        :param names: list of credential names
        :returns: list of credential values
        """
        if not isinstance(names, list):
            raise CredentialManagerError("names parameter must be instance of list")
        return [self.get_credential(resource, name) for name in names]

    def override_credential(self, resource, name, value):
        """
        Override value of credential.

        :param resource: resource name
        :param name: credential name
        :param value: overriding value
        """
        full_name = CredentialManager.__get_full_name(resource, name)
        self.__forced_credentials[full_name] = value

    def reset_credential(self, resource, name):
        """
        Clear overriding value of credential.

        :param resource: resource name
        :param name: credential name
        """
        full_name = CredentialManager.__get_full_name(resource, name)
        self.__forced_credentials.pop(full_name, None)

    def reset_credentials(self, resource, names):
        """
        Clear overriding values of credentials.

        :param resource: resource name
        :param names: list of credential names
        """
        if not isinstance(names, list):
            raise CredentialManagerError("names parameter must be instance of list")
        for name in names:
            self.reset_credential(resource, name)


class CredentialManagerError(Exception):
    """
    CredentialManager exception
    """
    pass
