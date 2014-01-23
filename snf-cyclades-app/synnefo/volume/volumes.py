import logging

from django.db import transaction
from snf_django.lib.api import faults
from synnefo.db.models import Volume
from synnefo.volume import util
from synnefo.logic import server_attachments

log = logging.getLogger(__name__)


@transaction.commit_on_success
def create(user_id, size, server_id, name=None, description=None,
           source_volume_id=None, source_snapshot_id=None,
           source_image_id=None, metadata=None):

    # Currently we cannot create volumes without being attached to a server
    if server_id is None:
        raise faults.BadRequest("Volume must be attached to server")
    server = util.get_server(user_id, server_id, for_update=True,
                             exception=faults.BadRequest)

    # Assert that not more than one source are used
    sources = filter(lambda x: x is not None,
                     [source_volume_id, source_snapshot_id, source_image_id])
    if len(sources) > 1:
        raise faults.BadRequest("Volume can not have more than one source!")

    if source_volume_id is not None:
        source_type = "volume"
        source_uuid = source_volume_id
    elif source_snapshot_id is not None:
        source_type = "snapshot"
        source_uuid = source_snapshot_id
    elif source_image_id is not None:
        source_type = "image"
        source_uuid = source_image_id
    else:
        source_type = source_uuid = None

    volume = _create_volume(server, user_id, size, source_type, source_uuid,
                            name, description, index=None)

    if metadata is not None:
        for meta_key, meta_val in metadata.items():
            volume.metadata.create(key=meta_key, value=meta_val)

    server_attachments.attach_volume(server, volume)

    return volume


def _create_volume(server, user_id, size, source_type, source_uuid,
                   name=None, description=None, index=None,
                   delete_on_termination=True):

    # Only ext_ disk template supports cloning from another source. Otherwise
    # is must be the root volume so that 'snf-image' fill the volume
    disk_template = server.flavor.disk_template
    can_have_source = (index == 0 or disk_template.startswith("ext_"))
    if not can_have_source and source_type != "blank":
        msg = ("Volumes of '%s' disk template cannot have a source" %
               disk_template)
        raise faults.BadRequest(msg)

    # TODO: Check Volume/Snapshot Status
    if source_type == "volume":
        source_volume = util.get_volume(user_id, source_uuid,
                                        for_update=True,
                                        exception=faults.BadRequest)
        if source_volume.status != "IN_USE":
            raise faults.BadRequest("Cannot clone volume while it is in '%s'"
                                    " status" % source_volume.status)
        # If no size is specified, use the size of the volume
        if size is None:
            size = source_volume.size
        elif size < source_volume.size:
            raise faults.BadRequest("Volume size cannot be smaller than the"
                                    " source volume")
        source = Volume.prefix_source(source_uuid, source_type="volume")
        origin = source_volume.backend_volume_uuid
    elif source_type == "snapshot":
        source_snapshot = util.get_snapshot(user_id, source_uuid,
                                            exception=faults.BadRequest)
        source = Volume.prefix_source(source_uuid,
                                      source_type="snapshot")
        if size is None:
            raise faults.BadRequest("Volume size is required")
        elif (size << 30) < int(source_snapshot["size"]):
            raise faults.BadRequest("Volume size '%s' is smaller than"
                                    " snapshot's size '%s'"
                                    % (size << 30, source_snapshot["size"]))
        origin = source_snapshot["checksum"]
    elif source_type == "image":
        source_image = util.get_image(user_id, source_uuid,
                                      exception=faults.BadRequest)
        if size is None:
            raise faults.BadRequest("Volume size is required")
        elif (size << 30) < int(source_image["size"]):
            raise faults.BadRequest("Volume size '%s' is smaller than"
                                    " image's size '%s'"
                                    % (size << 30, source_image["size"]))
        source = Volume.prefix_source(source_uuid, source_type="image")
        origin = source_image["checksum"]
    elif source_type == "blank":
        if size is None:
            raise faults.BadRequest("Volume size is required")
        source = origin = None
    else:
        raise faults.BadRequest("Unknwon source type")

    volume = Volume.objects.create(userid=user_id,
                                   size=size,
                                   name=name,
                                   machine=server,
                                   description=description,
                                   delete_on_termination=delete_on_termination,
                                   source=source,
                                   origin=origin,
                                   #volume_type=volume_type,
                                   status="CREATING")
    return volume


@transaction.commit_on_success
def delete(volume):
    """Delete a Volume"""
    # A volume is deleted by detaching it from the server that is attached.
    # Deleting a detached volume is not implemented.
    if volume.machine_id is not None:
        server_attachments.detach_volume(volume.machine, volume)
        log.info("Detach volume '%s' from server '%s', job: %s",
                 volume.id, volume.machine_id, volume.backendjobid)
    else:
        raise faults.BadRequest("Cannot delete a detached volume")

    return volume


@transaction.commit_on_success
def rename(volume, new_name):
    volume.name = new_name
    volume.save()
    return volume


@transaction.commit_on_success
def update_description(volume, new_description):
    volume.description = new_description
    volume.save()
    return volume
