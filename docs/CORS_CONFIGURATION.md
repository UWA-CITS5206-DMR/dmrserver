# CORS Configuration Guide

This document explains how to configure Cross-Origin Resource Sharing (CORS) settings for Django applications using environment variables.

## Environment Variable Configuration

### CORS_ALLOW_CREDENTIALS

- **Description**: Whether to allow credentials (cookies, authorization headers, etc.) in CORS requests
- **Default**: `True`
- **Valid values**: `True`, `False`, `1`, `0`, `yes`, `no`, `on`, `off`
- **Example**:

  ```env
  CORS_ALLOW_CREDENTIALS=True
  ```

### CORS_ALLOW_ALL_ORIGINS

- **Description**: Whether to allow requests from all origins
- **Default**: `True` (recommended for development)
- **Valid values**: `True`, `False`, `1`, `0`, `yes`, `no`, `on`, `off`
- **Example**:

  ```env
  CORS_ALLOW_ALL_ORIGINS=False  # Recommended for production
  ```

### CORS_ALLOWED_ORIGINS

- **Description**: Specific list of allowed domains when `CORS_ALLOW_ALL_ORIGINS=False`
- **Format**: Comma-separated list of URLs
- **Example**:

  ```env
  CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com,https://app.yourdomain.com
  ```

### CORS_ALLOWED_HEADERS

- **Description**: List of allowed HTTP headers
- **Default**: Common headers list (see below)
- **Special value**: `*` means allow all headers
- **Example**:

  ```env
  CORS_ALLOWED_HEADERS=*
  # Or specify specific headers
  CORS_ALLOWED_HEADERS=authorization,content-type,x-csrftoken
  ```

### CORS_ALLOWED_METHODS

- **Description**: List of allowed HTTP methods
- **Default**: `DELETE,GET,OPTIONS,PATCH,POST,PUT`
- **Format**: Comma-separated list of HTTP methods
- **Example**:

  ```env
  CORS_ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS
  ```

### CORS_PREFLIGHT_MAX_AGE

- **Description**: Preflight request cache time (in seconds)
- **Default**: `86400` (24 hours)
- **Example**:

  ```env
  CORS_PREFLIGHT_MAX_AGE=3600  # 1 hour
  ```

## Default Configuration

If environment variables are not set, the system will use the following default configuration:

### Development Environment Default Settings

```env
CORS_ALLOW_CREDENTIALS=True
CORS_ALLOW_ALL_ORIGINS=True
CORS_ALLOWED_HEADERS=*
CORS_ALLOWED_METHODS=DELETE,GET,OPTIONS,PATCH,POST,PUT
CORS_PREFLIGHT_MAX_AGE=86400
```

### Production Environment Recommended Settings

```env
CORS_ALLOW_CREDENTIALS=True
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
CORS_ALLOWED_HEADERS=accept,accept-encoding,authorization,content-type,dnt,origin,user-agent,x-csrftoken,x-requested-with
CORS_ALLOWED_METHODS=DELETE,GET,OPTIONS,PATCH,POST,PUT
CORS_PREFLIGHT_MAX_AGE=86400
```

## Security Considerations

1. **Production Environment**:
   - Do not use `CORS_ALLOW_ALL_ORIGINS=True`
   - Explicitly specify domains in `CORS_ALLOWED_ORIGINS`
   - Avoid using `CORS_ALLOWED_HEADERS=*`

2. **Development Environment**:
   - Relaxed settings can be used for convenience
   - Ensure to update to secure production configuration before deployment

3. **Credentials Handling**:
   - If `CORS_ALLOW_CREDENTIALS=True` is set, you cannot use `CORS_ALLOW_ALL_ORIGINS=True` simultaneously
   - Must explicitly specify allowed domains

## Common Configuration Examples

### Frontend React Application (localhost:3000)

```env
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=http://localhost:3000
CORS_ALLOW_CREDENTIALS=True
```

### Multiple Frontend Applications

```env
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080,https://app.yourdomain.com
CORS_ALLOW_CREDENTIALS=True
```

### Pure API Service (No Credentials Required)

```env
CORS_ALLOW_ALL_ORIGINS=True
CORS_ALLOW_CREDENTIALS=False
```

## Troubleshooting

1. **CORS Errors**: Check browser console for error messages
2. **Preflight Request Failures**: Ensure `OPTIONS` method is included in `CORS_ALLOWED_METHODS`
3. **Credentials Issues**: Check the combination of `CORS_ALLOW_CREDENTIALS` and domain configuration
