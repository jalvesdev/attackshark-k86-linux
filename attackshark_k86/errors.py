class K86Error(Exception):
    """Base library error."""


class HidApiUnavailable(K86Error):
    pass


class DeviceNotFound(K86Error):
    pass


class AmbiguousDevice(K86Error):
    pass


class IncorrectDevice(K86Error):
    pass


class IncorrectInterface(K86Error):
    pass


class DescriptorMismatch(K86Error):
    pass


class PermissionDenied(K86Error):
    pass


class DeviceDisconnected(K86Error):
    pass


class TransportTimeout(K86Error):
    pass


class TransportError(K86Error):
    pass


class MalformedReport(K86Error):
    pass


class UnauthorizedWrite(K86Error):
    pass
