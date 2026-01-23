"""
Storage API Client

This module provides a client for managing file storage operations via MinIO/S3-compatible storage.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, BinaryIO, Union
try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    raise ImportError(
        "minio package is required for storage operations. "
        "Please install it with: pip install minio"
    )


class StorageClient:
    """
    Client for managing file storage operations
    
    Provides methods for listing files, checking file existence,
    uploading files/folders, and downloading files.
    
    The client uses MinIO/S3-compatible storage and requires:
    - Storage endpoint URL
    - Access key (from PYROMIND_STORAGE_ACCESS_KEY env var)
    - Secret key (from PYROMIND_STORAGE_SECRET_KEY env var)
    - Bucket name (from PYROMIND_STORAGE_BUCKET env var, optional)
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        secure: bool = False,
        region: Optional[str] = None
    ):
        """
        Initialize the Storage Client
        
        Args:
            endpoint: Storage endpoint URL (e.g., "storage.pyromind.ai:9000")
                    If not provided, reads from PYROMIND_STORAGE_ENDPOINT env var
            access_key: Access key for storage authentication
                       If not provided, reads from PYROMIND_STORAGE_ACCESS_KEY env var
            secret_key: Secret key for storage authentication
                       If not provided, reads from PYROMIND_STORAGE_SECRET_KEY env var
            bucket_name: Default bucket name to use
                        If not provided, reads from PYROMIND_STORAGE_BUCKET env var
            secure: Whether to use HTTPS (default: False)
            region: Storage region (optional)
        
        Raises:
            ValueError: If required credentials are not provided
        """
        # Get endpoint from parameter or environment variable
        if endpoint is None:
            endpoint = os.getenv("PYROMIND_STORAGE_ENDPOINT")
        
        if not endpoint:
            raise ValueError(
                "Storage endpoint is required. Please provide it either as a parameter "
                "or set the PYROMIND_STORAGE_ENDPOINT environment variable."
            )
        
        # Get access key from parameter or environment variable
        if access_key is None:
            access_key = os.getenv("PYROMIND_STORAGE_ACCESS_KEY")
        
        if not access_key:
            raise ValueError(
                "Storage access key is required. Please provide it either as a parameter "
                "or set the PYROMIND_STORAGE_ACCESS_KEY environment variable."
            )
        
        # Get secret key from parameter or environment variable
        if secret_key is None:
            secret_key = os.getenv("PYROMIND_STORAGE_SECRET_KEY")
        
        if not secret_key:
            raise ValueError(
                "Storage secret key is required. Please provide it either as a parameter "
                "or set the PYROMIND_STORAGE_SECRET_KEY environment variable."
            )
        
        # Get bucket name from parameter or environment variable
        if bucket_name is None:
            bucket_name = os.getenv("PYROMIND_STORAGE_BUCKET")
        
        # Strip whitespace
        endpoint = endpoint.strip()
        access_key = access_key.strip()
        secret_key = secret_key.strip()
        
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.default_bucket = bucket_name
        self.secure = secure
        self.region = region
        
        # Initialize MinIO client
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region
        )
    
    def _ensure_bucket(self, bucket_name: str) -> None:
        """Ensure bucket exists, create if it doesn't."""
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)
    
    def _get_bucket(self, bucket_name: Optional[str] = None) -> str:
        """Get bucket name, using default if not provided."""
        bucket = bucket_name or self.default_bucket
        if not bucket:
            raise ValueError(
                "Bucket name is required. Please provide it either as a parameter "
                "or set the PYROMIND_STORAGE_BUCKET environment variable."
            )
        return bucket
    
    def list_files(
        self,
        folder_path: str = "",
        bucket_name: Optional[str] = None,
        recursive: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List files in a folder
        
        Args:
            folder_path: Path to the folder (e.g., "documents/" or "images/2024/")
            bucket_name: Bucket name (uses default if not provided)
            recursive: Whether to list files recursively (default: True)
        
        Returns:
            List of file information dictionaries, each containing:
            - object_name: Full path to the file
            - size: File size in bytes
            - last_modified: Last modification time
            - etag: ETag of the object
        """
        bucket = self._get_bucket(bucket_name)
        self._ensure_bucket(bucket)
        
        # Normalize folder_path to prefix
        if folder_path:
            prefix = folder_path.rstrip("/") + "/"
        else:
            prefix = ""
        
        files = []
        try:
            objects = self.client.list_objects(
                bucket_name=bucket,
                prefix=prefix,
                recursive=recursive
            )
            
            for obj in objects:
                # Skip directory markers
                if obj.object_name.endswith("/"):
                    continue
                
                files.append({
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                    "etag": obj.etag
                })
        except S3Error as e:
            raise ValueError(f"Failed to list files: {e.message}")
        
        return files
    
    def file_exists(
        self,
        file_path: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """
        Check if a file exists
        
        Args:
            file_path: Path to the file (e.g., "documents/file.txt")
            bucket_name: Bucket name (uses default if not provided)
        
        Returns:
            True if file exists, False otherwise
        """
        bucket = self._get_bucket(bucket_name)
        
        try:
            self.client.stat_object(bucket, file_path)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise ValueError(f"Failed to check file existence: {e.message}")
    
    def upload_file(
        self,
        file_path: Union[str, Path, BinaryIO],
        object_name: str,
        bucket_name: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to storage
        
        Args:
            file_path: Local file path or file-like object to upload
            object_name: Destination object name in storage (e.g., "documents/file.txt")
            bucket_name: Bucket name (uses default if not provided)
            content_type: MIME type of the file (auto-detected if not provided)
        
        Returns:
            Dictionary containing upload result:
            - object_name: Uploaded object name
            - etag: ETag of the uploaded object
            - size: Size of the uploaded file
        """
        bucket = self._get_bucket(bucket_name)
        self._ensure_bucket(bucket)
        
        # Handle file path or file-like object
        original_path = None
        if isinstance(file_path, (str, Path)):
            original_path = Path(file_path)
            if not original_path.exists():
                raise FileNotFoundError(f"File not found: {original_path}")
            
            file_size = original_path.stat().st_size
            file_obj = open(original_path, "rb")
            should_close = True
        else:
            # Assume it's a file-like object
            file_obj = file_path
            file_obj.seek(0, 2)  # Seek to end
            file_size = file_obj.tell()
            file_obj.seek(0)  # Seek back to start
            should_close = False
        
        try:
            # Auto-detect content type if not provided
            if content_type is None and original_path is not None:
                import mimetypes
                content_type, _ = mimetypes.guess_type(str(original_path))
                if content_type is None:
                    content_type = "application/octet-stream"
            
            result = self.client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=file_obj,
                length=file_size,
                content_type=content_type or "application/octet-stream"
            )
            
            return {
                "object_name": object_name,
                "etag": result.etag,
                "size": file_size,
                "version_id": result.version_id
            }
        except S3Error as e:
            raise ValueError(f"Failed to upload file: {e.message}")
        finally:
            if should_close:
                file_obj.close()
    
    def upload_folder(
        self,
        folder_path: Union[str, Path],
        object_prefix: str = "",
        bucket_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Upload a folder and all its contents recursively
        
        Args:
            folder_path: Local folder path to upload
            object_prefix: Prefix for object names in storage (e.g., "backups/2024/")
            bucket_name: Bucket name (uses default if not provided)
        
        Returns:
            List of upload results for each file
        """
        folder_path = Path(folder_path)
        if not folder_path.is_dir():
            raise ValueError(f"Path is not a directory: {folder_path}")
        
        results = []
        
        # Walk through all files in the folder
        for file_path in folder_path.rglob("*"):
            if file_path.is_file():
                # Calculate relative path from folder_path
                relative_path = file_path.relative_to(folder_path)
                
                # Construct object name with prefix
                if object_prefix:
                    object_name = f"{object_prefix.rstrip('/')}/{relative_path.as_posix()}"
                else:
                    object_name = relative_path.as_posix()
                
                try:
                    result = self.upload_file(
                        file_path=file_path,
                        object_name=object_name,
                        bucket_name=bucket_name
                    )
                    results.append(result)
                except Exception as e:
                    results.append({
                        "object_name": object_name,
                        "error": str(e)
                    })
        
        return results
    
    def download_file(
        self,
        object_name: str,
        file_path: Optional[Union[str, Path]] = None,
        bucket_name: Optional[str] = None
    ) -> Union[bytes, Path]:
        """
        Download a file from storage
        
        Args:
            object_name: Object name in storage (e.g., "documents/file.txt")
            file_path: Local file path to save to (if None, returns bytes)
            bucket_name: Bucket name (uses default if not provided)
        
        Returns:
            If file_path is provided, returns the Path object.
            If file_path is None, returns the file content as bytes.
        """
        bucket = self._get_bucket(bucket_name)
        
        try:
            response = self.client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            
            if file_path is not None:
                # Save to file
                file_path = Path(file_path)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "wb") as f:
                    f.write(data)
                return file_path
            else:
                # Return bytes
                return data
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {object_name}")
            raise ValueError(f"Failed to download file: {e.message}")
    
    def close(self):
        """Close the client (no-op for MinIO client)"""
        pass
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
