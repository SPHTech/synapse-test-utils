# Synapse Test Utils Library

## heartbeat.py

For Kubernetes(K8s) deployment, readiness and liveness probes are used to check if the container in the pod is ready and still functioning.

Upon start-up, each crossbar component will register a Remote Procedure Call (RPC) on its own "heartbeat" topic. K8s readiness and liveness probes would trigger a [heartbeat component script](heartbeat.py), and this component would call that heartbeat RPC. The crossbar component is deemed to be working if the trigger completes successfully, else the probes would fail and the container in the pod would be restarted.

## probe.py

Contains functions to start up a component and block until it is ready, as well as to make a crossbar component that subscribes to a crossbar topic and store the messages it receives.
