from typing import cast

from Nodes.ResourceStorage import ResourceStorage


class Valve(ResourceStorage):
    def __init__(self, node_id: str, resource_type: str, fluid_per_tick: float, **kwargs) -> None:
        super().__init__(node_id, resource_type, 0, 2 * fluid_per_tick, **kwargs)
        self._fluid_per_tick = fluid_per_tick
        self._max_resources_requestables_per_tick = fluid_per_tick

        # A valve cooler pretends to be a resource storage, but it shouldn't display this.
        self.additional_properties.remove("amount_stored")

        # Also try to pump up resources!
        self._optional_resources_required_per_tick[self._resource_type] = fluid_per_tick
        self._min_performance = 0
        self._description = "This device pumps {resource_type} from all incomming connections and provides them to" \
                            " all of it's outgoing connections."
        self._description = self._description.format(resource_type = resource_type)
        self._performance_change_factor = 1
        self._heat_convection_coefficient = 0.2  # type: float

        self._updateResourceRequiredPerTick()
        self._has_settable_performance = True

    def _updateResourceRequiredPerTick(self) -> None:
        new_amount_required = self._fluid_per_tick * self._performance
        storage_room_left = cast(float, self._max_storage) - self._amount
        if storage_room_left < new_amount_required:
            new_amount_required = storage_room_left
        self._optional_resources_required_per_tick[self._resource_type] = max(0., new_amount_required)

    def _setPerformance(self, new_performance) -> None:
        self._updateResourceRequiredPerTick()
        super()._setPerformance(new_performance)

        self._max_storage = 2 * self._performance * self._fluid_per_tick

    def update(self) -> None:
        # First, we store the resources other nodes *gave* us (these are already added!)
        resource_already_added = self._resources_received_this_tick.get(self._resource_type, 0)

        # Then we check how much resources in total we got this turn (aka; how much after we also requested resources)
        super().update()
        resource_available = self.getResourceAvailableThisTick(self._resource_type)

        # Now we can figure out how much we really have right now.
        self._amount = self._amount - resource_already_added + resource_available

        resources_to_distribute = min(self._fluid_per_tick * self.performance, self._amount)
        resources_left = self._amount - resources_to_distribute

        # Then we try to give as much away as possible.
        self._amount = self._provideResourceToOutgoingConnections(self._resource_type, resources_to_distribute) + resources_left

    def postUpdate(self) -> None:
        super().postUpdate()
        # This is done in the post update to ensure that it also takes resouces taken by other nodes into account.
        # We can't do this in the update, because other nodes might be updated later.
        self._updateResourceRequiredPerTick()