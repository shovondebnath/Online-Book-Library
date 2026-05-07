from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class SupabaseBaseStorage(S3Boto3Storage):
    default_acl = None
    file_overwrite = False
    querystring_auth = False
    endpoint_url = settings.AWS_S3_ENDPOINT_URL
    region_name = settings.AWS_S3_REGION_NAME


class BookFileStorage(SupabaseBaseStorage):
    bucket_name = 'book-files'
    custom_domain = (
        f"{settings.SUPABASE_PROJECT_REF}.supabase.co"
        '/storage/v1/object/public/book-files'
    )


class CoverImageStorage(SupabaseBaseStorage):
    bucket_name = 'cover-image'
    custom_domain = (
        f"{settings.SUPABASE_PROJECT_REF}.supabase.co"
        '/storage/v1/object/public/cover-image'
    )


def book_file_storage():
    return BookFileStorage()


def cover_image_storage():
    return CoverImageStorage()