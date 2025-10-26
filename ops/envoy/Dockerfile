# Envoy Dockerfile for mTLS ingress
###############################
# DEPRECATED – DO NOT USE
# This repository does not build a custom Envoy image here.
# If an Envoy proxy is needed, reference the upstream image directly
# in your deployment manifests.
ERROR DO_NOT_USE_THIS_DOCKERFILE

# Copy static config and certs
COPY envoy.yaml /etc/envoy/envoy.yaml
COPY certs/ /etc/envoy/certs/

# Expose mTLS port
EXPOSE 8443

CMD ["envoy", "-c", "/etc/envoy/envoy.yaml"]
