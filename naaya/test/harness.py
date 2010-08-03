import zope_wrapper

class TestHarness(object):
    def __init__(self, orig_db, db_layer):
        self.orig_db = orig_db
        self.db_layer = db_layer

    wsgi_app = staticmethod(zope_wrapper.wsgi_publish)


def zope_test_harness(orig_conf_path):
    orig_db, db_layer = zope_wrapper.startup(orig_conf_path)
    return TestHarness(orig_db, db_layer)

def test_zope_for_part_name(part_name):
    import sys
    from os import path
    buildout_root = path.dirname(path.dirname(sys.argv[0]))
    orig_conf_path = path.join(buildout_root, 'parts', part_name,
                                 'etc', 'zope.conf')

    tzope = zope_test_harness(orig_conf_path)
    return tzope

def demo_http_server(tzope):
    from contextlib import contextmanager

    def wsgireffix(app):
        from webob.dec import wsgify
        @wsgify
        def wrapper(request):
            response = request.get_response(app)
            del response.headers['Connection']
            return response
        return wrapper

    @contextmanager
    def temp_request(app, user_id):
        from ZPublisher.BaseRequest import BaseRequest
        user = app.acl_users.getUserById('admin')
        app.REQUEST = BaseRequest(AUTHENTICATED_USER=user)
        yield
        del app.REQUEST

    def install_fixtures(db):
        import transaction
        from Products.Naaya.NySite import manage_addNySite

        app = db.open().root()['Application']
        app.acl_users._doAddUser('admin', 'admin', ['Manager'], [])
        with temp_request(app, 'admin'):
            manage_addNySite(app, 'portal')

        transaction.commit()


    install_fixtures(tzope.orig_db)

    from wsgiref.simple_server import make_server
    app = wsgireffix(tzope.wsgi_app)
    httpd = make_server('127.0.0.1', 8080, app)

    while True:
        with tzope.db_layer() as db_layer:
            print "waiting for requests. press ctrl_c to refresh db."
            try:
                httpd.serve_forever()
            except SystemExit:
                return # continue

def demo(part_name):
    tzope = test_zope_for_part_name(part_name)
    demo_http_server(tzope)