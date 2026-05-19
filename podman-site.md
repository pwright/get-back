# Local load balancing

Set `skupper` to use podman

```
export SKUPPER_PLATFORM=podman
```


Define the site

```
skupper system apply -f podman/site.yaml 
skupper system apply -f podman/listener.yaml 
skupper system apply -f podman/connectors.yaml 
```

