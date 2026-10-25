try:
    from aws_xray_sdk.core import patch
except ImportError:
    patch = None


def init():
    if patch:
        patch(["boto3"])
