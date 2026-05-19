# Local load balancing

Set `skupper` to use podman

```bash
export SKUPPER_PLATFORM=podman
```


Define the site

```bash
skupper system apply -f podman/site.yaml 
skupper system apply -f podman/listener.yaml 
skupper system apply -f podman/connectors.yaml 
```


Run the image twice with different ports:

```bash
podman run -d --replace --name getback-1 -p 19091:9091 -p 19092:9092 -p 9093:9093 getback:dev

podman run -d --replace --name getback-2 -p 29091:9091 -p 29092:9092  getback:dev
```
