from compressor.storage import CompressorFileStorage as BaseCompressorFileStorage


class CompressorFileStorage(BaseCompressorFileStorage):
    """
    Override to make sure static/CACHE files are world-readable, even if other files created by the system aren't.
    """
    def __init__(self, *args, **kwargs):
        super(CompressorFileStorage, self).__init__(file_permissions_mode=0o644, directory_permissions_mode=0o755, *args, **kwargs)