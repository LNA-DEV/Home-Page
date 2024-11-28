#!/bin/bash

# Config
KUBECONFIG_PATH="/home/runner/work/_temp/config"

# Get old pvc
PVC_NAME_OLD=$(kubectl get pvc -n personal-dev -o jsonpath='{.items[0].metadata.name}' --kubeconfig $KUBECONFIG_PATH)

# Generate a unique name for the PVC
PVC_NAME="personal-website-pvc-$(head /dev/urandom | tr -dc a-z0-9 | head -c 6)"
echo "Creating PVC: $PVC_NAME"

# Create the PVC
cat <<EOF | kubectl --kubeconfig=$KUBECONFIG_PATH apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: $PVC_NAME
  namespace: personal-dev
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: longhorn
  resources:
    requests:
      storage: 10Gi
EOF

# Create a pod that mounts the PVC
cat <<EOF | kubectl --kubeconfig=$KUBECONFIG_PATH apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: data-uploader
  namespace: personal-dev
spec:
  containers:
  - name: nginx
    image: nginx:alpine
    volumeMounts:
    - name: data-volume
      mountPath: /usr/share/nginx/html
  volumes:
  - name: data-volume
    persistentVolumeClaim:
      claimName: $PVC_NAME
EOF

# Wait for the pod to be ready
echo "Waiting for the pod to be ready..."
kubectl --kubeconfig=$KUBECONFIG_PATH wait --for=condition=ready pod/data-uploader -n personal-dev --timeout=120s

# Upload data to the pod
POD_NAME="data-uploader"
kubectl --kubeconfig=$KUBECONFIG_PATH cp ./public/. $POD_NAME:/usr/share/nginx/html/ -n personal-dev

# Confirm the data upload
echo "Data uploaded to the PVC via the pod."

# Cleanup
echo "Cleaning up temporary resources..."
kubectl --kubeconfig=$KUBECONFIG_PATH delete pod $POD_NAME -n personal-dev

# Optional: Deploy using Helm to bind this PVC to a long-term deployment
helm --kubeconfig=$KUBECONFIG_PATH upgrade --install charts.personal oci://registry-1.docker.io/lnadev/charts.personal --set homePage.dev.pvcName=$PVC_NAME --reuse-values --namespace default --wait

kubectl delete pvc $PVC_NAME_OLD
