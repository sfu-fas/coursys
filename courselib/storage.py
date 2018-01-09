import uuid
import os.path
from django.core.files.storage import FileSystemStorage
from django.conf import settings


UploadedFileStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)


def upload_path(*path_components):
    """
    Builds an upload path that will be unique: upload_path(a, b, c, filename) -> a/b/c/uuid1/filename
    """
    filename = path_components[-1]
    path_components = list(path_components[:-1])
    uu = uuid.uuid1(uuid.getnode())
    components = path_components + [str(uu), filename]
    # make sure filenames are entirely ASCII
    components = [c.encode('ascii', 'ignore').decode('ascii') for c in components]
    return os.path.join(*components)
