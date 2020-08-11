from typing import TYPE_CHECKING, List, Dict, Any
from atomicwrites import atomic_write

import json
import glob
import os
if TYPE_CHECKING:
    from Nodes.NodeEngine import NodeEngine


class NodeStorage:
    def __init__(self, engine: "NodeEngine") -> None:
        self._engine = engine
        self._engine.postUpdateCalled.connect(self.storeNodeState)
        self._base_storage_path = "node_state.json"
        self._num_versions_to_save = 3

    def _getCurrentRevision(self) -> int:
        """
        :return: The revision number of self's largest existing backup
        """
        revisions = [0] + self._getAllRevisions()
        return max(revisions)

    def _getAllRevisions(self) -> List[int]:
        """
        :return: Get the revision numbers of all of backups.
        """
        revisions = []
        backup_names = glob.glob("%s.~[0-9]*~" % (self._base_storage_path))
        for name in backup_names:
            try:
                revision = int(name.split("~")[-2])
                revisions.append(revision)
            except ValueError:
                # Some ~[0-9]*~ extensions may not be wholly numeric
                pass
        revisions.sort()
        return revisions

    def serializeAllNodes(self) -> List[Dict[str, Any]]:
        data = []
        for node in self._engine.getAllNodes().values():
            data.append(node.serialize())
        return data

    def _getVersionedName(self, revision: int) -> str:
        """
        Create a versioned path name based on the provided revision
        :param revision:
        :return: New path with a versioned name
        """
        return "%s.~%s~" % (self._base_storage_path, revision)

    def storeNodeState(self) -> None:
        node_data = self.serializeAllNodes()

        name = self._getVersionedName(self._getCurrentRevision() + 1)

        data_to_write = {"nodes": node_data}

        data_to_store = json.dumps(data_to_write, separators=(", ", ": "), indent=4)
        with atomic_write(name) as file:
            file.write(data_to_store)

        with atomic_write(self._base_storage_path, overwrite = True) as file:
            file.write(data_to_store)

        self._deleteOldRevisions()

    def _deleteOldRevisions(self) -> None:
        """
        Delete old versions of self's file, so that at most num_saved_versions (as set by constructor) versions are
        retained.
        :return:
        """
        revisions = self._getAllRevisions()
        revisions_to_delete = revisions[:-self._num_versions_to_save]
        for revision in revisions_to_delete:
            pathname = self._getVersionedName(revision)
            if os.path.isfile(pathname):
                os.remove(pathname)

    def restoreNodeState(self) -> None:
        with open("node_state.json") as file:
            data = file.read()

        parsed_json = json.loads(data)
        for entry in parsed_json["nodes"]:
            # TODO: This has no fault handling what so ever, which should be added at some point.
            node = self._engine.getNodeById(entry["node_id"])
            if node is not None:
                node.deserialize(entry)
