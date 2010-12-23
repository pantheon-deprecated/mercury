from twisted.web.server import Site
from twisted.web.resource import Resource

class Entity(Resource):
    isLeaf = True

    def __init__(self, entity_type, entity_id):
        Resource.__init__(self)
        self.entityType = entity_type
        self.entityId = entity_id

    def render_GET(self, request):
        # Cpde here to handle GET
        return 'GET'

    def render_PUT(self, request):
        bson = request.content.getvalue()

        # Code here to handle PUT
        return 'PUT: %s %s' % (self.entityType, self.entityId)

class EntityType(Resource):
    def __init__(self, entity_type):
        Resource.__init__(self)
        self.entityType = entity_type

    def getChild(self, name, request):
        return Entity(self.entityType, name)

class ReplicationBridge(Resource):
    def getChild(self, name, request):
        return EntityType(name)

root = ReplicationBridge()
factory = Site(root)
