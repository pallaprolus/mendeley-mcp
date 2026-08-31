# Mendeley MCP Server Docker Image
FROM python:3.12-slim

LABEL org.opencontainers.image.title="Mendeley MCP Server"
LABEL org.opencontainers.image.description="MCP server for Mendeley reference manager"
LABEL org.opencontainers.image.source="https://github.com/pallaprolus/mendeley-mcp"
LABEL org.opencontainers.image.licenses="MIT"

# Install from the checked-out source, so an image always contains the commit
# it was built from. Installing from PyPI here raced the upload on tag pushes:
# the image workflow and the publish workflow both fire on a v* tag, so an
# image could be tagged with a new version while containing the previous one.
COPY . /src
RUN pip install --no-cache-dir /src && rm -rf /src

# Environment variables for credentials (must be provided at runtime)
# MENDELEY_CLIENT_ID - Your Mendeley app client ID
# MENDELEY_CLIENT_SECRET - Your Mendeley app client secret
# MENDELEY_REFRESH_TOKEN - OAuth refresh token (get via mendeley-auth login)

# Run the MCP server
ENTRYPOINT ["mendeley-mcp"]
