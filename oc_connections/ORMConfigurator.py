from sys import version_info;

if version_info.major == 2:
    import tzlocal


    def configure_django_orm(conn_mgr, **additional_settings):
        """ Initializes django database connection which allows to use models after that.
        
        :param conn_mgr: ConnectionManager instance which is used to retrieve credentials
        :param additional_settings: dict with additional Django settings
        """
        from django.conf import settings
        settings.configure(
            DATABASES=conn_mgr.get_psql_django_configuration("PSQL"),
            USE_TZ=True,
            TIME_ZONE=tzlocal.get_localzone().zone,
            **additional_settings
        )
        import django
        django.setup()

if version_info.major == 3:
    raise ImportError( "ORMConfigurator module is not yet ported to python 3. Please use python 2.7." );
