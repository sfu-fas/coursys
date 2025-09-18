import datetime
import uuid
import os.path
from django.core.files.storage import FileSystemStorage
from django.conf import settings

# temporary storage for applications such as form wizard, to be periodically cleaned
# organized --> /temp/year/month/filename
TemporaryFileStorage = FileSystemStorage(location=settings.SUBMISSION_PATH + '/temp/' + datetime.date.today().strftime('%Y/') + datetime.date.today().strftime('%m/'), base_url=None, file_permissions_mode=0o600)

UploadedFileStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None, directory_permissions_mode=0o700, file_permissions_mode=0o600)


def upload_path(*path_components):
    """
    Builds an upload path that will be unique: upload_path(a, b, c, filename) -> year/month/a/b/c/uuid1/filename
    """
    today = datetime.date.today()

    filename = path_components[-1]
    path_components = list(path_components[:-1])
    uu = uuid.uuid1(uuid.getnode())
    components = [today.strftime('%Y'), today.strftime('%m')] + path_components + [str(uu), filename]
    # make sure filenames are entirely ASCII
    components = [c.encode('ascii', 'ignore').decode('ascii') for c in components]
    return os.path.join(*components)
