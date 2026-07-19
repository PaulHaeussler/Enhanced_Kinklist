# SWAG Setup

This app should be proxied as a subdomain or full domain, not a subfolder.

## Same Docker Host

1. Find the Docker network used by SWAG:

   ```bash
   docker inspect swag --format '{{json .NetworkSettings.Networks}}'
   ```

2. Set `SWAG_NETWORK` in this app's `.env` to that network name.

3. Start the app with the SWAG override:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.swag.yml up -d
   ```

4. Copy `enhanced-kinklist.subdomain.conf` into SWAG:

   ```bash
   cp deploy/swag/enhanced-kinklist.subdomain.conf /path/to/swag/config/nginx/proxy-confs/enhanced-kinklist.subdomain.conf
   ```

5. Edit the copied file and set `server_name` to the real domain.

6. Restart SWAG:

   ```bash
   docker restart swag
   ```

## Secondary Full Domain

If the app uses a separate full domain, add it to SWAG's `EXTRA_DOMAINS`, for example:

```env
EXTRA_DOMAINS=kinkli.st,www.kinkli.st
```

Make sure DNS for each name points at the SWAG host and that your certificate validation method can validate that domain.

## Subdomain Of Existing SWAG Domain

If the app uses a subdomain under SWAG's existing `URL`, add it to SWAG's `SUBDOMAINS` instead:

```env
SUBDOMAINS=www,kinklist
```

Then change the proxy config to:

```nginx
server_name kinklist.*;
```
