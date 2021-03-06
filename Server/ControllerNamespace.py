from flask import request
from flask_restx import Resource, fields, Namespace
import json
from Server.Blueprint import api
from Server.ControllerManager import ControllerManager


control_namespace = Namespace("controller", description ="Controllers are the remote devices that provide us with state.")

sensor = api.model("sensor", {
    "name": fields.String,
    "value": fields.Float
})

controller = api.model("controller", {
    "id": fields.String,
    "time_since_last_update": fields.Float,
    "sensors": fields.List(fields.Nested(sensor))
})



def getControllerData(controller_id):
    manager = ControllerManager.getInstance()
    controller = manager.getController(controller_id)
    if not controller:
        return None
    result = {"id": controller_id,
            "time_since_last_update": round(controller.time_since_last_update, 2),
            "sensors": []}

    for key in controller.getAllSensorNames():
        result["sensors"].append({"name": key, "value": controller.getSensorValue(key), "target": manager.getMappedIdFromSensor(controller_id, key)})

    return result

@control_namespace.route("/")
@control_namespace.doc(description ="Get all the known controllers.")
class Controllers(Resource):
    @api.response(200, "Sucess", fields.List(fields.Nested(controller)))
    def get(self):
        result = []
        manager = ControllerManager.getInstance()
        for key in manager.getAllControllerIds():
            controller_data = getControllerData(key)
            if controller_data is not None:
                result.append(controller_data)
        return result


@control_namespace.route("/<string:controller_id>/")
@control_namespace.doc(params={'controller_id': 'Identifier of the controller'})
class Controller(Resource):
    @api.response(200, "success", controller)
    @api.response(404, "Unknown Node")
    def get(self, controller_id):
        manager = ControllerManager.getInstance()
        return getControllerData(controller_id)

    @api.response(200, "success")
    def put(self, controller_id):
        manager = ControllerManager.getInstance()
        manager.updateController(controller_id, json.loads(request.data))
