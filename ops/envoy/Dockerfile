# Envoy Dockerfile for mTLS ingress
FROM envoyproxy/envoy:v1.29-latest

# Copy static config and certs
COPY envoy.yaml /etc/envoy/envoy.yaml
COPY certs/ /etc/envoy/certs/

# Expose mTLS port
EXPOSE 8443

CMD ["envoy", "-c", "/etc/envoy/envoy.yaml"]
