# Local development only. Official source pinned after public images became unavailable.
FROM golang:1.25.0-bookworm@sha256:81dc45d05a7444ead8c92a389621fafabc8e40f8fd1a19d7e5df14e61e98bc1a AS builder
WORKDIR /source
ADD --checksum=sha256:45521908307306e925c98d629e1c17d78c8b72b6ee242b1bfb1409f7d8ee5841 https://codeload.github.com/minio/minio/tar.gz/9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a /tmp/minio.tar.gz
RUN tar -xzf /tmp/minio.tar.gz --strip-components=1
ENV CGO_ENABLED=0 GOTOOLCHAIN=local
RUN go build -trimpath -ldflags="-s -w -X github.com/minio/minio/cmd.Version=RELEASE.2025-10-15T17-29-55Z" -o /out/minio .
FROM debian:bookworm-slim@sha256:734a72b3d6142a71993b4bc580ca01d8ca687f77a2c422d96a961d3376b179bc
COPY --from=builder /out/minio /usr/local/bin/minio
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=builder /source/LICENSE /usr/share/doc/minio/LICENSE
RUN mkdir /data && chown 10001:10001 /data
USER 10001:10001
EXPOSE 9000
ENTRYPOINT ["minio"]
CMD ["server","/data"]
