# Podman

Assumptions:

- You have created a skupper podman site named podman.
- You have linked the podman site to west site.


## Run getback

Run the following container
```bash
podman run --rm -p 9091:9091 -p 9092:9092 -p 9093:9093 quay.io/pwright/getback:latest
```

## Create Skupper resources

Create connectors:

```
skupper system apply -f podman/connectors.yaml 
```

You can now test at http://localhost:9093 